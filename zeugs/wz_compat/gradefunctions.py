### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/gradefunctions.py

Last updated:  2020-04-09

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

STREAMS = ('Gym', 'RS', 'HS')
_UNCHOSEN = '/'
_NO_AVERAGE = '*'

# Messages
_MULTIPLE_SUBJECT = "Fach {sid} mehrfach benotet"
_MISSING_DEM = "Keine Note in diesen Fächern: {sids}"
_MISSING_SID = "Keine Note im Fach {sid}"
_BADGRADE = "Ungültige Note im Fach {sid}: {grade}"
_MISSING_ABI_GRADE = "{pname}: Note fehlt im Abiturfach {sid}"
_FAILV = "{pname} wird nicht versetzt"
_FAILQ = "{pname} erlangt den Abschluss nicht"
# ... for Abitur final reports
_NO_GRADE = "Kein Ergebnis in %s"
_NULL_ERROR = "0 Punkte in %s"
_LOW1_ERROR = "Punkte in schriftlichen Fächer < 220"
_LOW2_ERROR = "Punkte in mündlichen Fächer < 80"
_UNDER2_1_ERROR = "< 2 schriftliche Fächer mit mindestens 5 Punkten"
_UNDER2_2_ERROR = "< 2 mündliche Fächer mit mindestens 5 Punkten"
_FAILED = "Abitur nicht bestanden: {error}"
_INVALID_GRADES = ("Ungültige Fächer/Noten für {pname}, erwartet:\n"
        "  .e .eN .e .eN .e .eN .g .gN .m .m .m .m")


from fractions import Fraction

from wz_core.db import DBT


class GradeError(Exception):
    pass


class Frac(Fraction):
    def truncate(self, decimal_places = 0):
        if not decimal_places:
            return str(int(self))
        v = int(self * 10**decimal_places)
        sval = ("{:0%dd}" % (decimal_places+1)).format(v)
        return (sval[:-decimal_places] + ',' + sval[-decimal_places:])
#
    def round(self, decimal_places = 0):
        f = Fraction(1,2) if self >= 0 else Fraction(-1, 2)
        if not decimal_places:
            return str(int(self + f))
        v = int(self * 10**decimal_places + f)
        sval = ("{:0%dd}" % (decimal_places+1)).format(v)
        return (sval[:-decimal_places] + ',' + sval[-decimal_places:])



def stripsid(sid):
    """Remove everything after the first '.', if there is one.
    """
    return sid.split('.', 1)[0]



def Manager(klass):
    if klass.klass >= '13':
        return GradeManagerQ1
    if klass.klass >= '12' and klass.stream == 'Gym':
        return GradeManagerQ1
    return GradeManagerN



class _GradeManager(dict):
    """Analyse the grades to derive the additional information
    necessary for the evaluation of the results.
    The grades in composite subjects can be calculated and made available
    (via the '.'-stripped sid) as an <int>.
    """
    ZPAD = 1    # set to 2 to force leading zero (e.g. '6' -> '06')

    def __init__(self, schoolyear, sid2tlist, grademap):
        """Sanitize all "grades" in <grademap>, storing the results as
        instance items.
        Also collect all numeric grades as instance attribute <grades>:
            {stripped sid -> int}.
        "Component" subjects ('<sid>_<tag>') are collected separately
        as instance attribute <components>:
            {tag -> [(stripped sid, int), ...]
        Attribute <sid0_sid> is a mapping {stripped sid -> sid}.
        A stripped subject is obtained by removing everything from the
        first '.' of the subject id.
        """
        super().__init__()

        def addcomponent(t, s, g):
            try:
                self.components[t].append((s, g))
            except KeyError:
                self.components[t] = [(s, g)]

        # Preserve the original mapping:
        grademap = dict(grademap) if grademap else {}
        self.schoolyear = schoolyear
        self.sid0_sid = {}  # {stripped sid -> sid}
        # Collect normal grades (not including "component" subjects):
        self.grades = {}    # numeric grades {stripped sid -> int}
        # Collect lists of "component" subjects. The tag is after '_':
        self.components = {}    # {tag -> [(stripped sid, int/None), ...]}
        self.composites = {}    # {sid -> composite tag}
        self.XINFO = {}         # additional (calculated) fields
        for sid, tlist in sid2tlist.items():
            if tlist == None:
                continue
            if tlist.COMPOSITE:
                # A composite
                self.composites[sid] = tlist.COMPOSITE
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
            tag = sid2tlist.component[sid]
            gint = self.gradeFilter(sid, g)
            if gint != None:
                self.sid0_sid[sid0] = sid
                if tag:
                    addcomponent(tag, sid0, None if gint < 0 else gint)
                elif gint >= 0:
                    self.grades[sid0] = gint


    def addDerivedEntries(self):
        """Add entries to the grade mapping for those items/subjects
        which are determined by processing the other grades.
        <self.composites> {sid -> tag} is a mapping of "composite"
        subjects, whose grade is the average of its "components". The
        "tag" refers to the components.
        """
        for sid, tag in self.composites.items():
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
                self[sid] = g.zfill(self.ZPAD)
                self.grades[sid] = int(g)
            else:
                self[sid] = _NO_AVERAGE


    def SET(self, tagmap):
        """<tagmap> should be a mapping of lists containing
        (subject, grade) tuples: {subject-group -> [(s, g), ...]}.
        This is for the exclusive use of the <GET> method.
        """
        self._tagmap = tagmap

    def GET(self, g):
        """<g> is a subject-group.
        Return the next entry in the group's subject/grade list,
        removing that entry from the list.
        """
        try:
            glist = self._tagmap[g]
            return glist.pop(0)
        except:
            return None

    def NOSHOW(self, g):
        """Indicate that no (further) subjects in the given group will
        be called for and, especially, that this is no error, any
        remaining subjects are to be silently ignored.
        Return the current contents.
        """
        glist = self._tagmap[g]
        self._tagmap[g] = []
        return glist



