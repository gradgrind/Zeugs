#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_grades/gradetables.py

Last updated:  2019-10-03

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
_CLOSINGDATE = "Einsendeschluss"
_HJ = "Halbjahr_%d"

### Messages
_GRADEMATRIX = "Noteneingabetabelle für Klasse {klass} erstellt:\n  {path}"
_NOPUPILS = "Keine Schüler in Klasse {klass}"


from wz_core.courses import CourseTables
from wz_core.pupils import Pupils
from wz_table.formattedmatrix import FormattedMatrix


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


    @staticmethod
    def termdate (n):
        """Return the "date" value for the given term/semester.
        """
        return _HJ % int (n)


#TODO: What effect should <realonly=False> have?!
#TODO: Separate tables for each stream?
    def gradeMatrix (self, klass, title=None,
            closingdate=None, empty=False, realonly=True):
        """Build a class-course matrix of teachers for each pupil and
        subject combination.
        <closingdate> (yyyy-mm-dd) is used to filter the pupils and
        appears as info in the table.
        The contents of an existing table should be taken into account
        unless <empty> is true.
        """
        if not title: title = _GRADESTITLE
        pupils = self.pupils.classPupils (klass, date=closingdate)
        if len (pupils) == 0:
            REPORT.Warn (_NOPUPILS, klass=klass)
            return
        sid2info = self.courses.filterGrades (klass, realonly)
        subjects = []
        for sid, sinfo in sid2info.items ():
            subjects.append ((sid, sinfo.COURSE_NAME))
        teacherMatrix = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_SUBJECTS', klass)

# If I want coloured columns, that would need another structure ...
# What if row and column specs clash?! Text colour for columns?

        info = {_CLOSINGDATE: closingdate} if closingdate else None
        matrix = FormattedMatrix (self.schoolyear,
                'FILE_CLASS_GRADES0' if empty else 'FILE_CLASS_GRADES',
                klass, date=self.date, infolines=info)
        oldvalues = None if empty else matrix.getValues ()

        _vlists = {}    # {stream -> validation object}

# At first just make styles for streams
        stylemaps = {}
        values = {}
        styles = {}
        for pdata in pupils:
            pid = pdata ['PID']
            try:
                oldvals = oldvalues [pid]
            except:
                oldvals = None
            pvalues = {}
            values [pid] = pvalues
            pstyles = {}
            styles [pid] = pstyles
            stream = pdata ['STREAM']
            try:
                style = stylemaps [stream]
            except KeyError:
                # Background colour
                try:
                    style = {'background': CONF.COLOURS [stream]}
                except KeyError:
                    style = {}

                # Validation list
                try:
                    style ['valid'] = _vlists [stream]
                except KeyError:
                    _gs = getGradeScale (klassStream (klass, stream))
                    _v = validGrades (_gs)
                    _vlists [stream] = _v
                    style ['valid'] = _v

                # Cache style for stream
                stylemaps [stream] = matrix.newEntryStyle (style)

            for sid, sname in subjects:
                t = teacherMatrix [pid][sid]
                if t:
                    try:
                        pvalues [sid] = oldvals [sid]
                    except:
                        pass
                    pstyles [sid] = style
                else:
                    pvalues [sid] = CONF.FORMATTING.INVALID
                    pstyles [sid] = None

        matrix.build (title, pupils, subjects,
                values=values, cellstyles=styles, infolines=info)
        fpath = matrix.save ()
        REPORT.Info (_GRADEMATRIX, klass=klass, path=fpath)



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
    for klass in '10', '11', '12', '13':
        REPORT.Test ("\n  >>>>>>>>>>> Class %s: course matrix" % klass)
        gtables.gradeMatrix (klass, empty=True, closingdate=_closingdate)

def test_03 ():
    gtables = GradeTables (_testyear, _term)
    for klass in '10', '11', '12':
        REPORT.Test ("\n  >>>>>>>>>>> Class %s: course matrix" % klass)
        gtables.gradeMatrix (klass, closingdate=_closingdate)

def test_04 ():
    klass = '13'
    gtables = GradeTables (_testyear, _term)
    REPORT.Test ("\n  >>>>>>>>>>> Class %s: course matrix" % klass)
    gtables.gradeMatrix (klass, title="Noten 1. Halbjahr", closingdate=_closingdate)
