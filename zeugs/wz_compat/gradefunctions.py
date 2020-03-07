### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/gradefunctions.py

Last updated:  2020-03-06

Calculations needed for grade handling.


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
_EMPTY_GRADE = '?'

# Messages
_MULTIPLE_SUBJECT = "Fach {sid} mehrfach benotet"
_MISSING_DEM = "Keine Note in diesen Fächern: {sids}"
_MISSING_SID = "Keine Note im Fach {sid}"
_BADGRADE = "Ungültige Note im Fach {sid}: {grade}"
_VD11_MISSING = ("Klasse {klass}: Das Datum der Notenkonferenz fehlt.\n"
        "  Siehe Einstellungen/Kalender.")

from fractions import Fraction

from wz_core.db import DB


#DEPRECATED
def gradeCalc(grademap, gcalc):
    """Calculate grades for the subject-ids listed in <gcalc>.
    <grademap> is the raw grade mapping {sid -> grade}. This supplies
    component grades and receives calculated ones.
    """
    for sid in gcalc:
        config = CONF.GRADES.XFIELDS[sid]
        f = getattr(FUNCTIONS, config.FUNCTION)
        val = f(grademap, config)
        grademap[sid] = val


class Frac(Fraction):
    def truncate(self, decimal_places = 0):
        if not decimal_places:
            return str(int(self))
        v = int(self * 10**decimal_places)
        sval = ("{:0%dd}" % (decimal_places+1)).format(v)
        return (sval[:-decimal_places] + ',' + sval[-decimal_places:])

    def round(self, decimal_places = 0):
        f = Fraction(1,2) if self >= 0 else Fraction(-1, 2)
        if not decimal_places:
            return str(int(self + f))
        v = int(self * 10**decimal_places + f)
        sval = ("{:0%dd}" % (decimal_places+1)).format(v)
        return (sval[:-decimal_places] + ',' + sval[-decimal_places:])




def DIVIDE_ROUND(inum, idiv, decimalplaces, idigits=None):
    """Divide <inum> by <idiv> and round to the given number (<rounding>)
    of decimal places. Use integer arithmetic to avoid rounding errors.
    Return the result as a string.
    <idigits> is only for the case <decimalplaces == 0>. It specifies
    whether leading zeros should be generated, by giving the total number
    of digits.
    """
    r = decimalplaces + 1
    v = (inum * 10**r) // idiv
    val = (v + 5) // 10
    if decimalplaces == 0:
        if idigits:
            return ("{:0%dd}" % idigits).format(val)
        return str(val)
    # Include the decimal separator
    sval = ("{:0%dd}" % r).format(val)
    return (sval[:-decimalplaces]
            + CONF.FORMATTING.DECIMALPOINT
            + sval[-decimalplaces:])


def stripsid(sid):
    """Remove everything after the first '.', if there is one.
    """
    return sid.split('.', 1)[0]


class GradeManagerN(dict):
    """Analyse the grades to derive the additional information
    necessary for the evaluation of the results.
    The grades in composite subjects can be calculated and made available
    (via the '.'-stripped sid) as an <int>.
     1) Average
     2) Average DEM
     3) Grades "5" and "6"
    """
    _DEM = ('De', 'En', 'Ma')
    _GRADES = {
            '1': "sehr gut",
            '2': "gut",
            '3': "befriedigend",
            '4': "ausreichend",
            '5': "mangelhaft",
            '6': "ungenügend",
            '*': "––––––",
            'nt': "nicht teilgenommen",
            't': "teilgenommen",
#            'ne': "nicht erteilt",
            'nb': "kann nicht beurteilt werden",
            _UNCHOSEN: None
    }
    VALIDGRADES = (
                '1+', '1', '1-',
                '2+', '2', '2-',
                '3+', '3', '3-',
                '4+', '4', '4-',
                '5+', '5', '5-',
                '6',
                '*', 'nt', 't', 'nb', #'ne',
                _UNCHOSEN
    )


    def printGrade(self, sid):
        """Fetch the grade for the given subject id and return the
        string representation required for the reports.
        """
        try:
            g = self[sid]
        except KeyError:
            return '???'
        try:
            return (self._GRADES[g])
        except KeyError:
            return _EMPTY_GRADE


    def __init__(self, schoolyear, sid2tlist, grademap):
        """Sanitize all "grades" in <grademap>, storing the results as
        instance items.
        Also collect all numeric grades, stripping '+' and '-', as
        instance attribute <grades>:
            {stripped sid -> int}.
        "Component" subjects ('<sid>_<tag>') are collected separately
        as instance attribute <components>:
            {tag -> [(stripped sid, int), ...]
        Attribute <sid0_sid> is a mapping {stripped sid -> sid}.
        A stripped subject is obtained by removing everything from the
        first '.' of the subject id.
        """
        def addcomponent(t, s, g):
            try:
                self.components[t].append((s, g))
            except KeyError:
                self.components[t] = [(s, g)]

