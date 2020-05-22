### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_core/teachers.py

Last updated:  2020-05-22

Access to the list of teachers.

=+LICENCE=============================
Copyright 2017-2020 Michael Towers

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
#_MISSINGDBFIELD = "Feld fehlt in Lehrer-Tabelle {filepath}:\n  {field}"
_UNKNOWN_TEACHER = "Unbekannte Lehrkraft. Kürzel: {tid}"
_BADSCHOOLYEAR  = "Falsches Jahr in Tabelle {filepath}: {year} erwartet"

_TEACHER_TABLE_TITLE = "Lehrkräfte"
_SCHOOLYEAR = "Schuljahr"

from wz_core.configuration import Paths
from wz_core.db import DBT
# To read/write spreadsheet tables:
from wz_table.dbtable import dbTable, makeDBTable


class TeacherData:
    def __init__(self, schoolyear):
        self.db = DBT(schoolyear)


    def checkTeacher(self, tid, report = True):
        """Return <True> if the teacher-id is valid.
        Otherwise return <False>; also report an error if <report> is true.
        """
        with self.db:
            if self.db.select1('TEACHERS', TID = tid):
                return True
        if report:
            REPORT.Error(_UNKNOWN_TEACHER, tid = tid)
        return False


    def getTeacherName(self, tid):
        """Return the teacher's name as it should appear in a report,
        as a single string.
        """
        return self[tid]['NAME']


    def __iter__(self):
        """Allow a class instance to act as an iterator over sorted
        teacher-ids.
        """
        with self.db:
            rows = self.db.select('TEACHERS', order = 'SHORTNAME')
        for r in rows:
            yield r['TID']


    def __getitem__(self, tid):
        """Access a teacher's data using teacher-id as key.
        """
        with self.db:
            row = self.db.select1('TEACHERS', TID = tid)
        if row:
            return row
        raise KeyError(_UNKNOWN_TEACHER.format(tid = tid))



def readTeacherTable(schoolyear, filepath):
    """Read in a table containing the information about the teachers/users
    needed by the application.
    The data is transferred to the TEACHERS table of the database,
    replacing all previous data.
    The table headers (field names) are translated according to the
    configuration file CONF.TABLES.TEACHER_FIELDNAMES.
    The (internal) names of date fields are expected to end with '_D'.
    Date values are accepted in isoformat, YYYY-MM-DD (that is %Y-%m-%d
    for the <datetime> module) or in the format specified for output,
    config value MISC.DATEFORMAT.
    """
    fields = CONF.TABLES.TEACHER_FIELDNAMES
    # An exception is raised if there is no file:
    table = dbTable(filepath, fields)
    fpath = table.filepath or filepath.filename
    try:
        # If there is a year field, check it against <schoolyear>
        _tyear = table.info[_SCHOOLYEAR]
    except KeyError:
        pass    # No year given in table
    else:
        try:
            if int(_tyear) != schoolyear:
                raise ValueError
        except:
            REPORT.Fail(_BADSCHOOLYEAR, filepath = fpath,
                    year = schoolyear)
    # Add all entries to database table
    with DBT(schoolyear) as db:
        db.clearTable('TEACHERS')
        # <pupilAdd> can modify/complete the <pdata> items
        db.addRows('TEACHERS', fields,
                [[tdata[f] for f in fields] for tdata in table.values()])
    return fpath


def exportTeachers(schoolyear, filepath = None):
    """Export the teacher data for the given year to a spreadsheet file,
    (.xlsx) formatted as a 'dbtable'.
    If <filepath> is supplied, it must be the full path, but the
    file-type ending is not required. The full path to the spreadsheet
    file, including the file-type ending, is returned.
    If no filepath is given, return the spreadsheet as a <bytes> object.
    """
    if filepath:
        # Ensure folder exists
        folder = os.path.dirname(filepath)
        if not os.path.isdir(folder):
            os.makedirs(folder)

    with DBT(schoolyear) as db:
        rrows = db.select('TEACHERS', order = 'SHORTNAME')
    # The fields of the pupils table (in the database):
    fields = CONF.TABLES.TEACHER_FIELDNAMES
    rows = []
    for vrow in rrows:
        values = []
        for f in fields:
            try:
                values.append(vrow[f])
            except KeyError:
                values.append(None)
        rows.append(vrow)
    rows.append(None)

    return makeDBTable(filepath, _TEACHER_TABLE_TITLE, fields.values(),
            rows, [(_SCHOOLYEAR, schoolyear)])



class User:
    """Handle user table for front-end (access control, etc.).
    This uses the active teachers table for the main data, but
    there can also be system users in the "master" db.
    """
    def __init__(self, tid):
        db0 = DBT()
        with db0:
            val = db0.getInfo('PW_' + tid)
            if val:
                self.valid = 'SYSTEM'
                self.perms, self.pwh = val.split('|', 1)
                self.name = 'Admin_' + tid
                return
        year = db0.schoolyear
        if year:
            try:
                row = TeacherData(year)[tid]
            except KeyError:
                pass
            else:
                self.valid = 'USER'
                self.perms = row['PERMISSION']
                self.pwh = row['PASSWORD']
                self.name = row['NAME']
                return
        self.valid = None



def migrateTeachers(toyear):
    """Copy the teachers table from the previous year.
    """
    with DBT(toyear - 1) as db:
        rrows = db.select('TEACHERS', order = 'SHORTNAME')
    # The fields of the pupils table (in the database):
    fields = CONF.TABLES.TEACHER_FIELDNAMES
    # Add all entries to database table
    with DBT(toyear) as db:
        db.clearTable('TEACHERS')
        db.addRows('TEACHERS', fields,
                [[tdata[f] for f in fields] for tdata in rrows])




##################### Test functions
_testyear = 2016
def test_01():
    filepath = Paths.getYearPath (_testyear, 'FILE_TEACHERDATA')
    fpath = readTeacherTable(_testyear, filepath)
    REPORT.Test("Table from %s entered into database (TEACHERS) for %d"
            % (fpath, _testyear))

def test_02():
    REPORT.Test ("Teachers: ID and name\n------------------------\n")
    teachers = TeacherData(_testyear)
    for tid in teachers:
        REPORT.Test("  %s: %s" % (tid, teachers.getTeacherName(tid)))

def test_03():
    teachers = TeacherData(_testyear)
    for tid in 'AM', 'nn', 'RP', 'MT':
        REPORT.Test ("\nTeacher %s: %s" % (tid, dict(teachers[tid])))

def test_04():
    REPORT.Test("User login data\n")
    for uid in 'X', 'Test', 'KA', 'MT':
        u = User(uid)
        if u.valid:
            REPORT.Test("&&& %s: %s / %s / %s ..." % (uid, u.name,
                    u.perms, u.pwh[:32]))
        else:
            REPORT.Test("&&& %s: invalid" % uid)

def test_05():
    REPORT.Test("Unknown teacher:")
    TeacherData(_testyear)['DUMMY']
