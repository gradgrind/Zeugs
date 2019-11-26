#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_grades/gradetables.py

Last updated:  2019-10-27

Handle the tables for grades.


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

_GRADESTITLE = "Noten"
_GRADESTITLE0 = "Noteneingabe"

_CLOSINGDATE = "Einsendeschluss"
_HJ = "Halbjahr_%d"

### Messages
_GRADEMATRIX0 = "Noteneingabetabelle für Klasse {klass} erstellt:\n  {path}"
_GRADEMATRIX = "Notentabelle für Klasse {klass} erstellt:\n  {path}"
_NOPUPILS = "Keine Schüler in Klasse {klass}"
_NOCOMPONENTS = "Sammelfach {sid} ({sname}) hat keine Komponenten"
_SPECIAL_WITH_COMPONENTS = "Sonderfach {sid} ({sname}) darf keine Komponenten haben"
#_NOGRADES = "Keine Noten für Klasse {klass}: {date}"
_REAL_COMPOSITE = ("Klasse {klass}: Fach '{sid}' wird als Sammelfach deklariert,"
                "\n – aber auch als unterrichtetes Fach")
_BAD_XCOL_GROUP = "Ungültige Gruppe (GROUPS = ... '{val}') in:\n  {path}"
_FUNCTION_ERROR = ("Klasse {klass}, Schüler {pupil}:\n  Fehler bei Berechnung"
                " der Funktion {field}")
_NO_ISSUE_DATE = "Notenzeugnisse für {date}: Kein Ausgabedatum"
_NO_DATES = "Kein Ausgabedatum-Tabelle: {path}"
_BAD_DATES = "Ungültige Ausgabedatum-Tabelle: {path}"


from collections import OrderedDict
import csv

from wz_core.configuration import Paths
from wz_core.courses import CourseTables, COMPOSITE, _INVALID
from wz_core.pupils import Pupils
from wz_table.formattedmatrix import FormattedMatrix
from wz_compat.gradefunctions import validGrades, GradeFunctions

_WILDCARD = '*'
_FUNCTION = '%'
_EXTRA = '_'
_EXCLUDE = '~'
#TODO: Separate tables for each stream?


class NullDict (dict):
    """A mapping object with a unique null element.
    """
    @classmethod
    def null (cls):
        try:
            return cls._null
        except:
            cls._null = cls ()
            return cls._null

    def isNull (self):
        return self is self.null ()


class XValues (NullDict):
    """Data structure used as the return value of <GradeTables.extraMatrix>.
    It is a mapping: {pid -> {[_Xtag2Value] xtag -> value}}.
    """
    class _Xtag2Value (NullDict): pass

    def add (self, pid, xtag, value):
        """All parameters should be strings.
        <value> can be <None>?
        """
        try:
            pmap = self [pid]
        except:
            pmap = self._Xtag2Value ()
            pmap [xtag] = value
            self [pid] = pmap
        else:
            pmap [xtag] = value

#?    def get (self, pid, xtag):


#? Empty fields are returned as <None>.
#            -> {pid -> {xtag -> value}}


class IssueDates (list):
    def wildcard (self, idate, cdate):
        self.idate, self.cdate = idate, cdate


