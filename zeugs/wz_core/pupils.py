#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_core/pupils.py - last updated 2019-09-27

Database access for reading pupil data.

==============================
Copyright 2019 Michael Towers

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

from collections import OrderedDict

from .db import DB


class PupilData (list):
    """A list which allows keyed access to its fields.
    As the fields are a class attribute, this class can only be used for
    one type of list. It is used to hold the fields of the pupil data.
    Before instantiating, <fields> must be called to set up the field
    names and indexes.
    """
    _fields = None

    @classmethod
    def fields (cls):
        if cls._fields == None:
            cls._fields = OrderedDict ()
            i = 0
            for f in CONF.TABLES.PUPILS_FIELDNAMES:
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




class Pupils:
    def __init__ (self, schoolyear):
        self.schoolyear = schoolyear
        self.db = DB (schoolyear)
        PupilData.fields ()

    def classes (self):
        """Return a sorted list of class names.
        """
        return self.db.selectDistinct ('PUPILS', 'CLASS', order=True)

    def classPupils (self, klass, date=None, stream=None):
        """Read in a table containing pupil data for the given class.
        Return an ordered list of <PupilData> named tuples.
        If a <date> is supplied, pupils who left the school before that
        date will not be included.
        If a <stream> is supplied, only pupils in this stream will be
        included.
        """
        fetched = self.db.select ('PUPILS', CLASS=klass)
        rows = []
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
        return rows




def test_01 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
    REPORT.Test ("Classes: %s" % repr(pdb.classes ()))

def test_02 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
    date = '2016-06-20'
    c = '10'
    cdata = pdb.classPupils (c, date)
    REPORT.Test ("\n-- Class %s" % c)
    for line in cdata:
        REPORT.Test ("     " + repr (line))

def test_03 ():
    schoolyear = 2016
    pdb = Pupils (schoolyear)
#    date = '2016-06-20'
    c = '10'
    g = 'RS'
    cdata = pdb.classPupils (c, stream=g)
    REPORT.Test ("\n-- Class/Stream %s %s" % (c, g))
    for line in cdata:
        REPORT.Test ("     " + repr (line))

