### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/gradetable.py - last updated 2020-02-28

Create grade tables for display and grade entry.

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

_FIRSTSIDCOL = 4    # Index (0-based) of first sid column
_UNUSED = '/'      # Subject tag for unused column

# Messages
_MISSING_SUBJECT = "Fachkürzel {sid} fehlt in Notentabellenvorlage:\n  {path}"
_NO_TEMPLATE = "Keine Notentabelle-Vorlage für Klasse/Gruppe {ks} in GRADES.GRADE_TABLE_INFO"
_NO_ITEMPLATE = "Keine Noteneingabe-Vorlage für Klasse/Gruppe {ks} in GRADES.GRADE_TABLE_INFO"


from wz_core.configuration import Paths
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_table.matrix import KlassMatrix
from .gradedata import getGradeData


#TODO: Incorporate info from choice tables?
def makeBasicGradeTable(schoolyear, term, klass, title):
    """Build a basic pupil/subject table for entering grades.
    <klass> is a <Klass> instance.
    <term> is a string.
     """
    # Info concerning grade tables:
    gtinfo = CONF.GRADES.GRADE_TABLE_INFO

    ### Determine table template
    t = klass.match_map(gtinfo.TEMPLATE_GRADE_TABLE)
    if not t:
        REPORT.Fail(_NO_ITEMPLATE, ks=klass)
    template = Paths.getUserPath('FILE_GRADE_TABLE_TEMPLATE').replace('*', t)
    table = KlassMatrix(template)
    table.setTitle(title)
    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass.klass),
        (kmap['TERM'], term)
    )
    table.setInfo(info)

    ### Get ordering information for subjects
    subject_ordering = CONF.GRADES.ORDERING
    grade_subjects = []
    for subject_group in klass.match_map(subject_ordering.CLASSES).split():
        grade_subjects += subject_ordering[subject_group]

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass)
#    print ("???1", list(sid2tlist))
    # Go through the template columns and check if they are needed:
    col = 0
    rowix = table.row0()    # index of header row
    for sid in grade_subjects:
        if sid and sid[0] != '_' and sid in sid2tlist:
            sname = courses.subjectName(sid)
            # Add subject
            col = table.nextcol()
            table.write(rowix, col, sid)
            table.write(rowix + 1, col, sname)
    # Enforce minimum number of columns
    while col < 18:
        col = table.nextcol()
        table.write(rowix, col, None)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    pupils = Pupils(schoolyear)
    for pdata in pupils.classPupils(klass):
        row = table.nextrow()
        pid = pdata['PID']
        table.write(row, 0, pid)
        table.write(row, 1, pdata.name())
        table.write(row, 2, pdata['STREAM'])
    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()


#DEPRECATED?
def makeGradeTable(schoolyear, term, klass, title):
    """Make a grade table for the given school-class/group.
    <klass> is a <Klass> instance.
    <term> is a string.
    """
    # Info concerning grade tables:
    gtinfo = CONF.GRADES.GRADE_TABLE_INFO
    # Determine table template
    t = klass.match_map(gtinfo.GRADE_TABLE_TEMPLATE)
    if not t:
        REPORT.Fail(_NO_TEMPLATE, ks=klass)
    template = Paths.getUserPath('FILE_GRADE_TABLE_TEMPLATE').replace('*', t)
    table = KlassMatrix(template)

    ### Insert general info
    table.setTitle(title)
    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass.klass),
        (kmap['TERM'], term)
    )
    table.setInfo(info)

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass)
#    print ("???1", list(sid2tlist))
    # Go through the template columns and check if they are needed:
    colmap = {}
    col = _FIRSTSIDCOL
    for k in table.headers[_FIRSTSIDCOL:]:
        if k:
            if k in sid2tlist:
                colmap[k] = col
            elif k == _UNUSED:
                table.hideCol(col, True)
            else:
                # Handle extra _tags
                klassmap = gtinfo.get(k)
                if klassmap:
                    m = klass.match_map(klassmap)
                    if m and term in m.split():
                        colmap[k] = col
                    else:
                        table.hideCol(col, True)
                else:
                    table.hideCol(col, True)
        col += 1