class GradeManagerN(_GradeManager):
    """Handle grades on the 1–6 scale, including '+' and '-'.
    Add analysis methods for:
     1) Average
     2) Average DEM
     3) Grades "5" and "6"
    """
    _DEM = ('De', 'En', 'Ma')   # for RS-Abschluss only
    _DMF = ('De', 'Ma', 'En', 'Fr', 'Ru', 'La') # for "Ausgleich" rules
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
            _UNCHOSEN: None,
            '': '?'
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
    XNAMES = {
            'AVE': 'Φ Alle Fächer',
            'DEM': 'Φ De-En-Ma',
            'GS': 'Gleichstellungsvermerk',
            'V': 'Versetzung (Quali)',
            'Q12': 'Abschluss 12. Kl.'
    }


    def printGrade(self, g):
        """Fetch the grade for the given subject id and return the
        string representation required for the reports.
        """
        return self._GRADES[g.rstrip('+-')]


    def gradeFilter(self, sid, g):
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
                return None
        else:
            plusminus = ''
            try:
                gint = int(g)
                if gint < 1 or gint > 6:
                    raise ValueError
            except ValueError:
                if g not in self.VALIDGRADES:
                    REPORT.Error(_BADGRADE, sid=sid, grade=g)
                    self[sid] = None
                    return None
                self[sid] = g
                return -1
        # Integer grade ...
        # Sanitized original grade:
        self[sid] = str(gint) + plusminus
        return gint


#NOTE: According to "Verordnung AVO-Sek_I, 2016", the averages should
# be truncated, not rounded, but the deviations (2nd decimal place)
# should be insignificant anyway.
    def X_AVE(self, pdata = None):
        """Return the grade average in all subjects in <self.grades>.
        Round to two decimal places, or return <None> if there are
        no grades.
        """
        try:
            return self._AVE
        except:
            pass
        asum, acount = 0, 0
        for sid, g in self.grades.items():
#            REPORT.Test('??? %s: %s' % (sid, g))
            asum += g
            acount += 1
        avg = Frac(asum, acount) if acount else None
        self._AVE = avg
        self.XINFO['AVE'] = avg.truncate(2)
#        REPORT.Test('??? ----> %s' % self.XINFO['AVE'])
        return avg


    def X_DEM(self, pdata = None):
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
        dem = Frac(asum, 3) if ok else None
        self.XINFO['DEM'] = dem.truncate(2)
        return dem


    def SekI(self):
        """Perform general "pass" tests on grades:
        not more than two times grade "5" or one "6", including
        compensation possibilities.
        """
