### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/gradefunctions.py

Last updated:  2020-09-02

Calculations needed for grade handling.


=+LICENCE=============================
Copyright 2020 Michael Towers

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

UNCHOSEN = '/'
_NO_GRADE = '*'

# OPTIONS field in CLASS_SUBJECTS table
STREAMS = ('Gym', 'RS', 'HS')
_ALL_STREAMS = '*'
_OPTIONAL_SUBJECT = '?'

# FLAGS field in CLASS_SUBJECTS table
_NULL_COMPOSITE = '/'
_NOT_GRADED = '-'

# Messages
_DUPLICATE_SID = "Fach {sid} kommt in Klasse-Fächer-Tabelle mehrmals vor"
_GRADE_MISSING = "Keine Note im Fach {sid}"
_GRADE_NOT_OPTIONAL = "Fach {sid} ist ein Pflichtfach – es muss benotet werden"
_BAD_GRADE = "Ungültige Note im Fach {sid}: {grade}"


_MULTIPLE_SUBJECT = "Fach {sid} mehrfach benotet"

_MISSING_DEM = "Keine Note in diesen Fächern: {sids}"
_MISSING_SID = "Keine Note im Fach {sid}"
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

_NOT_G = "{i}. Fach: {sid}. Dieses muss gA + schriftlich (Endung '.g') sein."
_NOT_E = "{i}. Fach: {sid}. Dieses muss eA (Endung '.e') sein."
_NOT_M = "{i}. Fach: {sid}. Dieses muss mündlich (Endung '.m') sein."
_SUBJECT_CHOICE = "Unerwarte Abifächer: {sids}"


from fractions import Fraction
#from collections import OrderedDict

from core.base import str2list
#from wz_core.db import DBT


class GradeError(Exception):
    pass

###

class Frac(Fraction):
    """A <Fraction> subclass with custom <truncate> and <round> methods.
    """
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



def Manager(gclass, gstream, term = None):
    if gclass >= '13':
        if term == 'A':
            return GradeManagerA
        return GradeManagerQ1
    if gclass >= '12' and gstream == 'Gym':
        return GradeManagerQ1
    return GradeManagerN



class _GradeManager(dict):
    """Analyse the grades to derive the additional information
    necessary for the evaluation of the results.
#?
    The grades in composite subjects can be calculated and made available
    as an <int>.
    """
    ZPAD = 1    # set to 2 to force leading zero (e.g. '6' -> '06')
#
    def __init__(self, klass, stream, grademap):
        """Sanitize the "grades" for the subjects in the given class.
        The grades are provided in the mapping <grademap>. The results are
        stored as instance items (<_GradeManager> instance [sid]).
        Also collect all numeric grades as instance attribute <grades>:
            {sid -> int}.
        However, grades for "component" subjects are collected separately
        as instance attribute <components>:
            {composite -> [int, ...]}.
        <grademap> is a mapping {sid -> grade}
        """
        super().__init__()

        # Preserve the original mapping:
        grademap = dict(grademap) if grademap else {}
        # Collect normal grades (not including "component" subjects):
        self.grades = {}    # numeric grades {sid -> int}
        # Collect lists of "component" subjects:
        #    {composite sid -> [component sid, ...]}.
        # Include a "special" composite for grades which "don't count".
        self.components = {_NULL_COMPOSITE: []}
        # ... and this for non-numerical grades:
        self.badcomponents = {_NULL_COMPOSITE: []}
        sid2optional = {}       # {sid -> optional(True/False)}
        subjects = {}           # [(graded sid, flags), ...]
        self.XINFO = {}         # additional (calculated) fields
        # Collect invalid grades:
        self.bad_grades = []

        subjecttable = Class_Subjects()
        for sdata in subjecttable.class_subjects(klass):
            sid = sdata['SID']
            # Check for duplicates:
            if sid in sid2optional:
                raise GradeError(_DUPLICATE_SID.format(sid = sid))
            flaglist = str2list(sdata['FLAGS'])
            if _NOT_GRADED in flaglist:
                # Subject not relevant for grades
                continue
            options = sdata['OPTIONS']
            if options:
                optlist = str2list(options)
                if _ALL_STREAMS in optlist or stream in optlist:
                    sid2optional[sid] = _OPTIONAL_SUBJECT in optlist
                    if sdata['TIDS']:
                        # graded subject
                        subjects.append(sid, flaglist)
                    else:
                        # composite subject
                        self.components[sid] = []
                        self.badcomponents[sid] = []
        # Run through <subjects> to sort out components and process grades
        for sid, flaglist in subjects:
            try:
                g = grademap.pop(sid)
            except KeyError:
                raise GradeError(_GRADE_MISSING.format(sid = sid))
            if g == UNCHOSEN:
                if not sid2optional[sid]:
                    raise GradeError(_GRADE_NOT_OPTIONAL.format(sid = sid))
                # This allows <grademap> to indicate that this subject
                # is not taken / not valid.
                self[sid] = UNCHOSEN
                continue
            gint = self.gradeFilter(sid, g) # this also sets <self[sid]>

            for csid in self.components:
                if csid in flaglist:
                    # <sid> is a component of composite <csid>.
                    if gint >= 0:
                        self.components[csid].append(gint)
                    else:
                        self.badcomponents[csid].append(g)
                    break
            else:
                # <sid> is not a component
                if gint >= 0:
                    self.grades[sid] = gint
        # Allow checking for "unused" grades
        self.unused_grades = grademap if grademap else None
        # Remove pseudo-composite
        del(self.components[_NULL_COMPOSITE])
        del(self.badcomponents[_NULL_COMPOSITE])
        # Check that non-optional composites have components
        for sid, glist in self.components.items():
            if not glist:
                if not self.badcomponents[sid] and not sid2optional[sid]:
                    raise GradeError(_GRADE_NOT_OPTIONAL.format(sid = sid))
