### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/gradetable.py - last updated 2020-03-16

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

# Title for grade tables
_TITLE = "Noten, Abgabe bis {date}"
_TITLE1 = "Noten zu {time}"


# Messages
_MISSING_SUBJECT = "Fachkürzel {sid} fehlt in Notentabellenvorlage:\n  {path}"
_NO_TEMPLATE = ("Keine Notentabelle-Vorlage für Klasse/Gruppe {ks} in"
        " GRADES.TEMPLATE_INFO.GRADE_TABLE")
_NOT_CURRENT_TERM = "Nicht aktuelles Halbjahr"


import datetime

from wz_core.configuration import Paths, Dates
from wz_core.db import DB
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_table.matrix import KlassMatrix
from wz_compat.grade_classes import getCurrentTerm, gradeGroups
from .gradedata import getGradeData, grades2map


def makeBasicGradeTable(schoolyear, term, klass, withgrades = False):
    """Build a basic pupil/subject table for entering grades.
    <klass> is a <Klass> instance, which can include one or more streams.
    <term> is a string (the term number).
    If <withgrades> is true, any existing grades (in the database) will
    be entered into the table.
     """
    # If using old data, a pupil's stream, and even class, may have changed!
    try:
        t, d = getCurrentTerm(schoolyear)
        if t != term:
            raise ValueError
    except:
        if withgrades:
            # Search within <klass.klass> for <term>, include those with
            # a stream covered by <klass>
            plist = oldTablePupils(schoolyear, term, klass)
        else:
            REPORT.Error(_NOT_CURRENT_TERM)
            return None
    else:
        plist = Pupils(schoolyear).classPupils(klass)
        for pdata in plist:
            if withgrades:
                gdata = getGradeData(schoolyear, pdata['PID'], term)
                if gdata:
                    if (gdata['CLASS'] == klass.klass and
                            gdata['STREAM'] == pdata['STREAM']):
                        pdata.grades = gdata['GRADES']
                        continue
            pdata.grades = None

    ### Determine table template
    gtinfo = CONF.GRADES.TEMPLATE_INFO
    t = klass.match_map(gtinfo.GRADE_TABLE)
    if not t:
        REPORT.Fail(_NO_TEMPLATE, ks = klass)
    template = Paths.getUserPath('FILE_GRADE_TABLE_TEMPLATE').replace('*', t)
    table = KlassMatrix(template)
    if withgrades:
        title = _TITLE1.format(time = datetime.datetime.now().isoformat(
                sep=' ', timespec='minutes'))
    else:
        title = _TITLE.format(date = Dates.dateConv(d))
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
    sidcol = []
    col = 0
    rowix = table.row0()    # index of header row
    for sid in grade_subjects:
        if sid and sid[0] != '_' and sid in sid2tlist:
            sname = courses.subjectName(sid)
            # Add subject
            col = table.nextcol()
            sidcol.append((sid, col))
            table.write(rowix, col, sid)
            table.write(rowix + 1, col, sname)
    # Enforce minimum number of columns
    while col < 18:
        col = table.nextcol()
        table.write(rowix, col, None)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    for pdata in plist:
        row = table.nextrow()
        pid = pdata['PID']
        table.write(row, 0, pid)
        table.write(row, 1, pdata.name())
        table.write(row, 2, pdata['STREAM'])
        if pdata.grades:
            for sid, col in sidcol:
                g = pdata.grades.get(sid)
                if g:
                    table.write(row, col, g)

    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()



def oldTablePupils(schoolyear, term, klass):
    """Search within <klass.klass> for <term>, include those with
    a stream covered by <klass>.
    """
    plist = []
    pupils = Pupils(schoolyear)
    for row in DB(schoolyear).select('GRADES',
            CLASS = klass.klass, TERM = term):
        stream = row['STREAM']
        if klass.containsStream(stream):
            pdata = pupils.pupil(row['PID'])
            pdata.grades = grades2map(row['GRADES'])
            # In case class or stream have changed:
            pdata['CLASS'] = klass.klass
            pdata['STREAM'] = stream
            plist.append(pdata)
    plist.sort(key=lambda pdata: pdata['PSORT'])
    return plist



##################### Test functions
_testyear = 2016
def test_01():
    _term = '1'
    for ks in gradeGroups(_term):
        klass = Klass(ks)
        bytefile = makeBasicGradeTable(_testyear, _term, klass, withgrades = True)
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_INPUT', make = -1,
                term = _term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)

def test_02():
    _term = '2'
    for ks in gradeGroups(_term):
        klass = Klass(ks)
        bytefile = makeBasicGradeTable(_testyear, _term, klass, withgrades = True)
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_INPUT', make = -1,
                term = _term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)
