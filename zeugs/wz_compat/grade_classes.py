# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/grade_classes.py

Last updated:  2020-03-22

For which school-classes and streams are grade reports possible?


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

# Messages
_WRONG_YEAR = "Nicht aktuelles Schuljahr: '{year}'"
_WRONG_TERM = "Nicht aktuelles Halbjahr: '{term}'"
_NO_TERM = "Kein aktuelles Halbjahr"
_INVALID_GROUP = "Ungültige Zeugnis-Gruppe für das {term}. Halbjahr: {group}"
_INVALID_YEAR = "Ungültiges Schuljahr: '{year}'"
_INVALID_KLASS = "Ungültige Klasse: '{klass}'"
_MISSING_PUPIL = "Schüler {pname} ist nicht in der Kurswahltabelle"
_UNKNOWN_PUPIL = "Unbekannter Schüler: {pid}"
_NEWCHOICES = "[{year}] Kurswahl für Klasse {klass} aktualisiert."
_NOPUPILS = "Keine Schüler"
_NSUBJECTS = "Für {pname} sind nicht genau 8 Fächer markiert"
_ABI_CHOICES = "{pname} muss genau 8 Fächer für das Abitur wählen"


from collections import OrderedDict

from wz_core.db import DB
from wz_core.configuration import Paths
from wz_core.pupils import Klass, Pupils
from wz_core.courses import CourseTables
from wz_table.dbtable import readPSMatrix
from wz_table.matrix import KlassMatrix


#TODO: Normalise! Return Klass?
def gradeGroups(term):
    """Return a list of "normalised" classes/groups for the given term.
    The groups are in string form.
    """
    try:
        groups = CONF.GRADES.TEMPLATE_INFO['GROUPS_' + term]
    except KeyError:
        REPORT.Bug("Invalid term in <gradeGroups>: %s" % term)
    return groups.csplit(None)


def gradeIssueDate(schoolyear, termn, klass, val = None):
    """Manage the date of issue for the grade reports for this year,
    term and class/group.
        val = None: return the date (not set => <None>),
        Otherwise: set the date to this value.
    """
    if val == None:
        return DB(schoolyear).getInfo('GRADE_ISSUE_DATE_%s:%s'
                % (termn, klass))
    else:
        DB(schoolyear).setInfo('GRADE_ISSUE_DATE_%s:%s'
                % (termn, klass), val)


def gradeDate(schoolyear, termn, klass, val = None):
    """Manage the date of the "Notenkonferenz" for the grade reports
    for this year, term and class/group.
        val = None: return the date (not set => <None>),
        Otherwise: set the date to this value.
    """
    if val == None:
        return DB(schoolyear).getInfo('KDATE_%s:%s'
                % (termn, klass))
    else:
        DB(schoolyear).setInfo('KDATE_%s:%s'
                % (termn, klass), val)



class CurrentTerm():
    class NoTerm(Exception):
        pass

    def __init__(self, year = None, term = None):
        """Manage the information about the current year and term.
        If <year> and/or <term> are supplied, the information will only
        be returned if these match the current year and term. If not,
        a <NoTerm> exception will be raised.
        """
        db = DB()
        self.schoolyear = db.schoolyear
        if year and year != self.schoolyear:
            raise self.NoTerm(_WRONG_YEAR.format(year = year))
        self.TERM = db.getInfo('TERM')
        if not self.TERM:
            self.setTerm('1')
        if term and term != self.TERM:
            raise self.NoTerm(_WRONG_TERM.format(term = term))


    def setTerm(self, term):
        """Set the current term for grade input and reports.
        Also set no groups open for grade input.
        """
        if term not in CONF.MISC.TERMS:
            REPORT.Bug("Invalid school term: %s" % term)
        db = DB()
        db.setInfo('TERM', term)
        self.TERM = term
        # No groups open for grade input
        db.setInfo('GRADE_OPEN', '')
        return term


    def openGroups(self):
        """Return the list of groups (a subset of the list returned by
        <gradeGroups()>) which are open for grade input.
        """
        try:
            return DB().getInfo('GRADE_OPEN').split()
        except:
            return None


    def isOpen(self, klass):
        """<klass> is a <Klass> instance. It can be either for a group
        in the list returned by <gradeGroups()> or for a single stream.
        Return <True> if <klass> is open for grade input, else <False>.
        """
        ogroups = self.openGroups()
        if not ogroups:
            return False
        if str(klass) in ogroups:
            return True
        if not klass.stream:
            return False
        for g in ogroups:
            k = Klass(g)
            if klass.klass != k.klass:
                continue
            if k.containsStream(klass.stream):
                return True



def abi_sids(schoolyear, pid, report = True):
    row = DB(schoolyear).select1('ABI_SUBJECTS', PID = pid)
    try:
        choices = row['SUBJECTS'].split(',')
        if len(choices) == 8:
            return choices
    except:
        pass
    if report:
        REPORT.Fail(_ABI_CHOICES, pname = Pupils.pid2name(schoolyear, pid))
    return None