class GradeTables:
    def __init__ (self, schoolyear, date):
        """Prepare an environment for the generation of grade tables.
        <date> should be simple number for a term/semester, or a date
        (yyyy-mm-dd) if the tables are for another occasion
        """
        self.schoolyear = schoolyear
        try:
            self.date = self.termdate (date)
        except:
            self.date = date
        self.pupils = Pupils (self.schoolyear)
        self.courses = CourseTables (schoolyear)
        self.xvcache = None


    @staticmethod
    def termdate (n):
        """Return the "date" value for the given term/semester.
        """
        return _HJ % int (n)


    def buildGradeMatrix (self, klass, closingdate=None):
        """
        """
        info = {_CLOSINGDATE: closingdate} if closingdate else None
        matrix = FormattedMatrix (self.schoolyear, 'FILE_CLASS_GRADES0',
                klass, date=self.date, infolines=info)
        pupils = []     # <PupilData> instances
        values = {}     # {pid -> {sid -> value}}
        styles = {}     # {pid -> {sid -> style data}}
        _vlists = {}    # {stream -> validation list}
        stylemaps = {}  # {stream -> style info}
        # Fetch the data concerning taken subjects:
        teacherMatrix = self.courses.teacherMatrix (klass)
        if not teacherMatrix:
            return False
        # List of (sid, name) pairs for matrix:
        subjects = [(sid, self.courses.subjectName (sid))
                for sid, sinfo in teacherMatrix.sid2info.items ()
                if not sinfo.NOTGRADE]
        # Iterate over all pupils in the class:
        for pid, sid2tid in teacherMatrix.items ():
            pdata = sid2tid.pupilData
            # Exclude those who have left:
            if closingdate:
                exd = pdata ['EXIT_D']
                if exd and exd < closingdate:
                    continue
            pupils.append (pdata)   # pupil list for matrix building
            pvalues = {}            # only invalid cells are included
            pstyles = {}            # style for each cell
            values [pid] = pvalues
            styles [pid] = pstyles
            # Get stream style
            stream = pdata ['STREAM']
            try:
                style = stylemaps [stream]
            except KeyError:
                # Background colour
                try:
                    sx = {'background': CONF.COLOURS [stream]}
                except KeyError:
                    sx = {}
                # Validation list
                try:
                    sx ['valid'] = _vlists [stream]
                except KeyError:
                    _v = validGrades (pdata)
                    _vlists [stream] = _v
                    sx ['valid'] = _v
                # Cache style for stream
                style = matrix.newEntryStyle (**sx)
                stylemaps [stream] = style
            # Iterate over the subjects
            for sid, sname in subjects:
                if sid in sid2tid:
                    pstyles [sid] = style
                else:
#                    pvalues [sid] = CONF.FORMATTING.INVALID
                    pvalues [sid] = _INVALID
                    pstyles [sid] = None
        # Build spreadsheet file:
        matrix.build (_GRADESTITLE0, pupils, subjects,
                values=values, cellstyles=styles, infolines=info)
        fpath = matrix.save ()
        REPORT.Info (_GRADEMATRIX0, klass=klass, path=fpath)
        return True


    def getExtras (self, klass):
        """Return a set of streams for extra columns which are relevant
        for this class:
            {[ordered] column tag -> {stream, ...}}
        """
        classes = self.courses.classes ()
        streams = CONF.GROUPS.STREAMS
        tag2streams = OrderedDict ()
        empty = frozenset ()

        class _VError (ValueError): pass

        def _getkstreams (ks):
            ksx = ks.split ('-')
            if len (ksx ) == 1:
                k, s = ks, _WILDCARD
            elif len (ksx ) == 2:
                k, s = ksx
            else:
                raise _VError
            # Check class and stream
            if k == _WILDCARD:
                ok = True
            elif k in classes:
                ok = (k == klass)
            else:
                raise _VError
            if s == _WILDCARD:
                sx = set (streams)
            elif s in streams:
                sx = {s}
            else:
                raise _VError
            return sx if ok else empty

        for x in CONF.GRADES.XCOLUMNS.list ():
            xset = set ()
            iset = set ()
            xmap = CONF.GRADES.XCOLUMNS [x]
            for ks in xmap.GROUPS:
                # Exclusions have priority.
                # A wildcard (_WILDCARD) may be used for class, stream or both.
                try:
                    if ks [0] == _EXCLUDE:
                        xset |= _getkstreams (ks[1:])
                    else:
                        iset |= _getkstreams (ks)
                except _VError:
                    REPORT.Error (_BAD_XCOL_GROUP, path=xmap._path, val=ks)
            kstreams = iset - xset
            if kstreams:
                tag2streams [xmap.TAG] = kstreams
        return tag2streams



#TODO: AT the moment I am only using one file, overwritten for each class!
# I could have one file per class, or one file for all classes, if I
# read and write the whole thing in one block.
    def extraMatrix (self, klass, evaluate=None):
        """Return a mapping of special ("grade") fields for the given class.
        If <evaluate> is supplied with a grade mapping, also function
        fields will be included.
        Empty fields are returned as <None>.
            -> {[XValues] pid -> {[_Xtag2Value] xtag -> value}}
        """
        extracols = self.getExtras (klass)
        # Read existing values