#
    def addDerivedEntries(self):
        """Add entries to the grade mapping for those items/subjects
        which are determined by processing the other grades.
        <self.components> {sid -> [int, ... ]} is a mapping of "composite"
        subjects, whose grade is the average of its "components". There
        is also a similar mapping, <self.badcomponents> {sid -> [str, ...]},
        for component "grades" which are not numerical.
        """
        for sid, glist in self.components.items():
            if glist:
                asum = 0
                for g in glist:
                    asum += g
                g = Frac(asum, len(glist)).round()
                self[sid] = g.zfill(self.ZPAD)
                self.grades[sid] = int(g)
            else:
                self[sid] = _NO_GRADE



#???
#
    def SET(self, tagmap):
        """<tagmap> should be a mapping of lists containing
        (subject, grade) tuples: {subject-group -> [(s, g), ...]}.
        This is for the exclusive use of the <GET> method.
        """
        self._tagmap = tagmap
#
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
#
    def NOSHOW(self, g):
        """Indicate that no (further) subjects in the given group will
        be called for and, especially, that this is no error, any
        remaining subjects are to be silently ignored.
        Return the current contents.
        """
        glist = self._tagmap[g]
        self._tagmap[g] = []
        return glist

###

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
            UNCHOSEN: None,
            '': '?'
    }
    VALID_GRADES = (
                '1+', '1', '1-',
                '2+', '2', '2-',
                '3+', '3', '3-',
                '4+', '4', '4-',
                '5+', '5', '5-',
                '6',
                '*', 'nt', 't', 'nb', #'ne',
                UNCHOSEN
    )
#
    def printGrade(self, g):
        """Fetch the grade for the given subject id and return the
        string representation required for the reports.
        """
        return self._GRADES[g.rstrip('+-')]
#
    def gradeFilter(self, sid, g):
        """Sanitize the grade <g>, saving the result as <self[sid]>.
        Return the corresponding integer value – or -1 for non-numerical
        grades ('+' and '-' suffixes are ignored here).
        """
        if g not in self.VALID_GRADES:
            self.bad_grades.append((sid, g))
            self[sid] = ''
            return -1
        # Separate out numeric grades, ignoring '+' and '-'
        plusminus = g[-1]
        if plusminus in '+-':
            g = g[:-1]
        else:
            plusminus = ''
        try:
            gint = int(g)
        except ValueError:
            self[sid] = g
            return -1
        else:
            self[sid] = str(gint) + plusminus
        return gint
#
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
            asum += g
            acount += 1
        if acount:
            avg = Frac(asum, acount)
            self._AVE = avg
            self.XINFO['AVE'] = avg.truncate(2)
            return avg
        return None
#
    def X_DEM(self, pdata = None):
        """Return the grade average in the subjects De, En, Ma.
        Round to two decimal places, or return <None> if one or more
        grades are missing.
        """
        asum = 0
        for sid in self._DEM:
            try:
                asum += self.grades[sid]
            except:
                return None
        dem = Frac(asum, len(self._DEM))
        self.XINFO['DEM'] = dem.truncate(2)
        return dem
#
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
#
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
#
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
#
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
#
#TODO: Actually there should also be a Q11, which is basically the same
# as Q12 – including the final exams, but "Erw" is not possible
# ("Verordnung AVO-Sek_I, 2016, §47 Abs 2").
#
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
#
#?
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

###

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
#
    @classmethod
    def demafs(cls, sid):
        """Check whether the given subject is Deutsch, Mathe or
        a Fremdsprache.
        """
        s = sid.split('.', 1)[0]
        return s in ('De', 'Ma', 'En') or s in cls.FS2

###

class _GradeManagerQ(_GradeManager):
    """Revised base class for the "Qualifikationsphase".
    """
    ZPAD = 2    # all (numeric) grades have two digits (e.g. '1' -> '01')
    VALID_GRADES = (
                '15', '14', '13',
                '12', '11', '10',
                '09', '08', '07',
                '06', '05', '04',
                '03', '02', '01',
                '00',
                '*', 'nt', 't', 'nb', #'ne',
                UNCHOSEN
    )
#
    def printGrade(self, g):
        """Fetch the grade for the given subject id and return the
        string representation required for the reports.
        """
        if g not in self.VALID_GRADES:
            raise ValueError
        try:
            int(g)
            return g
        except:
            if g:
                return "––––––"
            else:
                return "?"
