#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_table/dbtable.py

Last updated:  2019-09-22

Read and write a database-like table using a spreadsheet file (xlsx).
Each file has fields and rows, like a relational db, but there may also
be additional key-value lines at the head of the table.

=+LICENCE=============================
Copyright 2019 Michael Towers

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

from collections import UserList, OrderedDict

from .spreadsheet import Spreadsheet
from .spreadsheet_new import NewSpreadsheet


def readDBTable (filepath):
    sheet = Spreadsheet (filepath, mustexist=False)
    rows = UserList ()
    rows.info = OrderedDict ()

    headers = None
    for rowix in range (sheet.colLen ()):
        # Get the value in the first column
        entry1 = sheet.getValue (rowix, 0)
        if not entry1:
            continue
        if headers == None:
            if entry1 == '#':
                key = sheet.getValue (rowix, 1)
                val = sheet.getValue (rowix, 2)
                rows.info [key] = val
                continue

            # Read the column headers from this line
            headers = OrderedDict ()
            rows.headers = OrderedDict ()
            i, j = 0, 0
            for cellix in range (sheet.rowLen ()):
                h = sheet.getValue (rowix, cellix)
                if h:
                    headers [h] = i
                    rows.headers [h] = j
                    j += 1
                i += 1
            continue

        ### Read the row data
        rowdata = []
        for col in headers.values ():
            try:
                rowdata.append (sheet.getValue (rowix, col))
            except:
                rowdata.append (None)
        rows.append (rowdata)

    return rows


def makeDBTable (filepath, title, fields, values, kvpairs=None):
    """Create a spreadsheet containing the supplied data, rather as it
    would be stored in a database table. However, there is also a title
    line and there can be key-value lines at the head of the table,
    before the line with the field names.
    Normal table lines may not have empty first columns: such lines are
    ignored.
    The key-value lines are marked by '#' in the first column.

    The table data (<values>) is supplied as a list of line data. Each line
    is a list/tuple of the field values (in the correct order).
    The field names are provided as a separate list, <fields>.
    Also a title should be provided, as <title>.
    A number of key-value pairs may also, optionally, be provided as a
    list (<kvpairs>:
        [(key, value), ... ]
    """
    sheet = NewSpreadsheet (None)
    sheet.setCell (0, 0, None)
    sheet.setCell (0, 1, title)

    row = 2
    if kvpairs:
        for k, v in kvpairs:
            sheet.setCell (row, 0, '#')
            sheet.setCell (row, 1, k)
            sheet.setCell (row, 2, v)
            row += 1
    row += 1
    col = 0
    for f in fields:
        sheet.setCell (row, col, f)
        col += 1

    row += 2
    for vrow in values:
        if vrow == None:
            # Empty line
            row += 1
            continue
        col = 0
        for v in vrow:
            sheet.setCell (row, col, v)
            col += 1
        row += 1

    sheet.save (filepath)
