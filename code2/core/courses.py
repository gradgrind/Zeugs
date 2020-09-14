### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/courses.py - last updated 2020-09-14

Database access for reading course data.

==============================
Copyright 2020 Michael Towers

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

import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

### Messages
_UNKNOWN_SID = "Fach-Kürzel „{sid}“ ist nicht bekannt"
_FIELD_MISMATCH = ("Tabelle hat die falschen Felder für Datenbank {table}:\n"
        "  Datenbank: {dbfields}\n  Tabelle: {tablefields}")


#from collections import UserList

from core.db import DB
from tables.spreadsheet import Spreadsheet
from local.course_config import SUBJECT_FIELDS, CLASS_SUBJECT_FIELDS

class CourseError(Exception):
    pass

class Subjects:
    """Manage the SUBJECT table.
    """
    def __init__(self, schoolyear):
        self.schoolyear = schoolyear
        self.dbconn = DB(schoolyear)
#
    def __getitem__(self, sid):
        """Return the name of the subject with the given tag.
        """
        with self.dbconn:
            row = self.dbconn.select1('SUBJECT', SID = sid)
        if not row:
            raise KeyError(_UNKNOWN_SID.format(sid = sid))
        return row['SUBJECT']
#
    def from_table(self, filepath):
        """Reload the table from the given file (a table).
        """
        ss = Spreadsheet(filepath)
        dbt = ss.dbTable()
        tablefields = dbt.fieldnames()
        i = 0
        for f in SUBJECT_FIELDS:
            if f != tablefields[i]:
                raise CourseError(_FIELD_MISMATCH.format(table = 'SUBJECT',
                        dbfields = ', '.join(SUBJECT_FIELDS),
                        tablefields = ', '.join(tablefields)))
            i += 1
        rows = [row for row in dbt.rows if row[0]]
        with self.dbconn:
            self.dbconn.clearTable('SUBJECT')
            self.dbconn.addRows('SUBJECT', SUBJECT_FIELDS, rows)



class Class_Subjects:
    """Manage the CLASS_SUBJECTS table.
    """
    def __init__(self, schoolyear):
        self.schoolyear = schoolyear
        self.dbconn = DB(schoolyear)
#
    def for_class(self, klass):
        """Return a list of subject-data rows for the given class.
        """
        with self.dbconn:
            return list(self.dbconn.select('CLASS_SUBJECT', CLASS = klass))


    def from_table(self, filepath):
        pass


        with self.dbconn:
            self.dbconn.addRows('CLASS_SUBJECT', fields, data)







if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    subjects = Subjects(2016)
    filepath = os.path.join(DATA, 'testing', 'Subjects.ods')
    fname = os.path.basename(filepath)
    subjects.from_table(filepath)
    print("En ->", subjects['En'])
