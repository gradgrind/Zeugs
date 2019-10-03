#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_table/formattedmatrix.py

Last updated:  2019-10-02

Handles creation of spreadsheet tables having "subjects" as columns and
pupils as rows.


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
from .spreadsheet_make import NewSpreadsheet
from .dbtable import readDBTable, digestDBTable



class FormattedMatrix:
    def __init__ (self, schoolyear, filetag, klass=None, **kargs):
        """<filetag> is an entry in the PATHS config file, which may
        contain '*' (which will be replaced by the class).
        If the file exists already, the values will be available
        at <self.matrix> (otherwise <None>).
        """
        self.schoolyear = schoolyear
        self.klass = klass
        self._stylenum = 0      # internal tag for additional entry styles
        self.entrystyles = []   # list of additional entry styles
        # Configuration info for the options table
        self.fieldnames = CONF.TABLES.COURSE_PUPIL_FIELDNAMES

        self.filepath = Paths.getYearPath (schoolyear, filetag,
                make=-1, **kargs).replace ('*', klass)
        try:
            self._oldtable = readDBTable (self.filepath)
            self.matrix = digestDBTable (self._oldtable, self.fieldnames)
        except:
            self._oldtable = None
            self.matrix = None


    def getValues (self):
        return self.matrix


    @classmethod
    def readMatrix (cls, schoolyear, filetag, klass, **kargs):
        """A convenience method for reading a table for a particular class.
        """
        fm = cls (schoolyear, filetag, klass, **kargs)
        return fm.matrix


    def newEntryStyle (self, stylemap):
        """Declare extra parameter values for an entry style.
        <stylemap> is a mapping with the new paramter values.
        The mapping is given a name tag to identify it.
        """
        self._stylenum += 1
        stylemap ["__tag__"] = "EntryStyle%02d" % self._stylenum
        self.entrystyles.append (stylemap)
        return stylemap


    def build (self, title, pupils, subjects,
            values=None, cellstyles=None, infolines=None, withStream=True):
        """<title> is a string appearing in the first line.
        <pupils> is a list of <PupilData> instances.
        <subjects> is a list of (sid, subject name) pairs.
        <values> ...
        <cellstyles> ...
        <infolines> can be used to supply a mapping ({key->value}) of
        info-lines. The school year is included automatically. If a class
        is supplied, that will also be included automatically.
        If <withStream> is true, the pupils will have a stream field.
        In order to fit the subject names in narrow columns, these are
        written vertically.
        If there is an existing table, the old file will be
        backed up (by getting an extra '.bak' on the extension)
        """
        if self._oldtable:
            # Backup old table
            shutil.copyfile (self._oldtable.filepath,
                    self._oldtable.filepath + '.bak')
        if values == None:
            values = self.matrix
        # Cell size configuration values
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

        # Create the new sheet object.
        self.sheet = NewSpreadsheet ()

        # Styles:
        font = configs.FONT
        titleStyle = self.sheet.getStyle (font=(font,
                configs.FONT_SIZE_TITLE.nat (), None, None, None),
                align='c',
                border=2)
        tagStyle = self.sheet.getStyle (font=(font,
                configs.FONT_SIZE_TAG.nat (), None, None, None))
        font0 = (font, configs.FONT_SIZE.nat (), None, None, None)
        infoStyle = self.sheet.getStyle (font=font0, align='l', border=0)
        vStyle = self.sheet.getStyle (font=font0, align='b')
        h1Style = self.sheet.getStyle (font=font0, align='l')
        # For entries with no choice:
        invalidStyle = self.sheet.getStyle (font=font0,
                align='c', background=CONF.COLOURS.INVALID)
        padStyle = self.sheet.getStyle (border=0,
                background=CONF.COLOURS.SPACER)
        # This one is for entry fields, allowing editing:
        entryStyle = self.sheet.getStyle (font=font0,
                align='c', valid=True)

        # Further entry styles
        entryStyles = {}
        for stylemap in self.entrystyles:
            entryStyles [stylemap ['__tag__']] = self.sheet.getStyle (
                    base=entryStyle, **stylemap)

        # First column sizes
        self.sheet.setWidth (0, WIDTH_PID)
        self.sheet.setWidth (1, WIDTH_NAME)
        col = 2
        if withStream:
            self.sheet.setWidth (col, WIDTH_STREAM); col += 1
        self.sheet.setWidth (col, WIDTH_SEP); col += 1
        ncols = len (subjects) + col

        ### Add title
        self.sheet.setHeight (0, HEIGHT_TITLE)
        self.sheet.setCell (0, 0, None, titleStyle)
        self.sheet.merge (0, 1, 1, ncols-1)
        self.sheet.setCell (0, 1, title, titleStyle)
        row = 1

        ### Add info lines
        info = [(self.fieldnames ['SCHOOLYEAR'], str (self.schoolyear))]
        if self.klass:
            info.append ((self.fieldnames ['CLASS'], self.klass))
        if infolines:
            info += [(k, v) for k, v in infolines.items ()]
        for k, v in info:
            self.sheet.setHeight (row, HEIGHT_INFO)
            self.sheet.setCell (row, 0, '#', infoStyle)
            self.sheet.setCell (row, 1, k, infoStyle)
            self.sheet.merge (row, 2, 1, ncols-3)
            self.sheet.setCell (row, 2, v, infoStyle)
            row += 1

        ### Add header lines for the main table
        self.sheet.setHeight (row, HEIGHT_SEP); row += 1
        self.sheet.setHeight (row, HEIGHT_ID)
        self.sheet.setHeight (row+1, HEIGHT_SBJ)
        self.sheet.setHeight (row+2, HEIGHT_SEP)
        # headers for the pupils
        self.sheet.setCell (row, 0, self.fieldnames ['PID'], tagStyle)
        self.sheet.setCell (row, 1, self.fieldnames ['PUPIL'], tagStyle)
        self.sheet.setCell (row, 2, self.fieldnames ['STREAM'], tagStyle)
        # headers for the subjects
        COL0 = col
        ROWH, ROW0 = row, row + 3
        c = COL0
        for sid, sname in subjects:
            self.sheet.setWidth (c, WIDTH_ENTRY)
            self.sheet.setCell (ROWH, c, sid, tagStyle)
            self.sheet.setCell (ROWH+1, c, sname, vStyle)
            c += 1

        ### Add the pupil lines
        r = ROW0
        for pdata in pupils:
            pid = pdata ['PID']
            self.sheet.setHeight (r, HEIGHT_ROW)
            self.sheet.setCell (r, 0, pid, tagStyle)           # pid
            self.sheet.setCell (r, 1, pdata.name (), h1Style)  # pupil name
            if withStream:
                self.sheet.setCell (r, 2, pdata ['STREAM'], h1Style)   # stream

            try:
                vals = values [pid]
            except:
                vals = None
            try:
                pstyles = cellstyles [pid]
            except:
                pstyles = None

            c = COL0
            for sid, sname in subjects:
                try:
                    val = vals [sid]
                except:
                    val = None
                try:
                    s = pstyles [sid]
                    style = entryStyles [s ['__tag__']] if s else invalidStyle
                except:
                    style = entryStyle
                self.sheet.setCell (r, c, val, style)
                c += 1
            r += 1

        nrows = r

        # Horizontal separator
        r = ROW0 - 1
        for c in range (ncols):
            self.sheet.setCell (r, c, None, padStyle)

        # Vertical separator
        c = COL0 - 1
        for rx in range (ROWH, r):
            self.sheet.setCell (rx, c, None, padStyle)
        for rx in range (ROW0, nrows):
            self.sheet.setCell (rx, c, None, padStyle)

        # "Freeze" header area
        self.sheet.freeze (ROW0, COL0)


    def save (self):
        # Set protection on sheet:
        self.sheet.protectSheet ()
        # Set print sizes:
        self.sheet.sheetProperties (landscape=False, fitWidth=True, fitHeight=False)
        self.sheet.save (self.filepath)
        return self.filepath