#TODO: readExtras -> {pid -> {x -> value}}
        values = self.readExtras (klass)
        try:
            xdate = self.getIssueDates (klass).cdate
        except:
            REPORT.Error (_NO_ISSUE_DATE, date=self.date)
            return XValues.null ()
        xmatrix = XValues ()    # Result: {pid -> {xtag -> value}}

        pupils = self.pupils.classPupils (klass, date=xdate)
        for pdata in pupils:
            pid = pdata ['PID']
            try:
                pvalues = values [pid]
            except:
                pvalues = {}
            pstream = pdata ['STREAM']
            for x, streams in extracols.items ():
                if pstream in streams:
                    # Make entry
                    if x [0] == _FUNCTION:
                        if evaluate:
                            try:
                                xmatrix.add (pid, x, self.doFunction (x, evaluate))
                            except:
                                REPORT.Error (_FUNCTION_ERROR, klass=klass,
                                        pupil=pdata.name (), field=x)
                    else:
                        xmatrix.add (pid, x, pvalues.get (x))
        return xmatrix


# Using a tsv file
    def getIssueDates (self, klass):
        dlist = None
        fpath = Paths.getYearPath (self.schoolyear, 'FILE_GRADE_ISSUE',
                date=self.date)
        try:
            with open (fpath, encoding='utf-8', newline='') as csvfile:
                csvreader = csv.reader (csvfile, delimiter='\t')
                for row in csvreader:
                    if len (row) == 0:
                        continue
                    if row [0] [0] == '#':
                        continue
                    ks, idate, cdate = row
                    if dlist == None:
                        if ks == _WILDCARD:
                            dlist = IssueDates ()
                            dlist.wildcard (idate, cdate)
                            continue
                        raise ValueError
                    dlist.append (row)
        except FileNotFoundError:
            REPORT.Fail (_NO_DATES, path=fpath)
        except:
            REPORT.Fail (_BAD_DATES, path=fpath)
        return dlist



#############+++ Handle extra fields for grades.
# A version using a simple csv file.
    def readExtras (self, klass):
        if not self.xvcache:
            self.xvcache = XValues ()
            fpath = Paths.getYearPath (self.schoolyear, 'FILE_XGRADE_DATA',
                    date=self.date)
            try:
                with open (fpath, encoding='utf-8', newline='') as csvfile:
                    csvreader = csv.reader (csvfile, delimiter='\t')
                    for pid, x, val in csvreader:
                        self.xvcache.add (pid, x, val or None)
            except:
                return XValues.null ()
        xmatrix = XValues ()    # Result: {pid -> {xtag -> value}}
        for pdata in self.pupils.classPupils (klass):
            pid = pdata ['PID']
            try:
                x2v = self.xvcache [pid]
            except:
                continue
            for x, v in x2v.items ():
                xmatrix.add (pid, x, v)
        return xmatrix


    def saveExtras (self, klass, xmatrix):
