#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_table/optiontable.py

Last updated:  2019-09-29

The function <makeOptionsTable> constructs a matrix with the "subjects"
as columns and the pupils as rows.


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

import os, shutil
from glob import glob
from collections import OrderedDict

from wz_core.configuration import Paths
from .spreadsheet_new import NewSpreadsheet
from .dbtable import readDBTable, digestDBTable


def makeOptionsTable (title, schoolyear, klass, pupils, subjects,
        filetag, infolines=None, withStream=True):
    """<pupils> is a list of <PupilData> instances.
    <subjects> is a list of (sid, subject name) pairs.
    <filetag> is an entry in the PATHS config file, which may contain '*'
    (which will be replaced by the class).
    <infolines> can be used to supply a mapping ({key->value}) of
    additional info-lines. School year and class will be included
    automatically.
    If <withStream> is true, the pupils will have a stream field.
    In order to fit the subject names in narrow columns, these are
    written vertically.
    """
    configs = CONF.COURSE_PUPIL_TABLE
    WIDTH_PID = configs.WIDTH_PID.nat ()
    WIDTH_NAME = configs.WIDTH_NAME.nat ()
    WIDTH_STREAM = configs.WIDTH_STREAM.nat ()
    WIDTH_SEP = configs.WIDTH_SEP.nat ()
    WIDTH_ENTRY = configs.WIDTH_ENTRY.nat ()

    HEIGHT_TITLE = configs.HEIGHT_TITLE.nat ()
    HEIGHT_INFO = configs.HEIGHT_INFO.nat ()
    HEIGHT_ROW = configs.HEIGHT_ROW.nat ()
    HEIGHT_ID = configs.HEIGHT_ID.nat ()
    HEIGHT_SBJ = configs.HEIGHT_SBJ.nat ()
    HEIGHT_SEP = configs.HEIGHT_SEP.nat ()

    font = configs.FONT

    # Configuration info for the options table
    fieldnames = CONF.TABLES.COURSE_PUPIL_FIELDNAMES

    filepath = Paths.getYearPath (schoolyear, filetag,
            make=-1).replace ('*', klass)
    try:
        _oldtable = readDBTable (filepath)
        oldtable = digestDBTable (_oldtable, fieldnames)
        # Backup old table
        shutil.copyfile(_oldtable.filepath, _oldtable.filepath + '.bak')
    except:
        oldtable = None

    # Create the new sheet object.
    sheet = NewSpreadsheet (None)

    # Styles:
    titleStyle = getStyle (sheet, font, size=configs.FONT_SIZE_TITLE.nat (),
            align='c', #emph=True,
            border=2)
    tagStyle = getStyle (sheet, font, size=configs.FONT_SIZE_TAG.nat ())
    infoStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='l', border=0)
#    v1Style = getStyle (sheet, font, size=configs.FONT_SIZE_TAG.nat (),
#            align='b')
    vStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='b')
    h1Style = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='l')
    # This one is for entry fields, allowing editing:
    entryStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
            align='c', unlocked=True)
#    # For entries with no choice (invalid pid/sid or compulsory single teacher):
#    invalidStyle = getStyle (sheet, font, size=configs.FONT_SIZE.nat (),
#            align='c', background=configs.INVALID_BG)
    padStyle = getStyle (sheet, None, None,
            border=0, background=configs.SPACER_COLOUR)

    # First column sizes
    sheet.setWidth (0, WIDTH_PID)
    sheet.setWidth (1, WIDTH_NAME)
    col = 2
    if withStream:
        sheet.setWidth (col, WIDTH_STREAM); col += 1
    sheet.setWidth (col, WIDTH_SEP); col += 1
    ncols = len (subjects) + col

    ### Add title
    sheet.setHeight (0, HEIGHT_TITLE)
    sheet.setCell (0, 0, None, **titleStyle)
    sheet.merge (0, 1, 1, ncols-1)
    sheet.setCell (0, 1, title, **titleStyle)
    row = 1

    ### Add info lines
    info = [(fieldnames ['SCHOOLYEAR'], str (schoolyear)),
            (fieldnames ['CLASS'], klass)]
    if infolines:
        info += [(k, v) for k, v in infolines.items ()]
    for k, v in info:
        sheet.setHeight (row, HEIGHT_INFO)
        sheet.setCell (row, 0, '#', **infoStyle)
        sheet.setCell (row, 1, k, **infoStyle)
        sheet.merge (row, 2, 1, ncols-3)
        sheet.setCell (row, 2, v, **infoStyle)
        row += 1

    ### Add header lines for the main table
    sheet.setHeight (row, HEIGHT_SEP); row += 1
    sheet.setHeight (row, HEIGHT_ID)
    sheet.setHeight (row+1, HEIGHT_SBJ)
    sheet.setHeight (row+2, HEIGHT_SEP)
    # headers for the pupils
    sheet.setCell (row, 0, fieldnames ['PID'], **tagStyle)
    sheet.setCell (row, 1, fieldnames ['PUPIL'], **tagStyle)
    sheet.setCell (row, 2, fieldnames ['STREAM'], **tagStyle)
    # headers for the subjects
    COL0 = col
    ROWH, ROW0 = row, row + 3
    c = COL0
    for sid, sname in subjects:
        sheet.setWidth (c, WIDTH_ENTRY)
        sheet.setCell (ROWH, c, sid, **tagStyle)
        sheet.setCell (ROWH+1, c, sname, **vStyle)
        c += 1

    ### Add the pupil lines
    r = ROW0
    for pdata in pupils:
        pid = pdata ['PID']
        sheet.setHeight (r, HEIGHT_ROW)
        sheet.setCell (r, 0, pid, **tagStyle)           # pid
        sheet.setCell (r, 1, pdata.name (), **h1Style)  # pupil name
        if withStream:
            sheet.setCell (r, 2, pdata ['STREAM'], **h1Style)   # stream

        try:
            oldvals = oldtable [pid]
        except:
            oldvals = None

        c = COL0
        for sid, sname in subjects:
            try:
                val = oldvals [sid]
            except:
                val = None
            sheet.setCell (r, c, val, **entryStyle)
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
    return filepath



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
    styleMap = {'number_format':'@'}
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
