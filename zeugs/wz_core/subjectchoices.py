# python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/gradetable.py - last updated 2020-02-04

Create subject choice tables.

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

from wz_core.configuration import Paths
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_table.matrix import KlassMatrix


def choiceTable(schoolyear, klass):
    """Build a subject choice table for the given school-class.
    <klass> is a <Klass> instance.
     """
    template = Paths.getUserPath('FILE_SUBJECT_CHOICE_TEMPLATE')
    table = KlassMatrix(template)
    # Title already set in template:
    #table.setTitle("Kurswahl")

    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass.klass),
    )
    table.setInfo(info)

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass)
    # <table.headers> is a list of cell values in the header row.
    rsid = table.rowindex - 1       # row tag for sid
    rsname = table.rowindex         # row tag for subject name
    # Go through the template columns and check if they are needed:
    for sid in sid2tlist:
        if sid[0] != '_':
            sname = courses.subjectName(sid)
            # Add subject
            col = table.nextcol()
            table.write(rsid, col, sid)
            table.write(rsname, col, sname)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    pupils = Pupils(schoolyear)
    for pdata in pupils.classPupils(klass):
        row = table.nextrow()
        table.write(row, 0, pdata['PID'])
        table.write(row, 1, pdata.name())
        table.write(row, 2, pdata['STREAM'])
    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()



##################### Test functions
_testyear = 2016
def test_01():
    klass = Klass('13')
    bytefile = choiceTable(_testyear, klass)
    filepath = Paths.getYearPath(_testyear, 'FILE_SUBJECT_CHOICE_TABLE',
            make=-1).replace('*', str(klass).replace('.', '-')) + '.xlsx'
    with open(filepath, 'wb') as fh:
        fh.write(bytefile)
    REPORT.Test(" --> %s" % filepath)

