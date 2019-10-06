#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_grades/gradeprocessing.py

Last updated:  2019-10-06

Handle the processing of basic grades: composite subjects, qualifications, ...


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

from collections import OrderedDict

from wz_table.formattedmatrix import FormattedMatrix
from .gradetables import GradeTables, _NOPUPILS


_NOGRADES = "Keine Noten für Klasse {klass}: {date}"
class GradeTablesX (GradeTables):

#TODO: What effect should <realonly=False> have?!
#TODO: Separate tables for each stream?

# I need to get the data without producing formatted output ...
# Perhaps this bit should only deal with real subjects and fail if there
# is no data?
    def pid2sid2grade (self, klass, closingdate=None):
        """Build a class-course matrix of grades for each pupil and
        subject combination.
        <closingdate> (yyyy-mm-dd) is used to filter the pupils and
        appears as info in the table.
        Return a mapping {[ordered] pid -> {sid -> grade}}
        """
        pupils = self.pupils.classPupils (klass, date=closingdate)
        if len (pupils) == 0:
            REPORT.Warn (_NOPUPILS, klass=klass)
            return None
        sid2info = self.courses.filterGrades (klass, realonly=True)
        subjects = []
        for sid, sinfo in sid2info.items ():
            subjects.append ((sid, sinfo.COURSE_NAME))
        teacherMatrix = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_SUBJECTS', klass)
        values = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_GRADES', klass, date=self.date)
        if not values:
            REPORT.Warn (_NOGRADES, klass=klass, date=self.date)
            return None

        results = OrderedDict ()
        for pdata in pupils:
            pid = pdata ['PID']
            try:
                vals = values [pid]
            except:
                vals = None
            pvalues = {}
            results [pid] = pvalues

            for sid, sname in subjects:
                if teacherMatrix [pid][sid]:
                    try:
                        pvalues [sid] = vals [sid]
                    except:
                        pvalues [sid] = None
                #else: no entry (subject not available for /chosen by pupil)

        return results


    def collate (self, klass):
        """Fetch the subject information for the given class.
        Return an ordered mapping:
            {[ordered] sid -> (name, is component (bool),
                    function tag, set of component sids)}
        The function tag and the "set" may be <None>.
        """
        groups = {}             # {*-sid -> set of component sids}
        s2name = OrderedDict ()  # {[ordered] sid -> name}
        unreal = {}             # {*-sid -> function tag}
        components = set ()     # sids which contribute to composite grades.
        # Start with an ordered mapping {sid -> sinfo}
        sid2info = self.courses.filterGrades (klass, realonly=False)
        # Build group info
        for sid, sinfo in sid2info.items ():
            if sinfo.CGROUPS:
                for g in sinfo.CGROUPS.split ():
                    # Distinguish composites and specials
                    if g [0] != '_':
                        components.add (sid)
                    try:
                        groups [g].add (sid)
                    except:
                        groups [g] = {sid}
            try:
                for f in sinfo.FLAGS.split ():
                    if f [0] == CONF.COURSES.UNREAL:
                        unreal [sid] = f
                        break
            finally:
                s2name [sid] = sinfo.COURSE_NAME

        results = OrderedDict ()
        for sid, sname in s2name.items ():
            results [sid] = (sname, sid in components,
                    unreal.get (sid), groups.get (sid))

        return results


class GradeFunctions:
    def __init__ (self, grademap):
        self.grades = grademap
# Make a copy before extending the map?


    @staticmethod
    def getGrade (g):
        try:
            if g [-1] in '-+':
                return int (g [:-1])
            return int (g)
        except:
            # Invalid grade
            return None


    @staticmethod
    def DIVIDE_ROUND (inum, idiv, rounding):
        """Divid <inum> by <idiv> and round to the given number (<rounding>)
        of decimal places. Return the result as a string.
        """
        val = int (((inum * 10**rounding) / idiv) + 0.5)
        sval = "{:0{:d}d}".format (val, rounding + 1)
        if rounding == 0:
            return sval
        # Include the decimal separator
        return (sval [:-rounding]
                + CONF.FORMATTING.DECIMALPOINT
                + sval [-rounding:])



# The real subjects must be evaluated first, these are in self.grades.

    def call (self, f, parms):
        try:
            fx = f [1:].split ('.')
            f = getattr (self, fx [0])
            if f:
                return f (parms, *fx [1:])
        except:
            return "** NYI **"


    def a (self, parms, dps):
        dp = int (dps)
        s = 0
        i = 0
        for p in parms:
            # Get grade
            try:
                g = self.grades [p]
                if g == None:
                    # Empty grade cell
                    return None
#TODO: What about non-grades? How do they count towards averages?!
# I assume they are simply ignored ... which in the case of 'nb' might
# be cheating a bit.
                gn = self.getGrade (g)
                if gn == None:
                    continue
            except:
                # Invalid subject: no grade expected
                continue

            s += gn
            i += 1

        if i > 0:
            return self.DIVIDE_ROUND (s, i, dp)
        return None

#TODO: What about composites where no component is taken? That should
# result in a "nicht teilgenommen" or "–––––" ...



##################### Test functions
_testyear = 2016
_term = 1
_closingdate = '2016-01-18'

def test_01 ():
    REPORT.Test ("5 / 2 = %s" % GradeFunctions.DIVIDE_ROUND (5, 2, 2))
    REPORT.Test ("5 / 2 = %s" % GradeFunctions.DIVIDE_ROUND (5, 2, 0))
    REPORT.Test ("29 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (29, 7, 4))
    REPORT.Test ("29 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (29, 7, 2))
    REPORT.Test ("29 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (29, 7, 0))

def test_02 ():
    klass = '12'
    gtables = GradeTablesX (_testyear, _term)
    REPORT.Test ("\n  >>>>>>>>>>> Class %s: Subject data" % klass)
    for sid, xdata in gtables.collate (klass).items ():
        sname, comp, ftag, parms = xdata
        if comp:
            sid = '[' + sid + ']'
        components = repr (parms) if parms else '---'
        REPORT.Test ("  %s (%s): %s / %s" % (sname, sid,
                ftag or '---', repr (components)))

def test_03 ():
    klass = '12'
    gtables = GradeTablesX (_testyear, _term)
    REPORT.Test ("\n  >>>>>>>>>>> Class %s: Report data" % klass)
    sidinfo = gtables.collate (klass)
    gmatrix = gtables.pid2sid2grade (klass, closingdate=_closingdate)
    for pid, sidmap in gmatrix.items ():
        pgrades = gmatrix [pid]
        gfunctions = GradeFunctions (pgrades)
        REPORT.Test ("  PID: %s" % pid)
        for sid, xdata in sidinfo.items ():
            sname, comp, ftag, parms = xdata
            stag = '[' + sname + ']' if comp else sname
            if ftag:
                val = gfunctions.call (ftag, parms)
            else:
                val = pgrades.get (sid)
            REPORT.Test ("   --- %s: %s" % (sid, repr (val)))

#TODO: I need to keep the pupil data for the reports!
