#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_grades/grouptables.py

Last updated:  2019-07-13

Handle the spreadsheet tables for grades in class-stream groups.


=+LICENCE=============================
Copyright 2018-2019 Michael Towers

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
_INVALIDBGCOLOUR = "Ungültige Hintergrundfarbe: {val}"
#_MAKEENTRYFORMS = "Noten-Eingabe-Formulare für {date} erstellen"
_BADCHOICE       = ("Klasse {klass}: Ungültiger Eintrag in Fachwahl-Tabelle:\n"
        "   Schüler {pid}, Fach {sid}, Eintrag {tid}")
_PUPILGROUPUNKNOWN = "Klasse {klass}, Schüler {pid}: Gruppen nicht angegeben"
_GROUPFILEFAIL   = "Datei mit Gruppendaten fehlt:\n   {path}"
_BADGROUPLINE    = "Zeile in Gruppendatei ungültig: {text}"


import os
from collections import OrderedDict, UserDict

from wz_core.configuration import Paths
from wz_core.courses import DOTSEP, INVALID_CELL, CourseTables
from wz_table.spreadsheet_new import NewSpreadsheet



def klassStream (klass, stream):
    return klass + '-' + stream if stream else klass

def fromKlassStream (ks):
    try:
        k, s = ks.split ('-')
        return (k, s)
    except:
        return (ks, None)


def getGradeScale (ks0):
    for f in CONF.GRADES.list ():
        if f.startswith ('GRADES_'):
            cf = CONF.GRADES [f]
            for ks in cf.GROUPS:
                if ks == ks0:
                    return cf
    # Default:
    return CONF.GRADES.GRADES


def validGrades (gradeScale):
    return list (gradeScale.VALID)


def getGroups (schoolyear, date):
    """Read the contents of the groups file for the given date.
    """
    fpath = Paths.getYearPath (schoolyear, 'FILE_GROUPS', date=date)
    try:
        with open (fpath) as fh:
            text = fh.read ()
    except:
        # Couldn't read file
        REPORT.Fail (_GROUPFILEFAIL, path=fpath)
        assert False
    groups = {}
    for line in text.splitlines ():
        line = line.strip ()
        if not line: continue
        if line [0] == "#": continue
        try:
            g, d = line.split (":", 1)
        except:
            REPORT.Error (_BADGROUPLINE, text=line)
            continue
        groups [g] = d
    return groups