#WARNING: this doesn't handle differing numbers of lessons in the
# compensating subjects, it only differentiates between DMF subjects
# and the others.
        def compensate(sid, grade):
            for s, g in self.grades.items():
                if g <= grade:
                    if (sid not in self._DMF) or (s in self._DMF):
                        if s not in csids:
                            csids.append(s)
                            return True
            return False

        def seki():
            # Build lists of "fives" and "sixes".
            self.fives = []
            self.sixes = []
            for sid0, g in self.grades.items():
                if g == 5:
                    self.fives.append(sid0)
                elif g == 6:
                    self.sixes.append(sid0)

            if self.sixes:
                if self.fives or len(self.sixes) > 1:
                    return False
                sid = self.sixes[0]
                if compensate(sid, 2):
                    return True
                return compensate(sid, 3) and compensate(sid, 3)

            if len(self.fives) < 2:
                return True
            if len(self.fives) > 2:
                return False
            # Check DMF subjects first, as they are more difficult to compensate.
            sid = self.fives[0]
            if sid in self._DMF:
                if compensate(sid, 3):
                    sid = self.fives[1]
                    return compensate(sid, 3)
            else:
                sid = self.fives[1]
                if compensate(sid, 3):
                    sid = self.fives[0]
                    return compensate(sid, 3)
            return False

        try:
            return self._SEKI
        except:
            pass
        csids = []      # used compensation subjects
        self._SEKI = seki()
        return self._SEKI


#NOTE: Concerning leaving before the end of year 12 the "Verordnung
# AVO-Sek_I, 2016" is in some respects not 100% clear. I interpret it
# thus: All grades must be 4 or better, but with the possibility for
# compensation as implemented in the method <SekI>.
    def X_GS(self, pdata = None):
        """Determine qualification according to criteria for a
        "Gleichstellungsvermerk". Only a "Hauptschulabschluss" is
        possible.
        """
        xgs = '-'
        if self.SekI():
            ave = self.X_AVE()
            if ave and ave <= Frac(4, 1):
                xgs = 'HS'
        self.XINFO['GS'] = xgs
        return xgs


    def X_Q12(self, pdata):
        """Determine qualification at end of 12th year for a "Realschüler"
        or a "Hauptschüler".
        """
        q12 = '-'
        stream = pdata['STREAM']
        if self.SekI():
            ave = self.X_AVE()
            dem = self.X_DEM()
            if ave and dem:
                if ave <= Frac(4, 1):
                    # This is necessary for all qualifications
                    if stream == 'HS':
                        q12 = 'HS'
                    elif stream == 'RS':
                        if ave <= Frac(3, 1) and dem <= Frac(3, 1):
                            q12 = 'Erw'
                        else:
                            q12 = 'RS'
        self.XINFO['Q12'] = q12
        return q12

#TODO: Actually there should also be a Q11, which is basically the same
# as Q12 – including the final exams, but "Erw" is not possible
# ("Verordnung AVO-Sek_I, 2016, §47 Abs 2").


    def X_V(self, pdata):
        """For the "gymnasial" group, 11th class. Determine qualification
        for the 12th class. Return '✓' or '-'.
        """
        v = '-'
        ave = self.X_AVE()
        klass = pdata['CLASS']
        if (klass.startswith('11') and pdata['STREAM'] == 'Gym'
                and self.SekI()):
            if ave and ave <= Frac(3, 1):
                v = '✓'
        self.XINFO['V'] = v
        return v


    def reportFail(self, term, rtype, pdata):
        if rtype == 'Zeugnis':
            if term == '2' and pdata['STREAM'] == 'Gym':
                if self.XINFO['V'] == '-':
                    REPORT.Warn(_FAILV, pname = pdata.name())
            # include even if the pupil failed
        elif rtype == 'Abschluss':
            if self.XINFO['Q12'] == '-':
                REPORT.Warn(_FAILQ, pname = pdata.name())
                return False    # don't include
        return True


class AbiSubjects(list):
    FS2 = ('Fr', 'Ru', 'La')
# Note that this assumes that the first foreign language is always
# English ...
    def __init__(self, schoolyear, pid, fhs = False):
        with DBT(schoolyear) as db:
            sids = db.select1('ABI_SUBJECTS', PID = pid)
        if not sids:
            raise ValueError('Keine Abifächer')
        slist = sids['SUBJECTS'].split(',')
        if len(slist) != 8:
            raise ValueError('Abifächeranzahl ≠ 8')
        if fhs:
            for s in slist:
                if s in self.FS2:
                    slist.remove(s)
            if len(slist) != 7:
                raise ValueError('Fachabifächeranzahl ≠ 7')
        super().__init__(slist)

    @classmethod
    def demafs(cls, sid):
        """Check whether the given subject is Deutsch, Mathe or
        a Fremdsprache.
        """
        s = sid.split('.', 1)[0]
        return s in ('De', 'Ma', 'En') or s in cls.FS2



