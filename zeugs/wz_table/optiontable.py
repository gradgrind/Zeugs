#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_table/optiontable.py

Last updated:  2019-09-28

The function <makeOptionsTable> constructs a 'choice' table for a class.
There is a row for each pupil, a column for each subject.


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

#TODO!!!

import os
from glob import glob
from collections import OrderedDict

from .configuration import Paths
from .courses import CHOSEN_COURSE, INVALID_CELL, TEACHER_PENDING
from wz_table.spreadsheet_new import NewSpreadsheet


def clearNewTables (schoolyear):
    """Remove any "newly created" choice tables – i.e. ones resulting
    directly from calls to <makeOptionsTables>.
    These are in the 'tmp' subfolder, it doesn't refer to those used for
    reading choice information.
    """
    # Determine output folder and file-name mask
    cfpath = Paths.getYearPath (schoolyear, 'FILE_COURSE_OPTIONS')
    # The 'tmp' subfolder
    folder = os.path.join (os.path.dirname (cfpath), 'tmp')
    filemask = os.path.join (folder, os.path.basename (cfpath))
    if os.path.isdir (folder):
        for f in glob (filemask):
            # Remove any existing choice files in the subfolder
            os.remove (f)



def makeOptionsTable (title, schoolyear, klass, pupils, subjects, withStream=True):
    """In order to fit in the subject names, these are written vertically.
    """
    configs = CONF.COURSE_PUPIL_TABLE
    WIDTH_PID = configs.WIDTH_PID.nat ()
    WIDTH_NAME = configs.WIDTH_NAME.nat ()
    WIDTH_STREAM = configs.WIDTH_STREAM.nat ()
    WIDTH_SEP = configs.WIDTH_SEP.nat ()
    WIDTH_NORMAL = configs.WIDTH_NORMAL.nat ()

    HEIGHT_TITLE = configs.HEIGHT_TITLE.nat ()
    HEIGHT_INFO = configs.HEIGHT_INFO.nat ()
    HEIGHT_ROW = configs.HEIGHT_ROW.nat ()
    HEIGHT_CID = configs.HEIGHT_CID.nat ()
    HEIGHT_SBJ = configs.HEIGHT_SBJ.nat ()
    HEIGHT_SEP = configs.HEIGHT_SEP.nat ()

    font = configs.FONT.string ()





    # Configuration info for the options table
    fieldnames = CONF.TABLES.PUPIL_COURSE_FIELDNAMES.flatten ()
    # Sheet name (optional)
    #_sheetname = None

    # Determine output folder and file-name
    cfpath = Paths.getYearPath (courseInfo.schoolyear, 'FILE_COURSE_OPTIONS')
    fname = os.path.basename (cfpath)    # contains '*'
    if _pathoverride:
        folder = _pathoverride
    else:
        # Store the results in a subfolder
        folder = os.path.join (os.path.dirname (cfpath), 'tmp')
    filepath = os.path.join (folder, os.path.basename (cfpath)).replace (
            '*', klass)
    if not os.path.isdir (folder):
        os.makedirs (folder)

    # Get pupil data for the class:
#    pidinfo, sidinfo, pmatrix = courseInfo.optionMatrix (klass)
#    courses = []
#    for sid, info in sidinfo.items ():
#        if info [0]:
#            courses.append (sid)
#    if len (courses) == 0:
#        return False



    # Get existing choice data for the class:
    olddata = courseInfo.readOptionData (klass)




    # Create the new sheet object.
    sheet = NewSpreadsheet (None)
    # Styles:
    titleStyle = getStyle (sheet, font, size=configs.FONT_SIZE_TITLE.nat (),
            align='c', #emph=True,
            border=2)
    tagStyle = getStyle (sheet, font, size=configs.FONT_SIZE_TAG.nat ())
    infoStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='l', border=0)
    v1Style = getStyle (sheet, font, size=configs.FONT_SIZE_TAG.nat (),
            align='b')
    v2Style = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='b')
    h1Style = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='l')
    # This one is for entry fields, allowing editing:
    entryStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='c', unlocked=True)
    # For entries with no choice (invalid pid/sid or compulsory single teacher):
    invalidStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='c', background=configs.INVALID_BG.string ())
    padStyle = getStyle (sheet, None, None,
            border=0, background=configs.SPACER_COLOUR.string ())

    # First column sizes
    sheet.setWidth (0, WIDTH_PID)
    sheet.setWidth (1, WIDTH_NAME)