#    print("???COLMAP:", colmap)

    ### Add pupils
    pupils = Pupils(schoolyear)
    for pdata in pupils.classPupils(klass):
        row = table.nextrow()
        pid = pdata['PID']
        table.write(row, 0, pid)
        table.write(row, 1, pdata.name())
        table.write(row, 2, pdata['STREAM'])
        # Add existing grades
        gd = getGradeData(schoolyear, pid, term)
#        print("\n???", pid, gd)
        if gd:
            grades = gd['GRADES']
            if grades:
                for k, v in grades.items():
                    try:
                        col = colmap[k]
                    except KeyError:
#                        print("!!! excess subject:", k)
                        continue
                    if k:
                        if k.startswith('__'):
                            # Calculated entry
                            continue
                        table.write(row, col, v)
    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()


#DEPRECATED?
def stripTable(schoolyear, term, klass, title):
    """Build a basic pupil/subject table for entering grades.
    <klass> is a <Klass> instance.
    <term> is a string.
     """
    # Info concerning grade tables:
    gtinfo = CONF.GRADES.GRADE_TABLE_INFO

    ### Determine table template (output)
    t = klass.match_map(gtinfo.GRADE_INPUT_TEMPLATE)
    if not t:
        REPORT.Fail(_NO_ITEMPLATE, ks=klass)
    template = Paths.getUserPath('FILE_GRADE_TABLE_TEMPLATE').replace('*', t)
    table = KlassMatrix(template)
    table.setTitle(title)
    table.setInfo([])

    ### Read input table template (for determining subjects and order)
    # Determine table template (input)
    t = klass.match_map(gtinfo.GRADE_TABLE_TEMPLATE)
    if not t:
        REPORT.Fail(_NO_TEMPLATE, ks=klass)
    template0 = Paths.getUserPath('FILE_GRADE_TABLE_TEMPLATE').replace('*', t)
    table0 = KlassMatrix(template0)
    i, x = 0, 0
    for row0 in table0.rows:
        i += 1
        if row0[0] and row0[0] != '#':
            # The subject key line
            break
    # <row0> is the title row.

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass)
#    print ("???1", list(sid2tlist))
    # Set klass cell
    rowix = table.rowindex - 1
    table.write(rowix, 0, table.headers[0].replace('*', klass.klass))
    # Go through the template columns and check if they are needed:
    col = 0
    for sid in row0:
        if sid and sid[0] != '_' and sid in sid2tlist:
            sname = courses.subjectName(sid)
            # Add subject
            col = table.nextcol()
            table.write(rowix, col, sname)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    pupils = Pupils(schoolyear)
    for pdata in pupils.classPupils(klass):
        row = table.nextrow()
        table.write(row, 0, pdata.name())
        table.write(row, 1, pdata['STREAM'])
    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()



##################### Test functions
_testyear = 2016
def test_01():
    _term = '1'
    for ks in '11.RS-HS-_', '11.Gym','12.RS-HS', '12.Gym', '13':
        klass = Klass(ks)
        bytefile = makeBasicGradeTable(_testyear, _term, klass, "Noten")
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_INPUT', make=-1,
                term=_term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)


    return

    _term = '1'
    for ks in '11.RS-HS-_', '11.Gym','12.RS-HS', '12.Gym', '13':
        klass = Klass(ks)
        bytefile = makeGradeTable(_testyear, _term, klass, "Noten: 1. Halbjahr")
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_FULL', make=-1,
                term=_term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)
        bytefile = stripTable(_testyear, _term, klass, "Noten: 1. Halbjahr")
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_INPUT', make=-1,
                term=_term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)


def test_02():
    return
    _term = '2'
    for ks in '10', '11.Gym', '11.RS-HS-_', '12.RS-HS', '12.Gym', '13':
        klass = Klass(ks)
        bytefile = makeGradeTable(_testyear, _term, klass, "Noten: 1. Halbjahr")
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_FULL', make=-1,
                term=_term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)
        bytefile = stripTable(_testyear, _term, klass, "Noten: 1. Halbjahr")
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_INPUT', make=-1,
                term=_term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)