#
    def gradeFilter(self, sid, g):
        # Separate out numeric grades
        try:
            gint = int(g)
            if gint < 0 or gint > 15:
                raise ValueError
        except ValueError:
            if g not in self.VALID_GRADES:
                REPORT.Error(_BADGRADE, sid=sid, grade=g)
                self[sid] = None
                return None
            self[sid] = g
            return -1
        # Integer grade ...
        # Sanitized original grade:
        self[sid] = str(gint).zfill(self.ZPAD)
        return gint

###

class GradeManagerQ1(_GradeManagerQ):
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
#
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
#
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

###

class GradeManagerA(_GradeManagerQ):
    """This handles grades for the Abitur final results.
    Only the chosen Abitur subjects are included and the grades of the
    oral "Nachprüfungen" are added.
    """
#TODO
    def reportFail(self, term, rtype, pdata):
        REPORT.Warn("TODO: GradeManagerA.reportFail")
        return True
#
    def sidFilter(self, sid2tlist, pdata):
        """Iterate over the subject entries in <sid2tlist>, returning
        (sid, name) tuples for non-null entries.
        <pdata> allows for pupil-specific filtering, which is used here
        to keep only the chosen subjects and to add the results of the
        oral "Nachprüfungen".
        """
        if not pdata:
            REPORT.Bug("'sidFilter' invoked without pupil data")
        try:
            choices = AbiSubjects(self.schoolyear, pdata['PID'])
        except:
            REPORT.Fail(_ABI_CHOICES, pname = pdata.name())
        i = 0
        for sid in sid2tlist:
            try:
                choices.remove(sid)
            except ValueError:
                continue
            sname = sid2tlist[sid].subject
            i += 1
            if i < 4:
                # Check written subject, eA
                if not sid.endswith (".e"):
                    REPORT.Fail(_NOT_E, i = i, sid = sid)
                yield (sid, sname)
                yield ('N_' + sid, sname + ' – mdl. Nachprüfung')
            elif i == 4:
                # Check written subject, gA
                if not sid.endswith (".g"):
                    REPORT.Fail(_NOT_G, i = i, sid = sid)
                yield (sid, sname)
                yield ('N_' + sid, sname + ' – mdl. Nachprüfung')
            elif i <= 8:
                # Check oral subject
                if not sid.endswith (".m"):
                    REPORT.Fail(_NOT_M, i = i, sid = sid)
                yield (sid, sname)
            else:
                REPORT.Bug("It should not be possible to have too many subjects here")
        if choices:
            REPORT.Fail(_SUBJECT_CHOICE, sids = ', '.join(choices))

###

class AbiCalc:
    """Manage a mapping of all necessary grade components for an
    Abitur report.
    """
    _gradeText = {'0': 'null', '1': 'eins', '2': 'zwei', '3': 'drei',
            '4': 'vier', '5': 'fünf', '6': 'sechs', '7': 'sieben',
            '8': 'acht', '9': 'neun'
    }
#
    def __init__(self, sid2grade):
        """<sid2grade> must be a <GradeManagerA> instance. The subjects
        should thus be checked and ordered.
        """
        def getSG():
            for sid, grade in sid2grade.items():
                yield (sid, grade)

#        REPORT.Test("???name %s" % repr(sid2grade.sname))
#        REPORT.Test("???grade %s" % repr(sid2grade))
        self.zgrades = {}   # For report building
        self.sngg = []      # For grade entry/editing
        sg = getSG()
        for i in range(1, 9):
            sid, grade = sg.__next__()
            sname = sid2grade.sname[sid]
            self.zgrades["F%d" % i] = sname.split('|')[0].rstrip()
            grade = grade or '?'
            self.zgrades["S%d" % i] = grade
            if i <= 4:
                sn, gn = sg.__next__()
                gn = gn or '*'
                self.zgrades["M%d" % i] = '––––––' if gn == '*' else gn
            else:
                gn = None
            self.sngg.append((sid, sname, grade, gn))
#
    def getFullGrades(self):
        """Return the full tag mapping for an Abitur report.
        """
        gmap = self.zgrades.copy()
        errors = []
        critical = []
        ### First the 'E' points
        eN = []
        n1, n2 = 0, 0
        for i in range(8):
            try:
                s = int(self.sngg[i][2])
            except:
                critical.append(_NO_GRADE % self.sngg[i][1])
                s = 0
            if i < 4:
                # written exam
                f = 4 if i == 3 else 6  # gA / eA
                try:
                    e = s + int(self.sngg[i][3])
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
            gmap["E%d" % (i+1)] = str(e)
            eN.append(e)
            if e == 0:
                errors.append(_NULL_ERROR % self.sngg[i][1])

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
        if g1 == '0':
            g1 = '1'
            g2 = '0'
        else:
            g2 = str ((g180 % 180) // 18)
        gmap["Grade1"] = g1
        gmap["Grade2"] = g2
        gmap["GradeT"] = self._gradeText[g1] + ", " + self._gradeText[g2]
        gmap["PASS"] = True
        return gmap
#
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