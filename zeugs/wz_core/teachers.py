#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_core/teachers.py

Last updated:  2019-12-08

Access to the list of teachers.

=+LICENCE=============================
Copyright 2017-2019 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

=-LICENCE========================================
"""

### Messages
_MISSINGDBFIELD = "Feld fehlt in Lehrer-Tabelle {filepath}:\n  {field}"
_UNKNOWNTEACHER = "Unbekannte Lehrkraft. Kürzel: {tid}"


from collections import OrderedDict

from wz_core.configuration import Paths
# To read teacher table:
from wz_table.dbtable import readDBTable


class TeacherData (OrderedDict):
    """Manage the teacher list. This data is read in from a table in
    the file <TEACHERDATA_FILENAME>.
    """
    def __init__ (self, schoolyear):
        """Build a representation of the teacher table.
        """
        filepath = Paths.getYearPath (schoolyear, 'FILE_TEACHERDATA')
        super ().__init__ ()

        # An exception is raised if there is no file:
        table = readDBTable (filepath)

# Not presently used
#        self.info = table.info

        # Associate the headers with columns indexes.
        colmap = {}
        for f, f1 in CONF.TABLES.TEACHER_FIELDNAMES.items ():
            try:
                colmap [f] = table.headers [f1]
            except:
                # Field not present
                REPORT.Warn (_MISSINGDBFIELD, filepath=filepath,
                        field=f1)

        ### Read the row data
        for row in table:
            rowdata = {}
            for f, col in colmap.items ():
                rowdata [f] = row [col]
            self [row [0]] = rowdata


    def getTeacherName (self, tid):
        """Return the teacher's name as it should appear in a report,
        as a single string. If there is no name, return a default string.
        If <tid> is not defined, an exception will occur.
        """
        name = self [tid] ['NAME']
        return name or ("?%s?" % tid)


    def checkTeacher (self, tid, report=True):
        if tid in self:
            return True
        if report:
            REPORT.Error (_UNKNOWNTEACHER, tid=tid)
        return False



##################### Test functions
_testyear = 2016
def test_1 ():
    REPORT.Test ("Teachers: ID and name")
    tmap = TeacherData (_testyear)
    for tid in tmap:
        REPORT.Test ("  id - name: %s - %s" % (tid, tmap.getTeacherName (tid)))

def test_2 ():
    tmap = TeacherData (_testyear)
    for tid in 'AM', 'nn', 'RP', 'MT':
        REPORT.Test ("\nTeacher %s: %s" % (tid, tmap [tid]))
