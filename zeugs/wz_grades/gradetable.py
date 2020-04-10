### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/gradetable.py - last updated 2020-04-09

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
_TITLE0 = "Noten"
_TITLE = "Noten, bis {date}"
_TITLE2 = "Tabelle erstellt am {time}"
_TTITLE = "Klausurnoten"


# Messages
_MISSING_SUBJECT = "Fachkürzel {sid} fehlt in Notentabellenvorlage:\n  {path}"
_NO_TEMPLATE = ("Keine Notentabelle-Vorlage für Klasse/Gruppe {ks} in"
        " GRADES.TEMPLATE_INFO.GRADE_TABLE")
_NOT_CURRENT_TERM = "Nicht das aktuelle Halbjahr, die Noten werden erscheinen"


import datetime

from wz_core.configuration import Paths, Dates
from wz_core.db import DBT
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_table.matrix import KlassMatrix
from wz_compat.grade_classes import gradeGroups
from .gradedata import getGradeData, CurrentTerm, setGrades


def makeBasicGradeTable(schoolyear, term, klass):
    """Build a basic pupil/subject table containing the grades (initially
    empty).
    <term> is a string (the term number) OR 'T' + test number.
    <klass> is <Klass> instance. If a term table is to be produced, the
    value must be a grade-report group appearing in the list returned
    by <gradeGroups()>.
    """
    title = _TITLE0     # default, minimal title
    # If using old data, a pupil's stream, and even class, may have changed!
    try:
        termdata = CurrentTerm(schoolyear, term)
        gdate = termdata.dates()[str(klass)].GDATE_D
        if gdate:
#TODO: use a date 2 or 3 days earlier?
            title = _TITLE.format(date = Dates.dateConv(gdate))
        plist = None
    except CurrentTerm.NoTerm:
        # A term, but not the current term.
        # Search the GRADES table for entries with TERM == <term> and
        # matching class. Include those with a stream covered by <klass>.
        plist = oldTablePupils(schoolyear, term, klass)

#TODO: That won't do for Klausur results because it only searches
# existing grades- It should probably be more like the code below,
# but maybe also having a concept of "closed" data sets?
    if not plist:
        plist = Pupils(schoolyear).classPupils(klass)
        for pdata in plist:
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
    table.setTitle2(_TITLE2.format(time = datetime.datetime.now().isoformat(
                sep=' ', timespec='minutes')))

    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    if term[0] == 'T':
        info3 = kmap['TEST']
        title = _TTITLE
        t0 = term[1]
    else:
        info3 = kmap['TERM']
        t0 = term
    table.setTitle(title)
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass.klass),
        (info3, t0)
    )
    table.setInfo(info)

    ### Get ordering information for subjects
    subject_ordering = CONF.GRADES.ORDERING
    grade_subjects = []
    for subject_group in klass.match_map(subject_ordering.CLASSES).split():
        grade_subjects += subject_ordering[subject_group]

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass, filter_ = 'GRADE')
#    print ("???1", list(sid2tlist))
    # Go through the template columns and check if they are needed:
    sidcol = []
    col = 0
    rowix = table.row0()    # index of header row
    for sid in grade_subjects:
        try:
            tlist = sid2tlist[sid]
        except KeyError:
            continue
        if tlist.COMPOSITE:
            continue
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
    row = table.nextrow()
    table.delEndRows(row)

    ### Save file
    table.protectSheet()
    return table.save()



def oldTablePupils(schoolyear, term, klass):
    """Search the GRADES table for entries with CLASS <klass.klass>
    and TERM <term>. Include those with a stream covered by <klass>.
    """
    plist = []
    pupils = Pupils(schoolyear)
    with DBT(schoolyear) as db:
        rows = db.select('GRADES', CLASS = klass.klass, TERM = term)
    for row in rows:
        stream = row['STREAM']
        if klass.containsStream(stream):
            pdata = pupils.pupil(row['PID'])
            # Get the grades
            gmap = dict(row)
            setGrades(schoolyear, gmap)
            pdata.grades = gmap['GRADES']
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
    for klass in gradeGroups(_term):
        bytefile = makeBasicGradeTable(_testyear, _term, klass)
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_INPUT', make = -1,
                term = _term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)

def test_02():
    _term = '2'
    for klass in gradeGroups(_term):
        bytefile = makeBasicGradeTable(_testyear, _term, klass)
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_INPUT', make = -1,
                term = _term).replace('*', str(klass).replace('.', '-')) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)
