# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_core/pupils.py - last updated 2020-01-26

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

from fnmatch import fnmatchcase
from collections import OrderedDict, UserList

from .db import DB


class Klass:
    """An object representing a school-class, or one or more streams
    within a school-class.
    """
    def __init__(self, klass_stream):
        """<klass_stream> is a school-class with optional stream appendage.

        The class part can be 1 or 2 digits (school year/grade) followed
        by an optional tag string.
        The stream part can be a single stream, or '_', or a list of streams
        separated by '-'. '_' is used to cover pupils with no stream.
        The format is '<klass>.<stream list>'.
        Attributes:
            klass: str  (2-digit, if necessary with leading 0, + tag)
            streams: [str]
            stream: the stream if a single stream is given, otherwise <None>
            year: int   (school year – Am.: grade)
            klasstag: str (tag part of class)
            name: str (print-name of class)
        """
        self.stream = None
        try:
            klass, streams = klass_stream.split ('.')
            self.streams = sorted(streams.split('-'))
            if len(self.streams) == 1:
                self.stream = streams
        except:
            klass = klass_stream
            self.streams = []
        self.year = int(klass[0])
        try:
            self.year = self.year*10 + int(klass[1])
            self.klasstag = klass[2:]
        except:
            self.klasstag = klass[1:]
        self.klass = '%02d%s' % (self.year, self.klasstag)
        self.name = (self.klass if CONF.MISC.CLASS_LEADING_ZERO
                else self.klass.lstrip('0'))

    def __str__(self):
        if self.streams:
            return self.klass + '.' + '-'.join(self.streams)
        return self.klass

    @classmethod
    def fromKandS(cls, klass, stream):
        return cls(klass + '.' + (stream or '_'))


    def match_map(self, kmap):
        """Find the first matching entry for the klass.stream in the
        mapping list.
        The klass.stream is "normalized" so that there is always a '.',
        even if the whole class is addressed (empty stream part).
        An entry in the list has the form 'klass.stream: value'.
        "glob" (fnmatch) matching is used on the klass.stream part,
        with one extension:
        There may be a single '<'. The part before the '<' will be taken as
        the minimum acceptable klass.stream (string comparison).
        After the '<' is the part to be matched.
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
        ks = str(self)
        if not self.streams:
            ks += '.'
        for item in kmap:
            k, v = item.split(':', 1)
            try:
                kmin, k = k.split('<')
            except:
                kmin = '00'
            if fnmatchcase(ks, k):
                if ks >= kmin:
                    return v.strip() or None
        return None


    def klassStreams (self, schoolyear):
        """Return a sorted list of stream names for this school-class.
        """
        return sorted ([s or '_'
                for s in DB(schoolyear).selectDistinct ('PUPILS', 'STREAM',
                        CLASS=self.klass)])



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

    def getKlass(self, withStream=False):
        """Return a <Klass> object for this pupil.
        If <withStream> is true, add a stream tag.
        """
        if withStream:
            return Klass.fromKandS(self ['CLASS'], self ['STREAM'])
        return Klass(self['CLASS'])

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

    def pupil(self, pid):
        """Return a <PupilData> named tuple for the given pupil-id.
        """
        pdata = self.db.select1('PUPILS', PID=pid)
        if pdata:
            return PupilData(pdata)
        return None

    def classPupils (self, klass, date=None):
        """Read the pupil data for the given school-class (possibly with
        streams).
        Return an ordered list of <PupilData> named tuples.
        If a <date> is supplied, pupils who left the school before that
        date will not be included.
        <klass> is a <Klass> instance. If it has no streams, all pupils
        are returned. If there are strems, only those pupils in one of
        the given streams are returned.
        To enable indexing on pupil-id, the result has an extra
        attribute, <pidmap>: {pid-> <PupilData> instance}
        """
        fetched = self.db.select('PUPILS', CLASS=klass.klass)
        rows = UserList()
        rows.pidmap = {}
        slist = klass.streams
        for row in fetched:
            pdata = PupilData(row)
            # Check exit date
            if date:
                exd = pdata['EXIT_D']
                if exd and exd < date:
                    continue
            # Check stream
            if (not slist) or ((pdata['STREAM'] or '_') in slist):
                rows.append (pdata)
                rows.pidmap [pdata['PID']] = pdata
        return rows



def test_01 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
    REPORT.Test ("Classes: %s" % repr(pdb.classes ()))

def test_02 ():
    _year = 2016
    _klass = '12'
    REPORT.Test ("Streams: %s" % repr(Klass(_klass).klassStreams (_year)))

def test_03 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
    date = '2016-06-20'
    c = Klass('10')
    cdata = pdb.classPupils (c, date)
    REPORT.Test ("\n-- Class %s" % c)
    for line in cdata:
        REPORT.Test ("     " + repr (line))

def test_04 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
#    date = '2016-06-20'
    cs = Klass('10.RS')
    cdata = pdb.classPupils (cs)
    REPORT.Test ("\n-- Class.Stream %s" % cs)
    for line in cdata:
        REPORT.Test ("     " + repr (line))

