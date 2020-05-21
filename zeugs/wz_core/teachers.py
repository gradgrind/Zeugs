### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_core/teachers.py

Last updated:  2020-05-21

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
_UNKNOWNTEACHER = "Unbekannte Lehrkraft. Kürzel: {tid}"
_BADSCHOOLYEAR  = "Falsches Jahr in Tabelle {filepath}: {year} erwartet"

_TEACHER_TABLE_TITLE = "Lehrkräfte"
_SCHOOLYEAR = "Schuljahr"

from collections import OrderedDict

from wz_core.configuration import Paths
from wz_core.db import DBT
# To read/write spreadsheet tables:
from wz_table.dbtable import dbTable, makeDBTable


class TeacherData (OrderedDict):
    """Manage the teacher list. This data is read in from a table in
    the file <TEACHERDATA_FILENAME>.
    """
    def __init__ (self, schoolyear):
        """Build a representation of the teacher table.
        """
        filepath = Paths.getYearPath (schoolyear, 'FILE_TEACHERDATA')
        # An exception is raised if there is no file:
        super ().__init__ (dbTable(filepath, CONF.TABLES.TEACHER_FIELDNAMES))

#############################
#        super ().__init__ ()
#        table = readDBTable (filepath)
#
## Not presently used
##        self.info = table.info
#
#        # Associate the headers with columns indexes.
#        colmap = {}
#        for f, f1 in CONF.TABLES.TEACHER_FIELDNAMES.items ():
#            try:
#                colmap [f] = table.headers [f1]
#            except:
#                # Field not present
#                REPORT.Warn (_MISSINGDBFIELD, filepath=filepath,
#                        field=f1)
#
#        ### Read the row data
#        for row in table:
#            rowdata = {}
#            for f, col in colmap.items ():
#                rowdata [f] = row [col]
#            self [row [0]] = rowdata


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

    db = DBT(schoolyear)
    classes = {}
    with db:
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



class Users:
    """Handle user table for front-end (access control, etc.).
    This probably uses the latest teachers table.
    """
    def __init__(self):
        fpath = Paths.getUserFolder('users')
        self.udb = dbTable(fpath, CONF.TABLES.TEACHER_FIELDNAMES)

    def valid(self, tid):
        return tid in self.udb

    def getHash(self, tid):
        return self.udb[tid]['PASSWORD']

    def permission(self, tid):
        return self.udb[tid]['PERMISSION']

    def name(self, tid):
        return self.udb[tid]['NAME']



##################### Test functions
_testyear = 2016
def test_1():
    filepath = Paths.getYearPath (_testyear, 'FILE_TEACHERDATA')
    fpath = readTeacherTable(_testyear, filepath)
    REPORT.Test("Table from %s entered into database (TEACHERS) for %d"
            % (fpath, _testyear))

def test_2 ():
    REPORT.Test ("Teachers: ID and name")
    tmap = TeacherData (_testyear)
    for tid in tmap:
        REPORT.Test ("  id - name: %s - %s" % (tid, tmap.getTeacherName (tid)))

def test_3 ():
    tmap = TeacherData (_testyear)
    for tid in 'AM', 'nn', 'RP', 'MT':
        REPORT.Test ("\nTeacher %s: %s" % (tid, tmap [tid]))
