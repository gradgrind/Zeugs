#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_text/coversheet.py

Last updated:  2019-11-30

Build the outer sheets (cover sheets) for the text reports.
User fields in template files are replaced by the report information.

=+LICENCE=============================
Copyright 2017-2019 Michael Towers

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

_PUPILNOTINCLASS  = "Schüler {pid} nicht in Klasse {klass}"
_NOTEMPLATE       = "Klasse {klass}: Vorlagedatei (Deckblatt) fehlt"
_MADENCOVERS      = "{n} Deckblätter wurden erstellt, in:\n  {folder}"
_MADEKCOVERS      = "Alle Deckblätter für diese Klasse:\n  {path}"
_TEXTREPORTDONE   = "Textzeugnis-Deckblatt fertig: {path}"


import os
from collections import OrderedDict
from zipfile import ZipFile, ZIP_DEFLATED
from glob import glob

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils
from wz_textdoc.simpleodt import OdtUserFields
from wz_io.support import toA3, toPdf, concat


class TextReportCovers:
    def __init__ (self, schoolyear, date):
        """Handle generation of text report covers.
        Set up a class instance for this year and date.
        """
        self.schoolyear = schoolyear
        self.date = date
#        self.db = DBase (schoolyear)


# Return a single pdf with all covers?
# The klass should be specified, in case different classes have
# different templates?
    def makeCovers (self, klass, pids=None):
        """Build text report covers for the given school-class.
        If <pids> is specified, it must be a list. Reports will be
        generated only for pupils in this list (who must be in the
        specified class).
        Return a list of the successfully generated files (just the names).
        """
        # Alphabetical list of <PupilData> instances:
        pupils = Pupils (self.schoolyear)
        pupilData = pupils.classPupils (klass)

#TODO
        ## Gather info which is particular to the class and year
        self._typeInfo = {}
        self._typeInfo ['SCHOOLYEAR'] = Dates.printSchoolYear (self.schoolyear)
        self._typeInfo ['DATE_D'] = self.date   # Date of issue
        calendar = Dates.getCalendar (self.schoolyear)
        self._typeInfo ['START_D'] = calendar.START [0]
        self._typeInfo ['END_D'] = calendar.END [0]

        ## Get template path
        tpdir = Paths.getUserPath ('DIR_TEXT_REPORT_TEMPLATES')
        reportInfo = CONF.TEXT.COVER_SHEETS
        for k in reportInfo:
            if k == klass:
                tpfile = reportInfo [k].string ()
                break
        else:
            ktag = '*' + klass.lstrip ('0123456789')
            if ktag in reportInfo:
                tpfile = reportInfo [ktag].string ()
            elif '*' in reportInfo:
                tpfile = reportInfo ['*'].string ()
            else:
                REPORT.Fail (_NOTEMPLATE, klass=klass)
                assert False

        self._tppath = os.path.join (tpdir, tpfile)
#        print ("\nTEMPLATE:", tppath)
        self._fieldnames = OdtUserFields.listUserFields (self._tppath)

        self._outdir = Paths.getYearPath (self.schoolyear,
                'DIR_TEXT_COVERS_ODT',
                date=self.date, klass=klass, make=1)

#TODO: Make one file for all rather than one for each pupil ...
# That might be easier with weasyprint?
        files = []
        for pd in pupilData:
            if pids and pd ['PID'] in pids:
                f = self._makeReport (klass, pd)
                if f != None:
                    files.append (f)

        if files:
            toPdf (self._outdir, *files)
            pdf_files = [f.rsplit ('.', 1) [0] + '.pdf' for f in files]
            pdfdir = os.path.join (self._outdir, 'pdf')
            ofiles = toA3 (pdfdir, *pdf_files)
            REPORT.Info (_MADENCOVERS, n=len (files), folder=self._outdir)

            # Put all covers in one pdf-file
            kfile = Paths.getYearPath (self.schoolyear,
                    'FILE_TEXT_COVERS_KLASS',
                    date=self.date, klass=klass)
            concat (ofiles, kfile)
            REPORT.Info (_MADEKCOVERS, path=kfile)

        return files


    def _makeReport (self, klass, pupilData, pupilNumber):
        """Build a text report cover for the given pupil, <pid>.
        <pupilNumber> is the pupil's index within the class.
        """
        ## Start a <dict> with the pupil data
        FIELDS = pupilData._asdict ()

        FIELDS ['CLASS'] = (klass.lstrip ('0')
                if CONFIG.FORMATTING.CLASS_LEADING_ZERO [0] == '0'
                else klass)

        # Unused fields
        NOENTRY = CONFIG.FORMATTING.NOENTRY.string ()
        for f in self._fieldnames:
            if not f in FIELDS:
                FIELDS [f] = NOENTRY

        ## Add info from report type config file
        FIELDS.update (self._typeInfo)

        ## When all fields have been defined/entered, convert the dates.
        for f in FIELDS:
            if f.endswith ('_D'):
                d = FIELDS [f]
#                print ("???", f, d)
                if d:
                    FIELDS [f] = Dates.dateConv (d)
#        print ("#####################\n", FIELDS)

        outfile = CONFIG.PATHS.REPORT_FILE_TEMPLATE.string ().format (
                number=pupilNumber, pid=str (pupilData.PID), tag='Deckblatt',
                name=Paths.asciify (self.db.shortName (pupilData)))
        path = os.path.join (self._outdir, outfile)
#        print ("%%%%%%%", FIELDS)
#        quit (0)
        ofile, used, missing = OdtUserFields.fillUserFields (
                self._tppath, path, FIELDS)
        REPORT.Info (_TEXTREPORTDONE, path=ofile)
        return os.path.basename (ofile)


    def packPdf (self, folder=None):
        """Pack all available pdf cover-sheets into a zip file, in class
        directories.
        If <folder> is supplied it will override the normal location to
        which the file is saved.
        Return the path of the zip-file.
        """
        indir = Paths.getYearPath (self.schoolyear,
                'DIR_TEXT_COVERS_ODT', date=self.date, klass='*')
        outfile = Paths.getYearPath (self.schoolyear,
                'FILE_TEXT_COVERS_ALL', date=self.date)
        if folder != None:
            if not os.path.isdir (folder):
                os.makedirs (folder)
            outfile = os.path.join (folder, os.path.basename (outfile))

        with ZipFile (outfile, mode='w', compression=ZIP_DEFLATED) as fzip:
            for d in sorted (glob (indir)):
                dname = os.path.basename (d)
                for f in sorted (glob (os.path.join (d, 'pdf', '*.pdf'))):
                    fzip.write (f, arcname=os.path.join (dname,
                            os.path.basename (f)))