def makeGradeForm (courseInfo, date, ks, gdate=None, grades=None):
    """Make grade(-entry) table for the given class and stream
    (class-stream) for issue on the given date.
    Only 'real' courses for which grades are to be given are included.
    A table is built containing entries for all the relevant grades.
    <grades> is a mapping: pid -> {sid -> grade}. If this is supplied,
    all included grades will be entered into the resulting table.

    If <grades> is <None>, the resulting files are placed according to
    the 'FILE_GRADE_TABLE_RAW' entry in the PATHS configuration file.
    If <grades> is not <None>, the 'FILE_GRADE_TABLE' entry in PATHS
    is used.
    Return a list of tids of the teachers responsible for grades in this group.
    """
    def getBG (tag):
        """Return a background colour specifier for a cell style.
        <tag> is in the value list of the BG_COLOURS entry in the config
        file.
        """
        try:
            return bgmap [tag]
        except:
            _bg = bgclrs.get (tag)
            if _bg != None:
                _bg = sheet.background (_bg)
            bgmap [tag] = _bg
            return _bg

    def rsep (row):
        """Add a shaded separator row.
        """
        sheet.setHeight (row, HEIGHT_SEP)
        for c in range (ncols):
            sheet.setCell (row, c, None, bg=getBG ('SPACER'), **padStyle)

    configs = CONF.GRADE_ENTRY_TABLE
    WIDTH_PID = configs.WIDTH_PID.nat ()
    WIDTH_NAME = configs.WIDTH_NAME.nat ()
    WIDTH_SEP = configs.WIDTH_SEP.nat ()
    WIDTH_GRADE = configs.WIDTH_GRADE.nat ()

    HEIGHT_TITLE = configs.HEIGHT_TITLE.nat ()
    HEIGHT_INFO = configs.HEIGHT_INFO.nat ()
    HEIGHT_SID = configs.HEIGHT_SID.nat ()
    HEIGHT_SBJ = configs.HEIGHT_SBJ.nat ()
    HEIGHT_ROW = configs.HEIGHT_ROW.nat ()
    HEIGHT_SEP = configs.HEIGHT_SEP.nat ()

    font = configs.FONT

    bgclrs  = {}
    for clr in configs.BG_COLOURS:
        try:
            key, val = clr.split (':')
        except:
            REPORT.Fail (_INVALIDBGCOLOUR, val=clr)
            assert False
        if val:
            bgclrs [key] = val

    # Column labels etc.
    fieldnames = {k: str (v)
            for k, v in CONF.TABLES.GRADETABLE_FIELDNAMES.items ()}
    # Sheet name (optional)
    _sheetname = None

    # Determine output file-path
    if grades==None:
        filepath = Paths.getYearPath (courseInfo.schoolyear,
                'FILE_GRADE_TABLE_RAW',
                date=date, make=-1).replace ('*', ks)
        # Ensure that the folder for completed tables exists
        Paths.getYearPath (courseInfo.schoolyear,
                'FILE_GRADE_TABLE_TEACHER', date=date, make=-1)
    else:
        filepath = Paths.getYearPath (courseInfo.schoolyear,
                'FILE_GRADE_TABLE',
                date=date, make=-1).replace ('*', ks)

    # Get info for this class/stream:
    klass, stream = fromKlassStream (ks)
    sid_name, pmatrix = courseInfo.courseMatrix (klass, date=date, group=stream)

    ### Build spreadsheet file
    bgmap = {}
    vmap = {}
    # Create the new sheet object.
    sheet = NewSpreadsheet (_sheetname)

    # Validation list
    validation = sheet.dataValidation (validGrades (getGradeScale (ks)))

    # Styles:
    titleStyle = getStyle (sheet, font, size=configs.FONT_SIZE_TITLE.nat (),
            align='c', #bold=True,
            border=2)
    tagStyle = getStyle (sheet, font, size=configs.FONT_SIZE_TAG.nat (),
            align='c')
    infoStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='l', border=0)
    hStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='c')
    h2Style = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='b')#, border=0, bold=True)
    entryStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='c')
    padStyle = getStyle (sheet, None, None,
            border=0)

    # Initial column sizes
    sheet.setWidth (0, WIDTH_PID)
    sheet.setWidth (1, WIDTH_NAME)
    sheet.setWidth (2, WIDTH_SEP)
    ncols = 3
    COL0 = ncols
    sids = []
    for sid in sid_name:
        # Filter out non "real" subjects
        if sid in sid_name.nonreal:
            continue
        sids.append (sid)
        sheet.setWidth (ncols, WIDTH_GRADE)
        ncols += 1

    ### Add title
    sheet.setHeight (0, HEIGHT_TITLE)
    sheet.setCell (0, 0, None, **titleStyle)
    sheet.merge (0, 1, 1, ncols-1)
    sheet.setCell (0, 1, fieldnames ['_TITLE'], **titleStyle)
    sheet.setHeight (1, HEIGHT_SEP)

    ### Add info lines
    nrows = 2

    sheet.setHeight (nrows, HEIGHT_INFO)
    sheet.setCell (nrows, 0, '#', **infoStyle)
    sheet.setCell (nrows, 1, fieldnames ['_PGROUP'], **infoStyle)
    sheet.merge (nrows, 2, 1, ncols-2)
    sheet.setCell (nrows, 2, ks, **infoStyle)
    nrows += 1
    # Date of issue
    sheet.setHeight (nrows, HEIGHT_INFO)
    sheet.setCell (nrows, 0, '#', **infoStyle)
    sheet.setCell (nrows, 1, fieldnames ['_ISSUE_D'], **infoStyle)
    sheet.merge (nrows, 2, 1, ncols-2)
    sheet.setCell (nrows, 2, date, **infoStyle)
    nrows += 1
    # Date of grade finalization
    sheet.setHeight (nrows, HEIGHT_INFO)
    sheet.setCell (nrows, 0, '#', **infoStyle)
    sheet.setCell (nrows, 1, fieldnames ['GDATE_D'], **infoStyle)
    sheet.merge (nrows, 2, 1, ncols-2)
    sheet.setCell (nrows, 2, gdate, **infoStyle)
    nrows += 1

    ### Add header lines for the main table
    rsep (nrows)
    nrows += 1
    sheet.setHeight (nrows, HEIGHT_ROW)
    ROWH = nrows
    nrows += 1
    sheet.setHeight (nrows, HEIGHT_SBJ)
    nrows += 1
    sheet.setCell (ROWH, 0, '%id', **hStyle)
    sheet.setCell (ROWH, 1, fieldnames ['%pupil'], **hStyle)
    c = COL0
    for sid in sids:
        sheet.setCell (ROWH, c, sid, **tagStyle)
        sheet.setCell (ROWH+1, c, sid_name [sid], **h2Style)
        c += 1
    rsep (nrows)
    nrows += 1
    ### Pupil rows
    tidset = set ()     # Collect all relevant teacher tags
    for pupilData, pname, sid_tids in pmatrix:
        pid = pupilData.PID
        if stream:
            pgroups = pupilData.GROUPS
            if not pgroups:
                continue
            if stream not in pgroups.split ():
                continue
        sheet.setCell (nrows, 0, pid, **entryStyle)
        sheet.setCell (nrows, 1, pname, **entryStyle)
        c = COL0
        for sid in sids:
            try:
                tids = sid_tids [sid]
            except:
                # No entry
                grade = INVALID_CELL
                v = None
                bg = getBG ('INVALID')
                locked=True
            else:
                tidset.update (tids)
                try:
                    grade = grades [pid] [sid]
                except:
                    grade = None
                v = validation
                bg = None
                locked=False

            sheet.setCell (nrows, c, grade, locked=locked,
                    bg=bg, #number_format='@', (now done in <getStyle>)
                    validation=v, **entryStyle)
            c += 1
        nrows += 1

    ### Column separator(s)
    for r in range (ROWH, nrows):
        sheet.setCell (r, COL0-1, None, bg=getBG ('SPACER'), **padStyle)

    ### Build the table
    # Set protection on sheet, if it is an empty entry sheet:
    if grades==None:
        sheet.protectSheet ()
    # Set print sizes:
    sheet.sheetProperties (landscape=False, fitWidth=True, fitHeight=False)
    fp = sheet.save (filepath)