class GradeManagerQ1(_GradeManager):
    ZPAD = 2    # all (numeric) grades have two digits (e.g. '1' -> '01')
    VALIDGRADES = (
                '15', '14', '13',
                '12', '11', '10',
                '09', '08', '07',
                '06', '05', '04',
                '03', '02', '01',
                '00',
                '*', 'nt', 't', 'nb', #'ne',
                _UNCHOSEN
    )
    XNAMES = {
            'V13': 'Versetzung (13. Kl.)'
    }



    def printGrade(self, g):
        """Fetch the grade for the given subject id and return the
        string representation required for the reports.
        """
        if g not in self.VALIDGRADES:
            raise ValueError
        try:
            int(g)
            return g
        except:
            if g:
                return "––––––"
            else:
                return "?"


    def gradeFilter(self, sid, g):
        # Separate out numeric grades
        try:
            gint = int(g)
            if gint < 0 or gint > 15:
                raise ValueError
        except ValueError:
            if g not in self.VALIDGRADES:
                REPORT.Error(_BADGRADE, sid=sid, grade=g)
                self[sid] = None
                return None
            self[sid] = g
            return -1
        # Integer grade ...
        # Sanitized original grade:
        self[sid] = str(gint).zfill(self.ZPAD)
        return gint


    def SekII(self, pdata, fhs = False):
        """Perform general "pass" tests on grades at end of class 12:
        not more than two times points < 5 or one subject with 0
        points, including compensation possibilities.
        If <fhs> is true, the second language is not included in the
        considerations.
        """
        try:
            abis = AbiSubjects(self.schoolyear, pdata['PID'], fhs)
        except ValueError as e:
            REPORT.Error("ABI_SUBJECTS: %s (%s)" % (e, pdata.name()))
            return False
        # Build lists of "fives" and "sixes".
        fives, zerop, ok = [], None, []
        for sid in abis:
            g = self.grades.get(sid)
            if g == None:
                REPORT.Error(_MISSING_ABI_GRADE, pname = pdata.name(),
                        sid = sid)
                self[sid] = None    # It might have been 'nt', '*', etc.
                return False
            if g == 0:
                if zerop:
                    return False
                zerop = sid
            elif g < 5:
                fives.append((sid, g))
            else:
                ok.append((sid, g))

        if zerop:
            if fives:
                return False
            for s, g in ok:
                if g >= 10 and (abis.demafs(s) or not abis.demafs(zerop)):
                    return True
            c = 0
            for s, g in ok:
                if g >= 8 and (abis.demafs(s) or not abis.demafs(zerop)):
                    if c > 0:
                        return True
                    c = 1
            return False

        if len(fives) < 2:
            return True
        if len(fives) > 2:
            return False
        used = None
        # Check demafs subjects first, as they are more difficult to compensate.
        sid, g = fives[0]
        if abis.demafs(sid):
            sid2, g2 = fives[1]
        else:
            sid2, g2 = sid, g
            sid, g = fives[1]
        for sx, gx in ok:
            if g + gx >= 10 and (abis.demafs(sx) or not abis.demafs(sid)):
                used = sx
                break
        else:
            return False
        for sx, gx in ok:
            if sx == used:
                continue
            if g2 + gx >= 10 and (abis.demafs(sx) or not abis.demafs(sid)):
                return True
        return False


    def X_V13(self, pdata):
        """For the "gymnasial" group, 12th class. Determine qualification
        for the 13th class.
        """
        v = 'HS'
        if pdata['CLASS'] >= '13':
            v = 'Erw'
        else:
            # Check for RS first to avoid multiple error messages from
            # <SekII> (missing subject).
            fhs = self.SekII(pdata, fhs = True)
            if fhs:
                # Check for "pass"
                if self.SekII(pdata):
                    v = 'Erw'
                else:
                    v = 'RS'
        self.XINFO['V13'] = v
        return v


    def reportFail(self, term, rtype, pdata):
        if term == '2':
            if rtype == 'Zeugnis':
                if self.XINFO['V13'] != 'Erw':
                    REPORT.Warn(_FAILV, pname = pdata.name())
        else:
            # This is a hack to ensure that 'Erw' and 'RS' are only
            # possible at the END of year 12!
            self.XINFO['V13'] = 'HS'
        return True



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
        critical = []
        ### First the 'E' points
        eN = []
        n1, n2 = 0, 0
        for i in range(1, 9):
            try:
                s = int(gmap["S%d" % i])
            except:
                critical.append(_NO_GRADE % gmap["F%d" % i])
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

        if critical:
            for e in critical:
                REPORT.Error(e)
            raise GradeError

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
            gmap["PASS"] = False
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
        gmap["PASS"] = True
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