def choiceTable(schoolyear, klass):
    """Build a subject choice table for the given school-class.
    <klass> is a the class name.
    Unless the school-class has changed, existing choices will be retained.
     """
    ks = Klass(klass)
    pupils = Pupils(schoolyear)
    try:
        if klass.startswith('12') or klass.startswith('13'):
            plist = pupils.classPupils(ks)
            if not plist:
                raise ValueError
        else:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, klass=klass)
    template = Paths.getUserPath('FILE_SUBJECT_CHOICE_TEMPLATE')
    table = KlassMatrix(template)
    # Title already set in template:
    #table.setTitle("Kurswahl")

    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass),
    )
    table.setInfo(info)

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(ks, filter_ = 'GRADE')
    # <table.headers> is a list of cell values in the header row.
    rsid = table.rowindex - 1       # row index for sid
    rsname = table.rowindex         # row index for subject name
    # Go through the template columns and check if they are needed:
    sid2col = {}        # map sid -> column index
    for sid in sid2tlist:
        try:
            s, tag = sid.rsplit('_', 1)
            if s:
                # Don't include "components" of "composite" subjects
                continue
        except ValueError:
            pass
        sname = courses.subjectName(sid)
        # Add subject
        col = table.nextcol()
        table.write(rsid, col, sid)
        sid2col[sid] = col
        table.write(rsname, col, sname)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    # Go through all pids (with stream 'Gym')
    p2choices = {}
    for pdata in plist:
        if pdata['STREAM'] != 'Gym':
            continue
        pid = pdata['PID']
        pname = pdata.name()
        choices = abi_sids(schoolyear, pid, report = False)
        row = table.nextrow()
        table.write(row, 0, pid)
        table.write(row, 1, pname)
        table.write(row, 2, pdata['STREAM'])
        for sid, col in sid2col.items():
            try:
                if sid in choices:
                    table.write(row, col, 'X')
            except:
                pass
    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()



def choices2db(schoolyear, filepath):
    """Enter the choices from the given table into the database.
    <schoolyear> is checked against the value in the info part of the
    table (table.info['SCHOOLYEAR']).
    """
    table = readPSMatrix(filepath)
    # Check school-year
    try:
        y = table.info.get('SCHOOLYEAR', '–––')
        yn = int(y)
    except ValueError:
        REPORT.Fail(_INVALID_YEAR, val=y)
    if yn != schoolyear:
        REPORT.Fail(_WRONG_YEAR, year=y)
    # Check klass
    klass = Klass(table.info.get('CLASS', '–––'))
    # Check validity
    pupils = Pupils(schoolyear)
    try:
        if klass.klass.startswith('12') or klass.klass.startswith('13'):
            plist = pupils.classPupils(klass)
            if not plist:
                raise ValueError
        else:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, klass=klass)
    # Go through all pids (with stream 'Gym')
    p2choices = {}
    for pdata in plist:
        if pdata['STREAM'] != 'Gym':
            continue
        pid = pdata['PID']
        try:
            p2choices[pid] = table.pop(pid)
        except KeyError:
            # This pupil is not in the choice table
            REPORT.Fail(_MISSING_PUPIL, pname=pdata.name())
    # Anything left unhandled in <table>?
    for pid in table:
        REPORT.Error(_UNKNOWN_PUPIL, pid=pid)

    # Now enter to database.
    # To recognize new subjects in the subject matrix, also non-chosen
    # subjects must be included.
    if p2choices:
        allsids = table.sids
        db = DB(schoolyear)
        for pid, smap in p2choices.items():
            slist = [sid for sid in table.sids if smap.get(sid)]
            if len(slist) != 8:
                REPORT.Fail(_NSUBJECTS, pname = plist.pidmap[pid].name())
            cstring = ','.join(slist)
            db.updateOrAdd('ABI_SUBJECTS',
                    {   'PID': pid,
                        'SUBJECTS': cstring
                    },
                    PID=pid
            )
        REPORT.Info(_NEWCHOICES, klass=klass, year=schoolyear)
    else:
        REPORT.Warn(_NOPUPILS)



##################### Test functions
_testyear = 2016

def test_01():
    for key in ('1', '2', 'X'):
        REPORT.Test("\n Term %s (reports): %s" % (key, repr(gradeGroups(key))))
        REPORT.Test("\n Term %s (tables): %s" % (key, repr(gradeGroups(key, False))))

def test_02():
    for _klass in ('13', '12'):
        filepath0 = Paths.getYearPath(_testyear, 'FILE_SUBJECT_CHOICE_TABLE')
        filepath = filepath0.replace('*', _klass)
        choices2db(_testyear, filepath)

def test_03():
    for _klass in ('13', '12'):
        bytefile = choiceTable(_testyear, _klass)
        filepath = Paths.getYearPath(_testyear, 'FILE_SUBJECT_CHOICE_NEW',
                make=-1).replace('*', _klass) + '.xlsx'
        with open(filepath, 'wb') as fh:
            fh.write(bytefile)
        REPORT.Test(" --> %s" % filepath)
