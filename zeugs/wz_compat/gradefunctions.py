# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/gradefunctions.py

Last updated:  2020-02-15

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


_NO_GRADE = "Kein Ergebnis in %s"
_NULL_ERROR = "0 Punkte in %s"
_LOW1_ERROR = "Punkte in schriftlichen Fächer < 220"
_LOW2_ERROR = "Punkte in mündlichen Fächer < 80"
_UNDER2_1_ERROR = "< 2 schriftliche Fächer mit mindestens 5 Punkten"
_UNDER2_2_ERROR = "< 2 mündliche Fächer mit mindestens 5 Punkten"
_FAILED = "Abitur nicht bestanden: {error}"
_INVALID_GRADES = ("Ungültige Fächer/Noten für {pname}, erwartet:\n"
        "  .e .eN .e .eN .e .eN .g .gN .m .m .m .m")

class AbiCalc:
    """Manage a mapping of all necessary grade components for an
    Abitur report.
    """
    _gradeText = {'0': 'null', '1': 'eins', '2': 'zwei', '3': 'drei',
            '4': 'vier', '5': 'fünf', '6': 'sechs', '7': 'sieben',
            '8': 'acht', '9': 'neun'
    }

    @staticmethod
    def fixGrade(g):
        if g:
            return '––––––' if g == '*' else g
        else:
            return '?'


    def __init__(self, sid_name, sid2grade):
        self.zgrades = {}
        i = 0
        for sid, sname in sid_name:
            i += 1
            self.zgrades["F%d" % i] = sname
            self.zgrades["S%d" % i] = self.fixGrade(sid2grade[sid])
            if i <= 4:
                self.zgrades["M%d" % i] = self.fixGrade(sid2grade[sid + 'N'])
                if i == 4 and sid.endswith('.g'):
                    continue
                if sid.endswith('.e'):
                    continue
            elif sid.endswith('.m'):
                continue
            REPORT.Fail(_INVALID_GRADES, pname=pdata.name())


    def getFullGrades(self):
        """Return the tag mapping for an Abitur report.
        """
        gmap = self.zgrades.copy()
        errors = []
        ### First the 'E' points
        eN = []
        n1, n2 = 0, 0
        for i in range(1, 9):
            try:
                s = int(gmap["S%d" % i])
            except:
                errors.append(_NO_GRADE % gmap["F%d" % i])
                s = 0
            if i <= 4:
                # written exam
                f = 4 if i == 4 else 6  # gA / eA
                try:
                    e = s + int(gmap["M%d" % i])
                except:
                    e = s + s
                if e >= 10:
                    n1 += 1
                e *= f
            else:
                # oral exam
                e = 4 * s
                if e >= 20:
                    n2 += 1
            gmap["E%d" % i] = str(e)
            eN.append(e)
            if e == 0:
                errors.append(_NULL_ERROR % gmap["F%d" % i])

        t1 = eN[0] + eN[1] + eN[2] + eN[3]
        gmap["TOTAL1"] = t1
        if t1 < 220:
            errors.append(_LOW1_ERROR)
        t2 = eN[4] + eN[5] + eN[6] + eN[7]
        gmap["TOTAL2"] = t2
        if t2 < 80:
            errors.append(_LOW1_ERROR)
        if n1 < 2:
            errors.append(_UNDER2_1_ERROR)
        if n2 < 2:
            errors.append(_UNDER2_2_ERROR)

        if errors:
            gmap["Grade1"] = "–––"
            gmap["Grade2"] = "–––"
            gmap["GradeT"] = "–––"
            for e in errors:
                REPORT.Warn(_FAILED, error=e)
            return gmap