#TODO: get classes/streams from issue dates
        fpath = Paths.getYearPath (self.schoolyear, 'FILE_XGRADE_DATA',
                date=self.date)
        with open (fpath, 'w', encoding='utf-8', newline='') as csvfile:
            csvwriter = csv.writer (csvfile, delimiter='\t')
            for pid, x2val in xmatrix.items ():
                for x, val in x2val.items ():
                    csvwriter.writerow ([pid, x, val])
        self.xvcache = None


    def _xxx (self):
        for pid, sid2grade in gmatrix.items ():
            pupils.append (sid2grade.pupilData)
            if empty:
                oldvals = sid2grade
            else:
                oldvals = None
            pvalues = {}
            values [pid] = pvalues
            pstyles = {}
            stream = sid2grade.pupilData ['STREAM']
            try:
                style = stylemaps [stream]
            except KeyError:
                # Background colour
                try:
                    sx = {'background': CONF.COLOURS [stream]}
                except KeyError:
                    sx = {}

                # Validation list
                try:
                    sx ['valid'] = _vlists [stream]
                except KeyError:
                    _v = validGrades (sid2grade.pupilData)
                    _vlists [stream] = _v
                    sx ['valid'] = _v

                # Cache style for stream
                style = matrix.newEntryStyle (**sx)
                stylemaps [stream] = style

            for sid, sname in subjects:
                try:
                    g = sid2grade [sid]
                except:
                    # Invalid cell
                    pvalues [sid] = CONF.FORMATTING.INVALID
                    pstyles [sid] = None
                    continue

                sidinfo = gradeMatrix.subjectData [sid]
                if sidinfo.IS_COMPONENT:
                    column_colour = CONF.COLOURS.COMPONENT
                elif sidinfo.CALC:
                    column_colour = CONF.COLOURS.SPECIAL
                else:
                    column_colour = None
                if column_colour:
                    xstream = stream + '+' + column_colour
                    try:
                        xstyle = stylemaps [xstream]
                    except IndexError:
                        xstyle = matrix.newEntryStyle (style, fg=column_colour)
                        stylemaps [xstream] = xstyle
                    pstyles [sid] = xstyle
                else:
                    pstyles [sid] = style

                if g == None or basic:
                    # Only set style
                    continue
                pvalue = g

        title = _GRADESTITLE0 if basic else _GRADESTITLE
        matrix.build (title, pupils, subjects,
                values=values, cellstyles=styles, infolines=info)
        fpath = matrix.save ()
        REPORT.Info (_GRADEMATRIX0 if basic else _GRADEMATRIX,
                klass=klass, path=fpath)


    def pid2sid2grade (self, klass, closingdate=None):
        """Build a class-subject matrix of grades for each pupil and
        subject combination. No calculated "subjects" are included in
        this mapping (but "special" input cells are).
        The subject data is fetched by <self.collate> and available as
        the <subjectData> attribute of the result.
        Return a mapping {[ordered] pid -> {sid -> grade}}
        The pupil data is fetched for the date <closingdate>. If
        <closingdate> is not supplied, the date will be read from the
        table. If there is no table (or it contains no date),
        <date=None> will be assumed, ignoring any exit dates.
        The result also contains the pupil data as attribute <pupilData>
        of each inner mapping.
        The teacher mapping for each pupil is available as the <teachers>
        attribute of each inner mapping.
        """
        class _adict (dict): pass   # a <dict> with extra attributes

        grades = OrderedDict ()
        sidinfo = self.collate (klass)
        grades.subjectData = sidinfo
        subjects = [sid for sid, sinfo in sidinfo.items ()
                if (not sinfo.CALC) or sinfo.CALC [0] == '_']
        teacherMatrix = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_SUBJECTS', klass)
        values = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_GRADES', klass, date=self.date)
        try:
            grades.info = values.info
            grades.filepath = values.filepath
            if not closingdate:
                closingdate = values.info [_CLOSINGDATE]
        except:
            pass
        pupils = self.pupils.classPupils (klass, date=closingdate)
        if len (pupils) == 0:
            REPORT.Fail (_NOPUPILS, klass=klass)
        for pdata in pupils:
            pid = pdata ['PID']
            try:
                vals = values [pid]
            except:
                vals = None
            pvalues = _adict ()
            pvalues.pupilData = pdata
            pvalues.teachers = teacherMatrix [pid]
            grades [pid] = pvalues
            for sid in subjects:
#TODO: Some way of filtering the special subjects?
                if pvalues.teachers [sid] or sidinfo [sid].CALC:
                    try:
                        pvalues [sid] = vals [sid]
                    except:
                        pvalues [sid] = None
                #else: no teacher entry for pupil and subject
        return grades


    def composites (self, klass):
        """Fetch the subject tags used as composites in the given class.
        A mapping is returned: {composite-sid -> [component sid, ...]}.
        """
        composites = {}         # {composite-sid -> list of component sids}
        sid2flag = self.courses.filterGrades (klass)
        for sid, sflag in sid2flag.items ():
            try:
                sxname = self.courses.subjectName (sflag)
            except:
                continue
            # <sflag> is a composite
            if sflag in sid2flag:
                # ... but is also used as a taught ("real") subject.
                REPORT.Fail (_REAL_COMPOSITE, klass=klass, sid=sflag)
            try:
                composites [sflag].append (sid)
            except:
                composites [sflag] = [sid]
        return composites


