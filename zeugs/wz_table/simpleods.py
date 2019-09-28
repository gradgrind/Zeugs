#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_table/simpleods.py

Last updated:  2018-09-22

OdsReader:
Read the data from the sheets of an ods file ignoring all formatting/style information.
The content is found in the file "content.xml".

=+LICENCE=============================
Copyright 2017-2018 Michael Towers

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

import zipfile as zf
import io as si
import re

#TODO ...
# Add option to ignore content of covered cells?

_odsContentFile = 'content.xml'
_debug = False

from xml.parsers.expat import ParserCreate


class OdsReader:
    """Uses the expat parser to get at the tables and their data.
    All formatting information is ignored.
    An xml string is parsed to a table of cell values.

    Note that the expat parser converts all items to unicode.

    An instance of the expat parser can only handle a single file, so
    a new instance must be created for each file to be parsed.
    """
    no_covered_cells = None    # Set to <True> to read all covered cells as empty
    _sheets = None
    _rows = None
    _rowcount = None
    _rowrepeat = None
    _cells = None
    _ncols = None
    _cellcount = None
    _celltype = None
    _repeat = None
    _value = None
    _paras = None
    _text = None
    _mergeList = None
    _merge = None

    @classmethod
    def parseXML (cls, xmldata):
        parser = ParserCreate ()

        parser.StartElementHandler = cls._start_element
        parser.EndElementHandler = cls._end_element
        parser.CharacterDataHandler = cls._char_data

        cls._sheets = None
        parser.Parse (xmldata)
        return cls._sheets


    @classmethod
    def show (cls, *args):
        if _debug:
            print (*args)


    @classmethod
    def _cellStart (cls, attrs):
        assert cls._celltype == None
        cls._paras = []
        cls._formula = attrs.get ('table:formula')
        cls._celltype = attrs.get ('office:value-type')
        if cls._celltype == None:
            # Empty cells are handled specially because there can be a
            # very large number of these at the end of a row
            cls._celltype = '__EMPTY__'
            cls._value = None
        elif cls._celltype in ('float', 'percentage', 'currency'):
            value = attrs.get ('office:value')
            if value == None:
                cls._value = None
            else:
                cls._value = float (value)
        elif cls._celltype == 'string':
            cls._value = attrs.get ('office:string-value')
        elif cls._celltype == 'boolean':
            value = attrs.get ('office:boolean-value')
            if value == 'true':
                cls._value = True
            else:
                assert value == 'false'
                cls._value = False
        elif cls._celltype == 'date':
            cls._value = attrs.get ('office:date-value')
        elif cls._celltype == 'time':
            cls._value = attrs.get ('office:time-value')
        else:
            print ("ERROR: unknown cell type:", cls._celltype)
            assert False


    ############ 3 handler functions ############

    @classmethod
    def _start_element(cls, name, attrs):
        cls.show ('>>> Start element:', name, attrs)
        if name == 'table:table-cell' or name == 'table:covered-table-cell':
            cls._repeat = int (attrs.get ("table:number-columns-repeated", 1))
            cls._cellStart (attrs)
            # Note merge information
            cls._merge = (attrs.get ('table:number-rows-spanned'),
                    attrs.get ('table:number-columns-spanned'))

        elif name == 'text:p':
            assert cls._text == None
            cls._text = ""

        elif name == 'table:table-row':
            assert cls._cells == None
            cls._cellcount = 0
            cls._cells = []
            cls._rowrepeat = int (attrs.get ("table:number-rows-repeated", 1))

        elif name == 'table:table':
            assert cls._rows == None
            cls._sheetname = attrs ['table:name']
            cls.show ('\n    --- sheet name: %s\n' % cls._sheetname)
            cls._rows = []
            cls._rowcount = 0
            cls._mergeList = []
            cls._ncols = 0

        elif name == 'office:spreadsheet':
            assert cls._sheets == None
            cls._sheets = []


    @classmethod
    def _end_element(cls, name):
        cls.show ('>>> End element:', name)
        if name == 'table:table-cell' or name == 'table:covered-table-cell':
            # Retrieve merge information
            rs, cs = cls._merge
            # Check whether this is the main cell of a merged range
            if rs or cs:
                cls._mergeList.append ((cls._rowcount, cls._cellcount,
                        int (rs or 1), int (cs or 1)))

            if cls._celltype == '__EMPTY__' and cls._formula != None:
                # Don't count formula cells as empty, even if there is no value,
                # but mark them as empty untyped.
                cls._celltype = None

            if name == 'table:covered-table-cell' and cls.no_covered_cells:
                cls._celltype = '__EMPTY__'

            if cls._celltype != '__EMPTY__':
                # Add skipped empty cells
                while len (cls._cells) < cls._cellcount:
                    # Add an empty cell
                    cls._cells.append (None)

                val = (cls._celltype, cls._value, "\n".join (cls._paras), cls._formula)
                for i in range (cls._repeat):
                    cls._cells.append (val)

            #else:
                # Don't add any cells yet. Wait to see if there are any
                # non-empty calls afterwards.

            cls._cellcount += cls._repeat
            cls._celltype = None
            cls._repeat = None
            cls._paras = None

        elif name == 'text:p':
            assert cls._text != None
            if cls._paras != None:
                cls._paras.append (cls._text)
            cls._text = None

        elif name == 'table:table-row':
            if cls._cells:
                # The row is not empty: add skipped empty rows
                while len (cls._rows) < cls._rowcount:
                    # Add an empty row
                    cls._rows.append ([])

                for i in range (cls._rowrepeat):
                    cls._rows.append (cls._cells)

                nc = len (cls._cells)
                if nc > cls._ncols:
                    cls._ncols = nc

            # else:
            #     Don't add any rows yet. Wait to see if there are any
            #     non-empty rows afterwards.

            cls._rowcount += cls._rowrepeat
            cls._cells = None

        elif name == 'table:table':
            # Equalise the row lengths
            for row in cls._rows:
                while len (row) < cls._ncols:
                    row.append (None)

            cls._sheets.append ((cls._sheetname, cls._rows, cls._mergeList))
            cls._sheetname = None
            cls._rows = None
            cls._rowcount = None
            cls._mergeList = None


    @classmethod
    def _char_data(cls, data):
        cls.show ('>>> Character data:', type (data), repr(data))
        if cls._sheets != None:
            # Only while parsing the data of a sheet is <cls._text> not <None>
            # but this method can also be called at other places, where
            # the data is of no interest.
            cls._text += data

    ############ end handler functions ############


    @classmethod
    def readOdsFile (cls, filepath, ignoreCoveredCells=False):
        cls.no_covered_cells = ignoreCoveredCells
        xmldata = cls._getOdsContent (filepath)
        return cls.parseXML (xmldata)


    @staticmethod
    def _getOdsContent (filepath):
        """Returns the content xml file – I assume always bytes encoded as utf-8.
        """
        with zf.ZipFile (filepath) as zipfile:
            xmlbytes = zipfile.read (_odsContentFile)
        return xmlbytes


    @classmethod
    def readFile (cls, xmlfile):
        with open (xmlfile, "rb") as fi:
            xmldata = fi.read ()
        return cls.parseXML (xmldata)