#TODO: Optional?
    sheet.setWidth (2, WIDTH_STREAM)
    sheet.setWidth (3, WIDTH_SEP)

    ncols = len (courses) + 4
    ### Add title
    sheet.setHeight (0, HEIGHT_TITLE)
    sheet.setCell (0, 0, None, **titleStyle)
    sheet.merge (0, 1, 1, ncols-1)
    sheet.setCell (0, 1, _TITLE, **titleStyle)

    ### Add info lines – here just the class and schoolyear
    sheet.setHeight (1, HEIGHT_INFO)
    sheet.setCell (1, 0, '#', **infoStyle)
    sheet.setCell (1, 1, fieldnames ['%CLASS'], **infoStyle)
    sheet.merge (1, 2, 1, ncols-3)
    sheet.setCell (1, 2, klass, **infoStyle)
    sheet.setHeight (2, HEIGHT_INFO)
    sheet.setCell (2, 0, '#', **infoStyle)
    sheet.setCell (2, 1, fieldnames ['%SCHOOLYEAR'], **infoStyle)
    sheet.merge (2, 2, 1, ncols-3)
    sheet.setCell (2, 2, str (courseInfo.schoolyear), **infoStyle)

    ROWH = 4
    ### Add header lines for the main table
    sheet.setHeight (ROWH-1, HEIGHT_SEP)
    sheet.setHeight (ROWH, HEIGHT_CID)
    sheet.setHeight (ROWH+1, HEIGHT_SBJ)
    sheet.setHeight (ROWH+2, HEIGHT_SEP)

    sheet.setCell (ROWH, 0, fieldnames ['PID'], **tagStyle)
    sheet.setCell (ROWH, 1, fieldnames ['PUPIL'], **tagStyle)
    sheet.setCell (ROWH, 2, fieldnames ['GROUPS'], **tagStyle)
#        sheet.setCell (ROWH+1, 0, fieldnames ['%subject'], **tagStyle)

    COL0 = 4
    r, c = ROWH, COL0
    for sid in courses:
        sheet.setWidth (c, WIDTH_NORMAL)
        sheet.setCell (r, c, sid, **v1Style)
        sheet.setCell (r+1, c, sidinfo [sid] [1], **v2Style)
        c += 1

    ROW0 = ROWH + 3
    r = ROW0
    for pid, png in pidinfo.items ():
        try:
            oldpdata = olddata [pid]
        except:
            oldpdata = None
        sheet.setHeight (r, HEIGHT_ROW)
        sheet.setCell (r, 0, pid, **tagStyle)
        sheet.setCell (r, 1, png [0], **h1Style)    # pupil name
        sheet.setCell (r, 2, png [1], **h1Style)    # pupil groups

        c = COL0
        sid_tids = pmatrix [pid]
        for sid in courses:
            style = entryStyle

            canbenull = False
            try:
                tids = sid_tids [sid]
            except:
                # This subject is not available for this pupil
                vals = [INVALID_CELL]
                style = invalidStyle
            else:
                try:
                    tids.remove (None)
                    # The entry may be empty
                    canbenull = True
                except:
                    pass
                if len (tids) == 1:
                    # No choice of teacher
                    vals = [CHOSEN_COURSE]
                    if not canbenull:
                        style = invalidStyle
                else:
                    vals = [TEACHER_PENDING] + sorted (tids)

            val = vals [0]
            if oldpdata:
                try:
                    val1 = oldpdata [sid]
                    if val1:
                        if val1 in vals:
                            val = val1
                    elif canbenull:
                        val = None
                except:
                    pass

            sheet.setCell (r, c, val,
                    validation=sheet.dataValidation (vals),
                    **style)
            c += 1
        r += 1

    nrows = r

    # Horizontal separator
    r = ROW0 - 1
    for c in range (ncols):
        sheet.setCell (r, c, None, **padStyle)

    # Vertical separator
    c = COL0 - 1
    for rx in range (ROWH, r):
        sheet.setCell (rx, c, None, **padStyle)
    for rx in range (ROW0, nrows):
        sheet.setCell (rx, c, None, **padStyle)

    ### Build the table
    # Set protection on sheet:
    sheet.protectSheet ()
    # Set print sizes:
    sheet.sheetProperties (landscape=False, fitWidth=True, fitHeight=False)
    sheet.save (filepath)
    return True



def getStyle (sheet, font, size, align='c',
        background=None, emph=False, border=1, unlocked=False):
    """
    <sheet> is a <NewSpreadsheet> instance.
    <font> is the name of the font (<None> => default, not recommended,
        unless the cell is to contain no text).
    <size> is the size of the font (<None> => default, not recommended,
        unless the cell is to contain no text).
    <align> is the horizontal (l, c or r) OR vertical (b, m, t) alignment.
        Vertical alignment is for rotated text.
    <background> is a colour in the form 'RRGGBB', default none.
    <emph> is boolean.
    <border>: Only three border types are supported here:
        0: none
        1: all sides
        2: (thicker) underline
    """
    # Build a new style
    styleMap = {}
    # Font
    fstyle = {}
    if font != None:
        fstyle ['name'] = font
    if size != None:
        fstyle ['size'] = size
    if emph:
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

    # Background
    if background:
        styleMap ['bg'] = sheet.background (background)

    # Remove cell protection
    if unlocked:
        styleMap ['locked'] = False

    return styleMap