#############
    print ("*********** SAVED:", filepath)

    return list (tidset)



def getStyle (sheet, font, size, align='c', bold=False, border=1):
    """
    <sheet> is a <NewSpreadsheet> instance.
    <font> is the name of the font (<None> => default, not recommended,
        unless the cell is to contain no text).
    <size> is the size of the font (<None> => default, not recommended,
        unless the cell is to contain no text).
    <align> is the horizontal (l, c or r) OR vertical (b, m, t) alignment.
        Vertical alignment is for rotated text.
    <bold> indicates that the text should be emphasized.
    <border>: Only three border types are supported here:
        0: none
        1: all sides
        2: (thicker) underline
    """
    # Build a new style, all cells marked as text:
    styleMap = {'number_format':'@'}
    # Font
    fstyle = {}
    if font != None:
        fstyle ['name'] = font
    if size != None:
        fstyle ['size'] = size
    if bold:
        fstyle ['bold'] = True
    styleMap ['font'] = sheet.newFont (**fstyle)

    # Alignment
    if align in 'bmt':
        # Vertical
        h = 'c'
        v = align
        rotate = 90
    else:
        h = align
        v = 'm'
        rotate = None
    styleMap ['alignment'] = sheet.alignment (h=h, v=v, rotate=rotate)

    # Border
    if border == 2:
        styleMap ['border'] = sheet.border (left=0, right=0, top=0, bottom=2)
    elif border == 1:
        styleMap ['border'] = sheet.border ()

    return styleMap




##################### Test functions
def test_01 ():
    schoolyear = 2016
    #date = '2016-06-22'
    date = '2016-06-21'
    courseInfo = CourseTables (schoolyear)
    klass = '10'
    stream = 'RS'
    REPORT.PRINT ("\n  >>>>>>>>>>> Class %s: course matrix" % klass)
    sid_name, pdata = courseInfo.courseMatrix (klass, date=date, group=stream)
    REPORT.PRINT ("++++ Subjects: %s\n" % ", ".join (sid_name.values ()))
    for _, pname, sid_tids in pdata:
        REPORT.PRINT ("\n == %s ==\n" % pname, sid_tids)

def test_02 ():
    schoolyear = 2016
    #date = '2016-06-22'
    date = '2016-06-21'
    courseInfo = CourseTables (schoolyear)
    ks = '12-Gym'
    REPORT.PRINT ("\n  >>>>>>>>>>> Group %s" % ks)
    tids = makeGradeForm (courseInfo, date, ks)
    REPORT.PRINT ("\n &&&&& Teachers:\n", tids)

def test_03 ():
    schoolyear = 2016
    #date = '2016-06-22'
    date = '2016-06-21'
    courseInfo = CourseTables (schoolyear)
    for ks in ('10-Gym', '10-RS', '11-Gym', '11-RS', '12-RS', '13'):
        REPORT.PRINT ("\n  >>>>>>>>>>> Group %s" % ks)
        tids = makeGradeForm (courseInfo, date, ks)
        REPORT.PRINT ("\n &&&&& Teachers:\n", tids)
