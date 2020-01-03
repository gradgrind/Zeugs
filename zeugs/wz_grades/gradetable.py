# python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/gradetable.py - last updated 2020-01-03

Create attendance table for a class.

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
_TOO_MANY_INFOLINES = "Zu viele Infozeilen ('#, ...'), {n} erforderlich, in:\n  {path}"
_TOO_FEW_INFOLINES = "Zu wenige Infozeilen ('#, ...'), {n} erforderlich, in:\n  {path}"
_MISSING_SUBJECT = "Fachkürzel {sid} fehlt in Notentabellenvorlage:\n  {path}"
_NO_TEMPLATE = "Keine Notentabellenvorlage für Klasse/Gruppe {ks} in GRADES.GRADE_TABLE_INFO"


import datetime
#import os
#from collections import OrderedDict
#from copy import copy

from openpyxl import load_workbook
from openpyxl.worksheet.properties import WorksheetProperties, PageSetupProperties
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.styles import Alignment, Border, Side, PatternFill, NamedStyle

from wz_core.configuration import Paths #, ConfigFile
from wz_core.pupils import Pupils, fromKlassStream, match_klass_stream
from wz_core.courses import CourseTables
from .gradedata import getGradeData


class Table:
    """openpyxl based spreadsheet handler ('.xlsx'-files).
    """
    def __init__(self, filepath):
        self._wb = load_workbook(filepath + '.xlsx')
        self.rows = []
        for row in self._wb.active.iter_rows():
            values = []
            for cell in row:
                v = cell.value
                if isinstance(v, datetime.datetime):
                    v = v.strftime ("%Y-%m-%d")
                elif isinstance(v, str):
                    v = v.strip ()
                    if v == '':
                         v = None
                elif v != None:
                    v = str (v)
                values.append (v)
            self.rows.append (values)


    def getCell (self, celltag):
        return self._wb.active [celltag].value


    def setCell (self, celltag, value=None, style=None):
        cell = self._wb.active [celltag]
        cell.value = value
        if style:
            cell.style = style

    def hideCol(self, index, clearheader=None):
        """Hide the given column (0-indexed).
        <clearheader> is the row number (1-based) of a cell to be cleared.
        """
        letter = get_column_letter(index+1)
#TODO: disabled pending hidden column fix ...
#        self._wb.active.column_dimensions[letter].hidden = True
        if clearheader:
            # Clear any existing "subject"
            self.setCell(letter + str(clearheader))
            self.setCell(letter + str(clearheader+1))


#    def getRowHeight (self, row):
#        return self._wb.active.row_dimensions [row].height


#    def setRowHeight (self, row, height):
#        self._wb.active.row_dimensions [row].height = height


#    def mergeCells (self, crange):
#        """The row and column indexes are 1-based,
#        """
#        self._wb.active.merge_cells (crange)


#?
    def page_setup (self, sheet, landscape=False, fitHeight=False, fitWidth=False):
        ws = self._getTable (sheet)
        ws.page_setup.orientation = (ws.ORIENTATION_LANDSCAPE if landscape
                else ws.ORIENTATION_PORTRAIT)
        if fitHeight or fitWidth:
            wsprops = ws.sheet_properties
            wsprops.pageSetUpPr = PageSetupProperties (fitToPage=True)
#            ws.page_setup.fitToPage = True
            if not fitHeight:
                ws.page_setup.fitToHeight = False
            elif not fitWidth:
                ws.page_setup.fitToWidth = False


    def protectSheet (self, pw=None):
        if pw:
            self._wb.active.protection.set_password (pw)
        else:
            self._wb.active.protection.enable ()


    def save (self, filepath):
        self._wb.save (filepath + '.xlsx')



def makeGradeTable(schoolyear, term, klass_stream, title):
    # Info concerning grade tables:
    gtinfo = CONF.GRADES.GRADE_TABLE_INFO
    # Determine table template
    t = match_klass_stream(klass_stream, gtinfo.GRADE_TABLE_TEMPLATE)
    if not t:
        REPORT.Fail(_NO_TEMPLATE, ks=klass_stream)
    template = Paths.getUserPath('FILE_GRADE_TABLE_TEMPLATE').replace('*', t)
    table = Table(template)

    ### Insert general info
    klass, stream = fromKlassStream(klass_stream)
    table.setCell('B1', title)
    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass),
        (kmap['TERM'], term)
    )
    i, x = 0, 0
    for row in table.rows:
        i += 1
        if row[0] == '#':
            try:
                k, v = info[x]
            except IndexError:
                REPORT.Fail(_TOO_MANY_INFOLINES, n=len(info), path=template)
            x += 1
            table.setCell('B%d' % i, k)
            table.setCell('C%d' % i, v)
        elif row[0]:
            # The subject key line
            break
    if x < len(info):
        REPORT.Fail(_TOO_FEW_INFOLINES, n=len(info), path=template)
    # <row> is the title row, <i> is the row index of the next row (0-based).

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass)
#    print ("???1", list(sid2tlist))
    # Go through the template columns and check if they are needed:
    colmap = {}
    col = _FIRSTSIDCOL
    for k in row[_FIRSTSIDCOL:]:
        if k:
            if k in sid2tlist:
                colmap[k] = col
            elif k == _UNUSED:
                table.hideCol(col, i)
            else:
                # Handle extra _tags
                klassmap = gtinfo.get(k)
                if klassmap:
                    m = match_klass_stream(klass_stream, klassmap)
                    if m and term in m.split():
                        colmap[k] = col
                    else:
                        table.hideCol(col, i)
                else:
                    table.hideCol(col, i)
        col += 1
#    print("???COLMAP:", colmap)

    ### Add pupils
    # Find first non-empty line start
    while True:
        i += 1
        if table.getCell('A' + str(i)):
            break
    pupils = Pupils(schoolyear)
    for pdata in pupils.classPupils(klass_stream):
        pid = pdata['PID']
        table.setCell('A' + str(i), pid)
        table.setCell('B' + str(i), pdata.name())
        table.setCell('C' + str(i), pdata['STREAM'])
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
                        table.setCell(get_column_letter(col+1) + str(i), v)
        i += 1

    ### Save file
    table.protectSheet()
    filepath = Paths.getYearPath(schoolyear, 'FILE_GRADE_FULL', make=-1,
                term=term).replace('*', klass_stream.replace('.', '-'))
    table.save(filepath)




##################### Test functions
_testyear = 2016
def test_01():
    for ks in '11', '12.RS', '12.Gym', '13':
        makeGradeTable(_testyear, '1', ks, "Noten: Einsendeschluss 15.01.2016")

def test_02():
    for ks in '10', '11', '11.Gym', '11.RS', '12.RS', '12.Gym', '13':
        makeGradeTable(_testyear, '2', ks, "Noten: Einsendeschluss 10.06.2016")
