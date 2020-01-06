# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_core/pupils.py - last updated 2020-01-06

Database access for reading pupil data.

==============================
Copyright 2019-2020 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

# Note that "klass" is often used, in comments as well as in the code,
# to mean school-class. The "k" can help to avoid confusion with
# Python classes.

from fnmatch import fnmatchcase
from collections import OrderedDict, UserList

from .db import DB


def fromKlassStream (klass_stream):
    """Split a klass_stream item into klass and stream.
    If there is no stream, set this part to <None>.
    Return a tuple: (klass, stream).
    """
    try:
        klass, stream = klass_stream.split ('.')
        return (klass, stream)
    except:
        return (klass_stream, None)

def toKlassStream (klass, stream, forcestream=False):
    """Build a klass_stream name from klass and stream.
    Stream may be <None> or other "false" value, in which case
    just the klass is returned ...
    However, if <forcestream> is true, stream is set to '_' if
    there is no stream.
    Return klass_stream as <str>.
    """
    return klass + '.' + stream if stream else klass


def match_klass_stream(klass_stream, kmap):
    """Find the first matching entry for the klass/group in the mapping list.
    The klass-stream is "normalized" so that there is always a '.'
    between klass and stream, even if there is no stream.
    An entry in the list has the form 'klass_stream: value'.
    "glob" (fnmatch) matching is used on the klass_stream part,
    with one extension:
    There may be a single '<'. The part before the '<' will be taken as
    the minimum acceptable klass_stream. After the '<' is the part to
    be matched.
    Example <kmap>:
        ['13.Gym: Notenzeugnis/Abgang-13.html',
         '12.Gym: Notenzeugnis/Notenzeugnis-12_SII.html',
         '12.*': Notenzeugnis/Notenzeugnis-12_SI.html',
         '05<*: Notenzeugnis/Notenzeugnis-SI.html'
        ]
    Return the "stripped" value (after ':') if a match is found.
    If the entry has no value, or if there is no matching entry,
    return <None>.
    """
    k, s = fromKlassStream(klass_stream)
    ks = k + '.' + (s or '')
    for item in kmap:
        k, v = item.split(':', 1)
        try:
            kmin, k = k.split('<')
        except:
            kmin = '00'
        if fnmatchcase(ks, k):
            if klass_stream >= kmin:
                return v.strip() or None
    return None


class KlassData:
    def __init__(self, klass_stream):
        self.klass, self.stream = fromKlassStream(klass_stream)
        # Leading zero on klass names?
        self.name = (self.klass if CONF.MISC.CLASS_LEADING_ZERO
                else self.klass.lstrip('0'))
#TODO: switch to klasstag (report covers!)
#        self.klein = self.klass[-1] == 'K'      # "Kleinklasse"
        self.klasstag = self.klass[2:]          # assumes 2-digit classes
        self.year = self.klass[:2].lstrip('0')  # assumes 2-digit classes



class PupilData (list):
    """A list which allows keyed access to its fields.
    As the fields are a class attribute, this class can only be used for
    one type of list. It is used to hold the fields of the pupil data.
    Before instantiating, <fields> must be called to set up the field
    names and indexes.
    """
    _fields = None

    @staticmethod
    def fieldNames ():
        return CONF.TABLES.PUPILS_FIELDNAMES

    @classmethod
    def fields (cls):
        if cls._fields == None:
            cls._fields = OrderedDict ()
            i = 0
            for f in cls.fieldNames ():
                cls._fields [f] = i
                i += 1
        return cls._fields

    #### The main part of the class, dealing with instances:

    def __init__ (self, values):
        if len (values) != len (self._fields):
            REPORT.Fail (_WRONGLENGTH, fields=repr (self._fields),
                    values=repr (values))
        super ().__init__ (values)

    def __getitem__ (self, key):
        if type (key) == str:
            return super (). __getitem__ (self._fields [key])
        else:
            return super (). __getitem__ (key)

    def __setitem__ (self, key, value):
        if type (key) == str:
            return super (). __setitem__ (self._fields [key], value)
        else:
            return super (). __setitem__ (key, value)

    def name (self):
        """Return the (short form of) pupil's name.
        """
        return self ['FIRSTNAME'] + ' ' + self ['LASTNAME']

    def klassStream (self):
        return toKlassStream (self ['CLASS'], self ['STREAM'])

    def toMapping(self):
        return OrderedDict(map(lambda a,b: (a,b), self.fields(), self))


class Pupils:
    def __init__ (self, schoolyear):
        self.schoolyear = schoolyear
        self.db = DB (schoolyear)
        PupilData.fields ()

    def classes (self):
        """Return a sorted list of klass names.
        """
        return sorted (self.db.selectDistinct ('PUPILS', 'CLASS'))

    def streams (self, klass):
        """Return a sorted list of stream names for the given klass.
        """
        return sorted ([s or ''
                for s in self.db.selectDistinct ('PUPILS', 'STREAM',
                        CLASS=klass)])

    def classPupils (self, klass_stream, date=None):
        """Read the pupil data for the given klass (and stream).
        Return an ordered list of <PupilData> named tuples.
        If a <date> is supplied, pupils who left the school before that
        date will not be included.
        <klass_stream> may be just the klass name, in which case all
        pupils are returned. It may, however, also include a stream name,
        as <klass>.<stream>, restricting the result to those pupils in
        the given stream.
        To enable indexing on pupil-id, the result has an extra
        attribute, <pidmap>: {pid-> <PupilData> instance}
        """
        klass, stream = fromKlassStream (klass_stream)
        fetched = self.db.select ('PUPILS', CLASS=klass)
        rows = UserList()
        rows.pidmap = {}
        for row in fetched:
            pdata = PupilData (row)
            # Check exit date
            if date:
                exd = pdata ['EXIT_D']
                if exd and exd < date:
                    continue
            # Check stream
            if (not stream) or (stream == pdata ['STREAM']):
                rows.append (pdata)
                rows.pidmap [pdata ['PID']] = pdata
        return rows



def test_01 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
    REPORT.Test ("Classes: %s" % repr(pdb.classes ()))

def test_02 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
    REPORT.Test ("Streams: %s" % repr(pdb.streams ('12')))

def test_03 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
    date = '2016-06-20'
    c = '10'
    cdata = pdb.classPupils (c, date)
    REPORT.Test ("\n-- Class %s" % c)
    for line in cdata:
        REPORT.Test ("     " + repr (line))

def test_04 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
#    date = '2016-06-20'
    cs = '10.RS'
    cdata = pdb.classPupils (cs)
    REPORT.Test ("\n-- Class.Stream %s" % cs)
    for line in cdata:
        REPORT.Test ("     " + repr (line))