#TODO: This is all a bit confusing ...
# A collected-grade table could have the same format as an input table.
# The special-inputs could be stored separately, but perhaps also in this
# table. The calculated fields should not be in this table.
# It might be useful to be able to output a read-only table containing
# the calculated fields for display/printing. Ideally there would be
# a custom editor which can update itself (the calculated fields) and
# this table (or these tables).
    def gradeData (self, klass):
        """Fetch the pupil, subject and grade data for building grade reports
        for the given class.
        """
        gmatrix = self.pid2sid2grade (klass)
        for pid, pgrades in gmatrix.items ():
            gfunctions = GradeFunctions (pgrades)
            for sid, subjectInfo in gmatrix.subjectData.items ():
                if subjectInfo.CALC:
                    if subjectInfo.CALC [0] != '_':
                        pgrades [sid] = gfunctions.call (subjectInfo.CALC,
                                subjectInfo.COMPONENTS)
        return gmatrix


##################### Test functions
_testyear = 2016
_term = 1
_closingdate = '2016-01-18'
def test_01 ():
    klass = '12'
    REPORT.Test ("\n >>> Existing Grades, class %s" % klass)
    fm = FormattedMatrix.readMatrix (_testyear, 'FILE_CLASS_GRADES',
            klass, date=GradeTables.termdate (_term))
    REPORT.Test (repr (fm))

def test_02 ():
    gtables = GradeTables (_testyear, _term)
    REPORT.Test ("\n EXTRAs for class 12, with streams")
    for x, s in gtables.getExtras ('12').items ():
        REPORT.Test ("   %s: %s" % (x, repr (s)))


def test_03 ():
    gtables = GradeTables (_testyear, _term)
    for klass in '10', '11', '12':
        REPORT.Test ("\n  >>>>>>>>>>> Class %s: Extra grade fields" % klass)
        xmatrix = gtables.readExtras (klass)
        REPORT.Test ("     %s" % repr (xmatrix))
    quit (0)

    for klass in '10', '11', '12':
        REPORT.Test ("\n  >>>>>>>>>>> Class %s: Save extra grade fields" % klass)
        xmatrix = gtables.extraMatrix (klass)
        gtables.saveExtras (klass, xmatrix)
    quit (0)



def test_03a ():
    gtables = GradeTables (_testyear, _term)
    for klass in '10', '11', '12':
        REPORT.Test ("\n  >>>>>>>>>>> Class %s: course matrix" % klass)
        gtables.gradeMatrix (klass, closingdate=_closingdate)

def test_04 ():
    klass = '13'
    gtables = GradeTables (_testyear, _term)
    REPORT.Test ("\n  >>>>>>>>>>> Class %s: course matrix" % klass)
    gtables.gradeMatrix (klass, title="Noten 1. Halbjahr", closingdate=_closingdate)

def test_05 ():
    klass = '12'
    gtables = GradeTables (_testyear, _term)
    REPORT.Test ("\n  >>>>>>>>>>> Class %s: Subject data" % klass)
    for sid, subjectInfo in gtables.collate (klass).items ():
        REPORT.Test ("\n *** %s: %s" % (sid, repr (subjectInfo)))

def test_06 ():
    klass = '12'
    gtables = GradeTables (_testyear, _term)
    REPORT.Test ("\n  >>>>>>>>>>> Class %s: Report data" % klass)
    sidinfo, gmatrix = gtables.gradeData (klass)
    for pid, pgrades in gmatrix.items ():
        REPORT.Test ("  PID: %s" % pid)
        for sid, subjectInfo in sidinfo.items ():
            sname = subjectInfo.COURSE_NAME
            stag = '[' + sname + ']' if subjectInfo.IS_COMPONENT else sname
            try:
                val = pgrades [sid]
            except:
                val = '###'
            REPORT.Test ("   --- %s (%s): %s" % (stag, sid, repr (val)))

# The pupil data needed for the reports is available as <gmatrix.pupils>.