#<grademap> could be <None>
        grademap = dict(grademap)   # to preserve the original mapping
        self.schoolyear = schoolyear
        self.sid0_sid = {}  # {stripped sid -> sid}
        # Collect normal grades (not including "component" subjects):
        self.grades = {}    # numeric grades {stripped sid -> int}
        # Collect lists of "component" subjects. The tag is after '_':
        self.components = {}    # {tag -> [(stripped sid, int/None), ...]}
        self.composites = []    # [(sid, composite tag), ...]
        for sid, tlist in sid2tlist.items():
            if tlist == None:
                self[sid] = _UNCHOSEN
                continue
            if tlist.COMPOSITE:
                # A composite
                self.composites.append((sid, tlist.COMPOSITE))
                continue
            g = grademap.get(sid)
            if g == _UNCHOSEN:
                # This allows <grademap> to indicate that this subject
                # is not taken / not valid.
                self[sid] = _UNCHOSEN
                continue
            if not g:
                self[sid] = None
                continue
            # <sid0> is the '.'-stripped subject id.
            # Check that it has only one grade.
            sid0 = stripsid(sid)    # '.'-stripped subject id
            _sid = self.sid0_sid.get(sid0)
            g0 = self.get(_sid)
            if g0:
                REPORT.Fail(_MULTIPLE_SUBJECT, sid=sid0)
            # Differentiate between "normal" and "component" subjects
            try:
                _, tag = sid0.split('_', 1)
            except ValueError:
                tag = None
            # Separate out numeric grades, ignoring '+' and '-'
            plusminus = g[-1]
            if plusminus in '+-':
                try:
                    gint = int(g[:-1])
                    if gint < 1 or gint > 5:
                        raise ValueError
                except ValueError:
                    # Report and ignore
                    REPORT.Error(_BADGRADE, sid=sid, grade=g)
                    self[sid] = None
                    continue
            else:
                plusminus = ''
                try:
                    gint = int(g)
                    if gint < 1 or gint > 6:
                        raise ValueError
                except ValueError:
                    if g not in _GRADES:
                        REPORT.Error(_BADGRADE, sid=sid, grade=g)
                        self[sid] = None
                        continue
                    if tag:
                        addcomponent(tag, sid0, None)
                    self[sid] = g
                    self.sid0_sid[sid0] = sid
                    continue
            # Integer grade ...
            # Sanitized original grade:
            self[sid] = str(gint) + plusminus
            self.sid0_sid[sid0] = sid
            if tag:
                addcomponent(tag, sid0, gint)
            else:
                self.grades[sid0] = gint


    def addDerivedEntries(self):
        """Add entries to the grade mapping for those items/subjects
        which are determined by processing the other grades.
        <self.composites> [(sid, tag), ...] is a list of "composite" subjects,
        whose grade is the average of its "components". The "tag" refers
        to the components.
        Also build lists of "fives" and "sixes".
        """
        for sid, tag in self.composites:
            asum, acount = 0, 0
            try:
                components = self.components[tag]
            except KeyError:
                self[sid] = _UNCHOSEN
                continue
            for s, g in components:
                if g != None:
                    asum += g
                    acount += 1
            if acount:
                g = Frac(asum, acount).round()
                self[sid] = g
                self.grades[sid] = int(g)
            else:
                self[sid] = _NO_AVERAGE

        self.fives = []
        self.sixes = []
        for sid0, g in self.grades.items():
            if g == 5:
                self.fives.append(sid0)
            elif g == 6:
                self.sixes.append(sid0)


#TODO: According to "Verordnung AVO-Sek_I, 2016", the averages should
# not be rounded, but the deviations (2nd decimal place) should be
# insignificant.
    def AVE(self):
        """Return the grade average in all subjects in <self.grades>.
        Round to two decimal places, or return <None> if there are
        be no grades.
        """
        asum, acount = 0, 0
        for sid, g in self.grades.items():
            asum += g
            acount += 1
        return Frac(asum, acount) if acount else None


    def DEM(self):
        """Return the grade average in the subjects De, En, Ma.
        Round to two decimal places, or return <None> if one or more
        grades are missing.
        """
        asum, ok = 0, True
        for sid in self._DEM:
            try:
                asum += self.grades[sid]
            except:
                REPORT.Error(_MISSING_SID, sid=sid)
                ok = False
        return Frac(asum, 3) if ok else None


    def SekI(self):
        """Perform general "pass" tests on grades:
            not more than two times grade "5" or one "6", including
            compensation possibilities.
        """
