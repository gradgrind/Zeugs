#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/gradefunctions.py

Last updated:  2019-10-11

Calculation handling for "subjects" with entries in the CALC column.


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

_UNCHOSEN = '/'

def validGrades (pupilData):
    """Return a list of valid grades for the grade table.
    """
    gs = getGradeScale (pupilData.klassStream ())
    return list (gs.VALID)


def getGradeScale (ks0):
    for f in CONF.GRADES.list ():
        if f.startswith ('GRADES_'):
            cf = CONF.GRADES [f]
            for ks in cf.GROUPS:
                if ks == ks0:
                    return cf
    # Default:
    return CONF.GRADES.GRADES



class GradeFunctions:
    def __init__ (self, grademap):
        """<grademap> is a subject -> grade mapping as is available for a
        pupil in the result of <GradeTablesX.pid2sid2grade>.
        """
        self.grades = grademap
#TODO: Make a copy before extending the map?


    @staticmethod
    def getGrade (g):
        try:
            if g [-1] in '-+':
                return int (g [:-1])
            return int (g)
        except:
            # Invalid grade
            return None


    def gradeInfo (self):
        """Fetch the grade-scale info.
        """
        ks = self.grades.pupilData.klassStream ()
        return getGradeScale (ks)


    @staticmethod
    def DIVIDE_ROUND (inum, idiv, rounding, idigits=None):
        """Divid <inum> by <idiv> and round to the given number (<rounding>)
        of decimal places. Use integer arithmetic to avoid rounding errors.
        Return the result as a string.
        <idigits> is only for the case <rounding == 0>. It specifies whether
        leading zeros should be generated, by giving the total number of
        digits.
        """
        r = rounding + 1
        v = (inum * 10**r) // idiv
        val = (v + 5) // 10
        if rounding == 0:
            if idigits:
                return ("{:0%dd}" % idigits).format (val)
            return str (val)
        # Include the decimal separator
        sval = ("{:0%dd}" % r).format (val)
        return (sval [:-rounding]
                + CONF.FORMATTING.DECIMALPOINT
                + sval [-rounding:])


# The real subjects must be evaluated first, these are in self.grades.

    def call (self, f, parms):
        """Invoke a calculation function.
        <parms> is the list of subject groups (sids) on which this calculation
        depends, from the CGROUPS columns of the components.
        """
        try:
            f = getattr (self, f)
            if f:
                return f (parms)
        except:
            return "** NYI **"


    def _isum (self, parms):
        """Calculate the sum of a set of grades.
        Also the number of valid grades is returned.
        Finally a "tag" is returned, which can be '' (ok), '?' (one or
        more grades was non-numeric and not _UNCHOSEN) or '!' (one or
        more grades was missing.
        """
        s = 0
        i = 0
        tag = None
        for p in parms:
            # Get grade
            try:
                g = self.grades [p]
                if g == None:
                    # Empty grade cell
                    tag = '!'
                    continue
                gn = self.getGrade (g)
                if gn == None:
                    if g == _UNCHOSEN:
                        # Only this one has no effect on the average,
                        # essentially equivalent to the subject having
                        # no teacher in the course matrix.
                        continue
                    if not tag:
                        tag = '?'
                    continue
            except:
                # Invalid subject: no grade expected
                continue

            s += gn
            i += 1
        return (s, i, tag)


    def k (self, parms):
        """Composite grade: the average of the component grades.
        If an expected component is missing, the result will have '!'
        appended.
        If there are non-numerical grades, the result will have '?'
        appended.
        """
        s, i, tag = self._isum (parms)
        if i > 0:
            # Use integer arithmetic to calculate average.
            v = self.DIVIDE_ROUND (s, i, 0, self.gradeInfo ().DIGITS.nat ())
            return v + tag if tag else v
        return tag


    def a (self, parms):
        """The average of the component grades.
        If an expected component is missing, the result will have '!'
        appended.
        If there are non-numerical grades, the result will have '?'
        appended.
        """
        s, i, tag = self._isum (parms)
        if i > 0:
            # Use integer arithmetic to calculate average.
            v = self.DIVIDE_ROUND (s, i, 2)
            return v + tag if tag else v
        return tag



##################### Test functions
def test_01 ():
    REPORT.Test ("3 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (3, 7, 2))
    REPORT.Test ("3 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (3, 7, 0, 1))
    REPORT.Test ("3 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (3, 7, 0, 2))
    REPORT.Test ("5 / 2 = %s" % GradeFunctions.DIVIDE_ROUND (5, 2, 2))
    REPORT.Test ("5 / 2 = %s" % GradeFunctions.DIVIDE_ROUND (5, 2, 0, 0))
    REPORT.Test ("5 / 2 = %s" % GradeFunctions.DIVIDE_ROUND (5, 2, 0, 3))
    REPORT.Test ("7 / 2 = %s" % GradeFunctions.DIVIDE_ROUND (7, 2, 2))
    REPORT.Test ("7 / 2 = %s" % GradeFunctions.DIVIDE_ROUND (7, 2, 0))
    REPORT.Test ("31 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (31, 7, 4))
    REPORT.Test ("31 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (31, 7, 3))
    REPORT.Test ("31 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (31, 7, 2))
    REPORT.Test ("31 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (31, 7, 1))
    REPORT.Test ("31 / 7 = %s" % GradeFunctions.DIVIDE_ROUND (31, 7, 0))
