#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#DEPRECATED – at least in part ...
"""
wz_grades/makeabireports.py

Last updated:  2019-10-03

1) Generate empty grade tables for an abitur class.
2) Use completed grade tables to produce final grade reports for the class.

These functions use templates: xlsx for the tables, odt for the reports.
The reasons for these choices – and the "mixed standards":
 – Support under python: openpyxl provides really good support for xlsx
   spreadsheets. There is no equivalent for ods.
 – The tables are passed to other people. xlsx might be a bit better
   supported than ods.
 – For reading in tabular data, both xlsx and ods are supported.

 – The odt files (report templates) are primarily used internally, not
   normally passed to other people. The formatting and layout are critical
   here. Other programs may produce slight (or not so slight) differences.
   It is also important to have the correct fonts installed.
 – The odt files are converted to pdf using LibreOffice. Although
   LibreOffice can also read other file formats, the layout might suffer
   if a non-native format is used.
 – Using "userfields" for item substitution is relatively easy in odt.


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

# Messages
_BADSEXFIELD = "Klasse {klass}: ungültiges Geschlecht ({sex}) für {pname}"
_NOTNCOURSES = "Klasse {klass}: {pname} hat {n:d} Kurse ({nc0} erwartet)"
_MADENTABLES = "Klasse {klass}: {n} Ergebnistabellen erstellt"
_ABITABLE_EXISTS = "Klasse {klass}: Ergebnistabelle für {pname} existiert schon"
_MADENREPORTS = "Klasse {klass}: {n} Abiturzeugnisse wurden erstellt in:\n  {folder}"
_MADENPDFS = "{n} pdf-Dateien wurden erstellt in:\n  {folder}"
_ABIREPORTDONE = "Abizeugnis fertig: {path}"


import os, shutil
from glob import glob

from wz_core.configuration import Paths, Dates
from wz_core.courses import CourseTables
from wz_core.pupils import Pupils
from wz_table.formattedmatrix import FormattedMatrix
from wz_table.spreadsheet import Spreadsheet
from wz_table.spreadsheet_template import XLS_template
from wz_textdoc.simpleodt import OdtUserFields
from wz_io.support import toPdf


def readTableData (filepath, table=None):
    """Read (key, value) pairs from the table at the given path (xlsx or ods).
    The type-ending need not be supplied.
    If <table> is provided, it is the name of the sheet to be read.
    Otherwise the first sheet will be read.
    All values are strings. The cells may contain formulae, in which case
    the values will be read, not the formulae.
    Return the data as a mapping.
    """
    kvmap = {}
    ss = Spreadsheet (filepath)
    if table != None:
        ss.setTable (table)
    for row in range (ss.colLen ()):
        key = ss.getValue (row, 0)
        if (not key) or (key == '#'):
            continue
        value = ss.getValue (row, 1)
        kvmap [key] = value
    return kvmap



def makeAbiTables (schoolyear, klass, date):
    """Build grade tables (one for each student) for the final Abitur
    grades.
    These tables are used to prepare the grades for (automatic) entry
    into the certificates.
    The new tables are placed in a subfolder of the normal folder (see
    configuration file PATHS: FILE_ABITABLE_NEW). This is to avoid
    accidentally overwriting existing tables which already contain data.
    Most of the necessary "cleverness" is built into the template file.
    """
    template = Paths.getUserPath ('FILE_ABITUR_GRADE_TEMPLATE')
    outpath = Paths.getYearPath (schoolyear, 'FILE_ABITABLE_NEW', klass=klass)
    for f in glob (os.path.join (os.path.dirname (outpath), '*')):
        os.remove (f)
    outpath += '.xlsx'

    sheetname = CONF.TABLES.ABITUR_RESULTS.GRADE_TABLE_SHEET
    FrHr = {}
    for v in CONF.TABLES.ABITUR_RESULTS.P_FrHr:
        k, v = v.split (':')
        FrHr [k] = v

    ncourses = CONF.TABLES.ABITUR_RESULTS.NCOURSES.nat ()

    courseTables = CourseTables (schoolyear)
    pupils = Pupils (schoolyear).classPupils (klass, date)
    sid2info = courseTables.filterGrades (klass, realonly=True)
    subjects = []
    for sid, sinfo in sid2info.items ():
        subjects.append ((sid, sinfo.COURSE_NAME))

    teacherMatrix = FormattedMatrix.readMatrix (schoolyear,
            'FILE_CLASS_SUBJECTS', klass)

    i = 0       # pid index for ordering files
    files = []  # list of created files (full paths)
    for pdata in pupils:
        pid = pdata ['PID']
        pname = pdata.name ()
        i += 1
        filepath = outpath.replace ('*', '{pnum:02d}-{pid}-{name}'.format (
                pnum=i, pid=pid,
                name=Paths.asciify (pname)))

        fields = {'YEAR': str (schoolyear),
                'LASTNAME': pdata ['LASTNAME'],
                'FIRSTNAMES': pdata ['FIRSTNAMES'],
                'DOB_D': pdata ['DOB_D'],
                'POB': pdata ['POB'],
                'HOME': pdata ['HOME']}
        try:
            fields ['FrHr'] = FrHr [pdata ['SEX']]
        except:
            REPORT.Error (_BADSEXFIELD, klass=klass, pname=pname,
                    sex=pdata ['SEX'])
            fields ['FrHr'] = ' '

        f = 0
        for sid, sname in subjects:
            if not teacherMatrix [pid][sid]:
                continue
            f += 1
            fields ['F' + str (f)] = sname.split ('|') [0].rstrip ()
        if ncourses and f != ncourses:
            REPORT.Error (_NOTNCOURSES, klass=klass, pname=pname, n=f,
                    nc0=ncourses)
            continue

        unused = XLS_template (filepath, template, fields,
                sheetname=sheetname)
        files.append (filepath)

    REPORT.Info (_MADENTABLES, klass=klass, n=len (files))
    return files


def makeAbiReports (schoolyear, klass):
    """Build abitur grade reports using the grade tables defined by the
    configuration path FILE_ABITABLE.
    A template is used to construct the report files.
    The results – odt files – are placed according to the configuration
    path FILE_ABIREPORT, first removing any existing files in this folder.
    odt files are created from a template.
    Return a tuple: the output folder and a list of odt-file-names
    (without folder path).
    """
    sheetname = CONF.TABLES.ABITUR_RESULTS.GRADE_TABLE_SHEET
    infile = Paths.getYearPath (schoolyear, 'FILE_ABITABLE', klass=klass)
    filepath = Paths.getYearPath (schoolyear, 'FILE_ABIREPORT',
            klass=klass, make=-1)
    outdir = os.path.dirname (filepath)
    if os.path.isdir (outdir):
        shutil.rmtree (outdir)
    files = []
    for f in sorted (glob (infile)):
        # Extract pupil info from file-name
        try:
            _, index, pid, pname = f.rsplit ('.', 1) [0].rsplit ('-', 3)
        except:
            continue
        data = readTableData (f, table=sheetname)
        ofile = filepath.replace ('*', '{pnum}-{pid}-{name}'.format (
                pnum=index, pid=pid, name=pname))
        files.append (os.path.basename (makeAbiReport (ofile, data)))
    REPORT.Info (_MADENREPORTS, klass=klass, n=len (files), folder=outdir)
    return outdir, files


def odt2pdf (folder, files):
    if files:
        odir, pdf_files = toPdf (folder, *files)
        REPORT.Info (_MADENPDFS, n=len (pdf_files), folder=odir)
    return odir, pdf_files


def makeAbiReport (outpath, pdata):
    """Build an Abitur grade report for a pupil.
    The necessary information is supplied in the mapping <pdata>:
        {key: value}.
    The keys are user-fields in the document template (odt), the values
    are the strings to be inserted.
    The resulting file is placed at <outpath>, creating leading folders
    if necessary. <outpath> need not end in '.odt', if not present it
    will be added automatically.
    """
    NOTCHOSEN = CONF.FORMATTING.NOTCHOSEN

    ## Get template path
    template = Paths.getUserPath ('FILE_ABITUR_REPORT_TEMPLATE')
#    fieldnames = OdtUserFields.listUserFields (template)

    ## Convert the dates.
    for f in pdata:
        d = pdata [f]
        if f.endswith ('_D'):
#            print ("???", f, d)
            if d:
                pdata [f] = Dates.dateConv (d)
        # Substitute non-date empty cells
        elif not d:
            pdata [f] = NOTCHOSEN

    folder = os.path.dirname (outpath)
    if not os.path.isdir (folder):
        os.makedirs (folder)
    ofile, used, missing = OdtUserFields.fillUserFields (
            template, outpath, pdata)
    REPORT.Info (_ABIREPORTDONE, path=ofile)
    return ofile



##################### Test functions
def test_01 ():
    schoolyear = 2016
    date = '2016-06-07'
    klass = '13'

    REPORT.Test ("** Make Abi-tables:")
    for f in makeAbiTables (schoolyear, klass, date):
        REPORT.Test ("  --> %s" % f)

def test_02 ():
    ifile = Paths.getUserPath ('FILE_ABITUR_GRADE_EXAMPLE')
    outfile = os.path.join (os.path.dirname (ifile), 'tmp', 'AbiZeugnis.odt')
    pdata = readTableData (ifile, table='Daten')
    REPORT.Test ("??? Fields: %s" % repr(pdata))
    REPORT.Test ("\n --> %s" % makeAbiReport (outfile, pdata))

def test_03 ():
    schoolyear = 2016
    klass = '13'
    REPORT.Test ("\n  ========== Abi-reports %d, class %s ==========\n"
            % (schoolyear, klass))
    odir, files = makeAbiReports (schoolyear, klass)
    REPORT.Test ("\n  +++ Convert to pdf ...")
    odt2pdf (odir, files)
