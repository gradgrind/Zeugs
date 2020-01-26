# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/gradefunctions.py

Last updated:  2020-01-26

Handling for grades which are the result of calculations.


=+LICENCE=============================
Copyright 2019-2020 Michael Towers

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
_NO_AVERAGE = '*'


def gradeCalc(grademap, gcalc):
    """Calculate grades for the subject-ids listed in <gcalc>.
    <grademap> is the grade mapping {sid -> grade}. This supplies
    component grades and receives calculated ones.
    """
    for sid in gcalc:
        config = CONF.GRADES.XFIELDS[sid]
        f = getattr(FUNCTIONS, config.FUNCTION)
        val = f(grademap, config)
        grademap[sid] = val



def DIVIDE_ROUND(inum, idiv, rounding, idigits=None):
    """Divide <inum> by <idiv> and round to the given number (<rounding>)
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
            return ("{:0%dd}" % idigits).format(val)
        return str(val)
    # Include the decimal separator
    sval = ("{:0%dd}" % r).format(val)
    return (sval[:-rounding]
            + CONF.FORMATTING.DECIMALPOINT
            + sval[-rounding:])



class FUNCTIONS:
    @staticmethod
    def AVERAGE(grademap, config):
        """The average of the component grades, for a composite grade.
        <tag> is the sid extension (after '_') determining the components.
        It must detect the grade scale.
        """
        idigits = 0
        tag = '_' + config.TAG
        asum, acount = 0, 0
        for sid, g in grademap.items():
            if sid.endswith(tag):
                g = g.rstrip('+-')
                try:
                    asum += int(g)
                except ValueError:
                    # Not an integer
                    continue
                acount += 1
                if len(g) == idigits:
                    continue
                if idigits:
                    REPORT.Bug("Inconsistent grade scale. Grades: %s" % repr(grademap))
                idigits = len(g)
        if acount:
            # Use integer arithmetic to calculate average
            return DIVIDE_ROUND (asum, acount, 0, idigits=idigits)
        return _NO_AVERAGE




##################### Test functions
def test_01 ():
    REPORT.Test ("3 / 7 = %s" % DIVIDE_ROUND (3, 7, 2))
    REPORT.Test ("3 / 7 = %s" % DIVIDE_ROUND (3, 7, 0, 1))
    REPORT.Test ("3 / 7 = %s" % DIVIDE_ROUND (3, 7, 0, 2))
    REPORT.Test ("5 / 2 = %s" % DIVIDE_ROUND (5, 2, 2))
    REPORT.Test ("5 / 2 = %s" % DIVIDE_ROUND (5, 2, 0, 0))
    REPORT.Test ("5 / 2 = %s" % DIVIDE_ROUND (5, 2, 0, 3))
    REPORT.Test ("7 / 2 = %s" % DIVIDE_ROUND (7, 2, 2))
    REPORT.Test ("7 / 2 = %s" % DIVIDE_ROUND (7, 2, 0))
    REPORT.Test ("31 / 7 = %s" % DIVIDE_ROUND (31, 7, 4))
    REPORT.Test ("31 / 7 = %s" % DIVIDE_ROUND (31, 7, 3))
    REPORT.Test ("31 / 7 = %s" % DIVIDE_ROUND (31, 7, 2))
    REPORT.Test ("31 / 7 = %s" % DIVIDE_ROUND (31, 7, 1))
    REPORT.Test ("31 / 7 = %s" % DIVIDE_ROUND (31, 7, 0))