#TODO: What about Fachabi?

        # Calculate final grade using a formula. To avoid rounding
        # errors, use integer arithmetic.
        g180 = (1020 - t1 - t2)
        g1 = str (g180 // 180)
        gmap["Grade1"] = g1
        g2 = str ((g180 % 180) // 18)
        gmap["Grade2"] = g2
        gmap["GradeT"] = self._gradeText[g1] + ", " + self._gradeText[g2]
        return gmap



########################################################################
#TODO: Below are some old Abitur-functions which need to be integrated:

_NOOPERATOR         = "Notenberechnung nicht definiert: {sbj}"
_BADOP              = "Notenberechnung schlug fehl: {sbj}"
_WEIGHTEDCRITERION  = "Notenberechnung darf nicht gewichtete Komponenten haben: {sbj}"
_WRITTENNOT4        = "Notenberechnung: {n} schriftliche Fächer (nicht 4)"
_ORALNNOT4          = "Notenberechnung: {n} mündliche Fächer (nicht 4)"

_PASS = "ja"
_FAIL = "nein"

class GradeEval:
    _gradeScale = None
    _subject = None
    _dp = None
    _gradeText = {'0': 'null', '1': 'eins', '2': 'zwei', '3': 'drei', '4': 'vier',
            '5': 'fünf', '6': 'sechs', '7': 'sieben', '8': 'acht', '9': 'neun'}


    @classmethod
    def setGradeScale (cls, gscale):
        cls._gradeScale = gscale
        cls._dp = CONFIG.FORMATTING.DECIMALPOINT.string ()


    @classmethod
    def str2grade (cls, sgrade, w):
        """Scale a grade possibly containing a decimal separator.
        The result should be an integer.
        """
        gflt = float (sgrade.replace (cls._dp, '.'))
        return int (gflt * w + 0.5)


    @classmethod
    def call (cls, sbj, op, s_w, s_grade):
        cls._subject = sbj
        opsplit = op.split ('.')
        try:
            f = getattr (cls, opsplit [0])
        except:
            REPORT.Error (_NOOPERATOR, sbj=cls._subject)
            return None
        try:
            return f (s_w, s_grade, *opsplit [1:])
        except:
            REPORT.Error (_BADOP, sbj=cls._subject)
            return None


    @classmethod
    def COMPOSITE_SFACH (cls, components, s_grade):
        """Calculate a (weighted) average of the contributions.
        Round to nearest integer.
        """
        vsum = 0
        i = 0
        nograde = None
        gscale = CONFIG.GRADES [cls._gradeScale]
        for s, w in components.items ():
            try:
                val = s_grade [s]
                if not val:
                    # Any empty component causes the result to be empty
                    return None
            except:
                continue
            try:
                # Only consider genuine grades
                ival = int (val.rstrip ('+-'))
            except:
                if i == 0:
                    # Prepare for "no grade" result
                    for np in gscale.NOGRADE_PRIORITY:
                        if np == nograde:
                            break
                        if np == val:
                            nograde = np
                            break
                continue
            vsum += ival * w
            i += w

        if i == 0:
            return (gscale.NOGRADE_PRIORITY [-1]
                    if nograde == None else nograde)

        vsum = int (vsum / i + 0.5)
        return "{:0{:d}d}".format (vsum, gscale.DIGITS.nat ())


    @classmethod
    def CALC_MITTEL (cls, components, s_grade, rounding):
        """Calculate a (weighted) average of the contributions.
        Round to given number of decimal places. Note that <rounding>
        is a string!
        """
        vsum = 0
        i = 0
        gscale = CONFIG.GRADES [cls._gradeScale]
        for s, w in components.items ():
            try:
                val = s_grade [s]
                if not val:
                    # Any empty component causes the result to be empty
                    return None
            except:
                continue
            try:
                # Only consider genuine grades
                ival = int (val.rstrip ('+-'))
            except:
                continue
            vsum += ival * w
            i += w

        if i == 0:
            return None

        rint = int (rounding)
        vsum = int (((vsum * 10**rint) / i) + 0.5)
        val = "{:0{:d}d}".format (vsum, rint+1)
        # Include the decimal separator
        return (val [:-rint]
                + CONFIG.FORMATTING.DECIMALPOINT.string ()
                + val [-rint:])


    @classmethod
    def CALC_ABI (cls, components, s_grade, subcalc, *args):
        """Calculations for the Abitur result.
        """
        if subcalc == "f4":
            # (z0, p52, s220, s_alle) or (z0, m52, s80, s_alle)
            try:
                bpmin = int (args [0])
                if bpmin not in (220, 80):
                    raise ValueError
            except:
                REPORT.Error (_NOOPERATOR, sbj=cls._subject)
                return '0:0:0:0'
            if len (components) != 4:
                REPORT.Error (_WRITTENNOT4 if bpmin == 220 else _ORALNNOT4,
                        n=len (components))
                return '0:0:0:0'
            isum = 0
            i0 = 0
            i5 = 0
            for s, w in components.items ():
                try:
                    val = cls.str2grade (s_grade [s], w)
                except:
                    i0 += 1
                    continue
                isum += val
                if val == 0:
                    i0 += 1
                elif val >= 5 * w:
                    i5 += 1
            res = [ '1' if i0 == 0 else '0',
                    '1' if i5 >= 2 else '0',
                    '1' if isum >= bpmin else '0',
                    str (isum)]
            return ':'.join (res)

        if subcalc == "ok":
            try:
                i = int (args [0])
            except:
                REPORT.Error (_NOOPERATOR, sbj=cls._subject)
                return None

            for s, w in components.items ():
                if w != 1:
                    REPORT.Error (_WEIGHTEDCRITERION, sbj=cls._subject)
                    return None
                if s_grade [s].split (':') [i] != '1':
                    return _FAIL
            return _PASS

        if subcalc == "teil":
            if len (components) != 1:
                REPORT.Error (_ONEEXPECTED, sbj=cls._subject)
                return None
            for s, w in components.items ():
                try:
                    vsplit = s_grade [s].rsplit (':', 1)
                    val = int (vsplit [1])
                except:
                    return None
                return str (val)


        if subcalc == "summe":
            # Weighted sum.
            i = 0
            for s, w in components.items ():
                try:
                    vsplit = s_grade [s].rsplit (':', 1)
                    val = int (vsplit [1])
                except:
                    return None
                if vsplit [0] != '1:1:1':
                    # Only return a value if all tests pass.
                    return None
                i += val * w
            return str (i)

        elif subcalc == "Note":
            # Presentation of the grade.
            if len (components) != 1:
                REPORT.Error (_ONEEXPECTED, sbj=cls._subject)
                return None
            for s, w in components.items ():
                break
            ntype = args [0]
            if ntype == 'N':
                try:
                    val = int (s_grade [s]) * w
                except:
                    return None
                return cls.AbiGrade (val)
            else:
                if w != 1:
                    REPORT.Error (_WEIGHTEDCRITERION, sbj=cls._subject)
                    return None
                val = s_grade [s]
                if not val:
                    return None
                d1, d2 = val.split (cls._dp)
                if ntype == '1':
                    return d1
                elif ntype == '2':
                    return d2
                elif ntype == 'T':
                    return cls._gradeText [d1] + cls._dp + ' ' + cls._gradeText [d2]
                REPORT.Error (_NOOPERATOR, sbj=cls._subject)


    @classmethod
    def CALC_BP (cls, components, s_grade):
        """Abitur: "Bewertungspunkte" (scaled average).
        One, and only one, component is expected.
        """
        if len (components) != 1:
            REPORT.Error (_ONEEXPECTED, sbj=cls._subject)
            return None
        for s, w in components.items ():
            try:
                val = cls.str2grade (s_grade [s], w)
                return str (val)
            except:
                return None


    @classmethod
    def AbiGrade (cls, points):
        """Use a formula to calculate "Abiturnote". To avoid rounding
        errors, use integer arithmetic.
        """
        g180 = (1020 - points)
        p180 = str (g180 // 180) + cls._dp + str ((g180 % 180) // 18)
        return p180


    @classmethod
    def FachAbiGrade (cls, points):
        """Use a formula to calculate "Abiturnote" (Waldorf/Niedersachsen).
        To avoid rounding errors, use integer arithmetic.
        """
        g420 = 2380 - points*20 + 21
        p420 = str (g420 // 420) + cls._dp + str ((g420 % 420) // 42)
        return p420





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