#WARNING: this doesn't handle differing numbers of lessons in the
# compensating subjects, it only differentiates between DEM subjects
# and the others.
        def compensate(grade):
            for s, g in self.grades.items():
                if g <= grade:
                    if (sid not in self._DEM) or (s in self._DEM):
                        if s not in [csids]:
                            csids.append(s)
                            return True
            return False

        csids = []      # used compensation subjects
        if self.sixes:
            if self.fives or len(self.sixes) > 1:
                return False
            sid = self.sixes[0]
            if compensate(2):
                return True
            return compensate(3) and compensate(3)

        if len(self.fives) > 2:
            return False
        if len(self.fives) < 2:
            return True
        # Check DEM subjects first, as they are more difficult to compensate.
        sid = self.fives[0]
        if sid in self._DEM:
            if compensate(3):
                sid = self.fives[1]
                return compensate(3)
        else:
            sid = self.fives[1]
            if compensate(3):
                sid = self.fives[0]
                return compensate(3)
        return False


    def X_GS(self, rtype, pdata):
        """Determine qualification according to criteria for a
        "Gleichstellungsvermerk". Only a "Hauptschulabschluss" is
        possible.
        """
        gs = ''
        if rtype == 'Abgang':
            if self.SekI():
                ave = self.AVE()
                if ave and ave <= Frac(4, 1):
                    gs = 'HS'
        self['_GS'] = gs
        return gs


    def X_Q12(self, rtype, pdata):
        """Determine qualification at end of 12th year for a "Realschüler"
        or a "Hauptschüler".
        """
        q = ''
        if rtype == 'Abschluss':
            stream = pdata['STREAM']
            if self.SekI():
                ave = self.AVE()
                dem = self.DEM()
                if ave and dem:
                    tst = ave if ave > dem else dem
                    if stream == 'RS':
                        if tst <= Frac(3, 1):
                            q = 'Erw'
                        elif tst <= Frac(4, 1):
                            q = 'RS'
                    elif stream == 'HS' and tst <= Frac(4, 1):
                        q = 'HS'
        return q


    def X_V_D(self, rtype, pdata):
        """For the "gymnasial" group, 11th class. Determine qualification
        for the 12th class.
        """
        date = ''
        klass = pdata['CLASS']
        if (klass.startswith('11') and pdata['STREAM'] != 'Gym'
                and rtype == 'Zeugnis' and self.SekI()):
            ave = self.AVE()
            if ave and ave <= Frac(3, 1):
                date = DB(self.schoolyear).getInfo('Versetzungsdatum_' + klass)
                if not date:
                    REPORT.Fail(_VD11_MISSING, klass = klass)
        self['_V_D'] = date
        return date





#DEPRECATED
class FUNCTIONS:
    @staticmethod
    def AVERAGE(grademap, config):
        """The average of the component grades, for a composite grade.
        The grade scale must be detected.
        """
        idigits = 0
        # <tag> is the sid extension (after '_') determining the components.
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


#TODO
    @classmethod
    def FachAbiGrade (cls, points):
        """Use a formula to calculate "Abiturnote" (Waldorf/Niedersachsen).
        To avoid rounding errors, use integer arithmetic.
        """
        g420 = 2380 - points*20 + 21
        p420 = str (g420 // 420) + cls._dp + str ((g420 % 420) // 42)
        return p420


#TODO
class GradeManagerQ1(dict):
    pass

#TODO
class GradeManagerQ2(dict):
    pass


def Manager(klass):
    if klass.klass >= '13':
        return GradeManagerQ2
    if klass.klass >= '12' and klass.stream == 'Gym':
        return GradeManagerQ1
    return GradeManagerN


##################### Test functions
def test_01 ():
    REPORT.Test ("5 / 9 = %s" % Frac(5, 9).round(2))
    REPORT.Test ("5 / 9 = %s" % Frac(5, 9).round())
    REPORT.Test ("5 / 9 = %s" % Frac(5, 9).round().zfill(3))
    REPORT.Test ("5 / 2 = %s" % Frac(5, 2).round(2))
    REPORT.Test ("5 / 2 = %s" % Frac(5, 2).round())
    REPORT.Test ("5 / 2 = %s" % Frac(5, 2).truncate())
    REPORT.Test ("200 / 3 = %s" % Frac(200, 3).round(2).zfill(0))
    REPORT.Test ("200 / 3 = %s" % Frac(200, 3).truncate(2).zfill(6))
    REPORT.Test ("31 / 7 = %s" % Frac(31, 7).round(4))
    REPORT.Test ("31 / 7 = %s" % Frac(31, 7).round(3))
    REPORT.Test ("31 / 7 = %s" % Frac(31, 7).round(2))
    REPORT.Test ("31 / 7 = %s" % Frac(31, 7).round(1))
    REPORT.Test ("31 / 7 = %s" % Frac(31, 7).round())
