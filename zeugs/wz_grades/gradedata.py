### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/gradedata.py

Last updated:  2020-04-06

Handle the data for grade reports.


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

# Messages
_MISSING_GRADE = "Keine Note für {pname} im Fach {sid}"
_UNUSED_GRADES = "Noten für {pname}, die nicht im Zeugnis erscheinen:\n  {grades}"
_INVALID_YEAR = "Ungültiges Schuljahr: '{val}'"
_INVALID_KLASS = "Ungültige Klasse: {klass}"
_UNKNOWN_PUPIL = "In Notentabelle: unbekannte Schüler-ID – {pid}"
_NOPUPILS = "Keine (gültigen) Schüler in Notentabelle"
_NEWGRADES = "Noten für {n} Schüler aktualisiert ({year}/{term}: {klass})"
_BAD_GRADE_DATA = "Fehlerhafte Notendaten für {pname}, TERM={term}"
_UNGROUPED_SID = ("Fach {sid} fehlt in den Fachgruppen (in GRADES.ORDERING)"
        " für Klasse {klass}")
_NO_TEMPLATE = "Keine Zeugnisvorlage für Klasse {ks}, Typ {rtype}"
_GROUP_CHANGE = "Die Noten für {pname} ({pk}) sind für Gruppe {gk}"
_WRONG_TERM = "Nicht aktuelles Halbjahr: '{term}'"
_BAD_LOCK_VALUE = "Ungültige Sperrung: {val} for {group}"
_BAD_IDATE_VALUE = "Ungültiges Ausstellungsdatum: {val} for {group}"
_BAD_GDATE_VALUE = "Ungültiges Datum der Notenkonferenz: {val} for {group}"
_UPDATE_LOCKED_GROUP = "Zeugnisgruppe {group} is gesperrt, keine Änderung möglich"
_NO_GRADES_FOR_PUPIL = "{pname} hat keine Noten => Sperrung nicht sinnvoll"
_PUPIL_ALREADY_LOCKED = "{pname} ist schon gesperrt"
_LOCK_NO_DATE = "Sperrung ohne Datum"
_LOCK_GROUP = "Klass {ks} wird gesperrt ..."
_GROUP_LOCKED = "Klass {ks} ist schon gesperrt"
_TOO_MANY_REPORTS = "{pname} hat zu viele Zeugnisse ..."


import os
from collections import OrderedDict, namedtuple

from wz_core.configuration import Paths, Dates
from wz_core.db import DB, UpdateError
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_core.template import getGradeTemplate, getTemplateTags, TemplateError
from wz_compat.gradefunctions import Manager
from wz_compat.grade_classes import gradeGroups
from wz_table.dbtable import readPSMatrix


_INVALID = '/'      # Table entry for cells marked "invalid"


def grades2db(gtable):
    """Enter the grades from the given table into the database.
    Only tables for the current year/term are accepted (check
        gtable.info['SCHOOLYEAR'] and gtable.info['TERM']).
    """
    # Check school-year and term
    try:
        y = gtable.info.get('SCHOOLYEAR', '–––')
        schoolyear = int(y)
    except ValueError:
        REPORT.Fail(_INVALID_YEAR, val = y)
    term = gtable.info.get('TERM')
    try:
        curterm = CurrentTerm(schoolyear, term)
    except CurrentTerm.NoTerm as e:
        REPORT.Fail(e)

    # Check klass
    klass = Klass(gtable.info.get('CLASS', '–––'))
    # Check validity
    pupils = Pupils(schoolyear)
    try:
        plist = pupils.classPupils(klass)
        if not plist:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, klass = klass)
    # Filter the relevant pids
    p2grades = {}
    p2stream = {}
    for pdata in plist:
        pid = pdata['PID']
        try:
            p2grades[pid] = gtable.pop(pid)
        except KeyError:
            # The table may include just a subset of the pupils
            continue
        p2stream[pid] = pdata['STREAM']
    # Anything left unhandled in <gtable>?
    for pid in gtable:
        REPORT.Error(_UNKNOWN_PUPIL, pid = pid)
    # Now enter to database
    if p2grades:
        db = DB(schoolyear)
        sid2tlist = CourseTables(schoolyear).classSubjects(klass, 'GRADE')
        for pid, grades in p2grades.items():
            ks = Klass.fromKandS(klass.klass, p2stream[pid])
            gradeManager = Manager(ks)(schoolyear, sid2tlist, grades)
            gstring = map2grades(gradeManager)
            db.updateOrAdd('GRADES',
                    {   'CLASS': ks.klass, 'STREAM': ks.stream,
                        'PID': pid, 'TERM': term,
                        'GRADES': gstring
                    },
                    TERM = term,
                    PID = pid
            )
        REPORT.Info(_NEWGRADES, n=len(p2grades),
                klass = klass, year = schoolyear, term = term)
    else:
        REPORT.Warn(_NOPUPILS)



def singleGrades2db(schoolyear, pdata, rtag, date, gdate, grades):
    """Add or update GRADES table entry for a single pupil and date.
    <pdata> is an extended <PupilData> instance. It needs the following
    additional attributes:
        <GKLASS>: A <Klass> instance to be used for the class and stream
        of the grade entry (mostly the same as the current values for
        the pupil, but there is a slight possibility that the pupil has
        changed group since the entry was created).
        <RTYPE>: The report type.
        <REMARKS>: The entry for the remarks field.
    <rtag> is the TERM key.
    <date> is for the DATE_D field.
    <gdate> is for the GDATE_D field.
    <grades> is a mapping {sid -> grade}.
    """
    db = DB(schoolyear)
    pid = pdata['PID']
    if rtag == 'X':
        # Make new tag
        xmax = 0
        for row in DB(schoolyear).select('GRADES', PID = pid):
            t = row['TERM']
            if t[0] == 'X':
                try:
                    x = int(t[1:])
                except:
#TODO: illegal tag, delete entry?
                    raise TODO
                if x > xmax:
                    xmax = x
        if xmax >= 99:
            REPORT.Fail(_TOO_MANY_REPORTS, pname = pdata.name())
        rtag = 'X%02d' % (xmax + 1)
    gstring = map2grades(grades)
    db.updateOrAdd('GRADES',
            {   'CLASS': pdata.GKLASS.klass,
                'STREAM': pdata.GKLASS.stream,
                'PID': pdata['PID'],
                'TERM': rtag,
                'REPORT_TYPE': pdata.RTYPE,
                'GRADES': gstring,
                'REMARKS': pdata.REMARKS,
                'DATE_D': date,
                'GDATE_D': gdate
            },
            TERM=rtag,
            PID=pid
    )



def updateGradeReport(schoolyear, pid, term, rtype):
    """Update grade database when building reports.
    <pid> (pupil-id) and <term> (term or extra date) are used to key the
    entry in the GRADES table.
    For term reports, update only the REPORT_TYPE field.
    This function is not used for "extra" reports.
    """
    db = DB(schoolyear)
    termn = int(term)   # check that term (not date) is given
    try:
        # Update term. This only works if there is already an entry.
        db.updateOrAdd ('GRADES',
                {'REPORT_TYPE': rtype},
                update_only=True,
                PID=pid, TERM=term
        )
    except UpdateError:
        REPORT.Bug("No entry in db, table GRADES for: PID={pid}, TERM={term}",
                pid=pid, term=term)



def db2grades(schoolyear, term, klass, rtype):
    """Fetch the grades for the given school-class/group, term,
    schoolyear and report type. This is intended to supply the grades
    for reports generated as a batch.
    All pupils in <klass> are included. Those without grades, or whose
    class/stream has changed or whose report type doesn't match will
    have <None> instead of the grade mapping.
    Return a list [(pid, pname, {subject -> grade}), ...]
    <klass> is a <Klass> instance, which can include a list of streams
    (including '_' for pupils without a stream). If there are streams,
    only grades for pupils in one of these streams will be included.
    """
    plist = []
    # Get the pupils from the pupils db and search for grades for these.
    pupils = Pupils(schoolyear)
    db = DB(schoolyear)
    for pdata in pupils.classPupils(klass):
        pid = pdata['PID']
        gdata = db.select1('GRADES', PID = pid, TERM = term)
        gmap = None
        if gdata:
            gstring = gdata['GRADES'] or None
            if gstring:
                # Check class/stream match
                pklass = pdata.getKlass(withStream = True)
                gklass = Klass.fromKandS(gdata['CLASS'], gdata['STREAM'])
                if (gklass.klass != pklass.klass
                        or gklass.stream != pklass.stream):
                    # Pupil has switched klass and/or stream.
                    REPORT.Warn(_GROUP_CHANGE, pname = pdata.name(),
                            pk = pklass, gk = gklass)
                    # This can only be handled via individual view.
                else:
                    # Check report type match
                    _rtype = gdata['REPORT_TYPE']
                    if (not _rtype) or _rtype == rtype:
                        try:
                            gmap = grades2map(gstring)
                        except ValueError:
                            REPORT.Fail(_BAD_GRADE_DATA,
                                    pname = pdata.name(),
                                    term = term)
                        # Add additional info from the GRADES table
                        gmap.REMARKS = gdata['REMARKS']
                        gmap.DATE_D = gdata['DATE_D']
                        gmap.GDATE_D = gdata['GDATE_D']
                        gmap.KLASS = gklass
        plist.append((pid, pdata.name(), gmap))
    return plist



def getGradeData(schoolyear, pid, term):
    """Return all the data from the database GRADES table for the
    given pupil and the given "term" as a mapping.
        <term>: Either a term (small integer) or, for "extra"
            reports, a tag (Xnn). It may also may also be any other
            permissible entry in the TERM field of the GRADES table.
    The string in field 'GRADES' is converted to a mapping. If there is
    grade data, its validity is checked. If there is no grade data, this
    field is <None>.
    """
    db = DB(schoolyear)
    gdata = db.select1('GRADES', PID = pid, TERM = term)
    if gdata:
        # Convert the grades to a <dict>
        gmap = dict(gdata)
        try:
            gmap['GRADES'] = grades2map(gdata['GRADES'])
        except ValueError:
            REPORT.Fail(_BAD_GRADE_DATA,
                    pname = Pupils.pid2name(schoolyear, pidpid),
                    term = term)
        return gmap
    return None



def grades2map(gstring):
    """Convert a grade string from the database to a mapping:
        {[ordered] sid -> grade}
    """
    try:
        grades = OrderedDict()
        for item in gstring.split(';'):
            k, v = item.split('=')
            grades[k.strip()] = v.strip()
        return grades
    except:
        if gstring:
            raise ValueError
        # There is an entry, but no data
        return None



def map2grades(gmap):
    """Convert a mapping {sid -> grade} to a grade string for the GRADES
    field in the GRADES table.
    """
    return ';'.join([g + '=' + (v or '') for g, v in gmap.items()])



class GradeReportData:
    """Manage data connected with a school-class, stream and report type.
    When referring to old report data, bear in mind that a pupil's stream,
    or even school-class, may have changed. The grade data includes the
    class and stream associated with the data.
    """
    def __init__(self, schoolyear, klass):
        """<klass> is a <Klass> object, which may include stream tags.
        In general – because of varying extra fields and different
        templates – <klass> should be a "grade-group" (see
        <grade_classes.gradeGroups>).
        """
        self.schoolyear = schoolyear
        self.klassdata = klass
        self._GradeManager = Manager(klass)
        ### Get subjects information, including ordering
        courses = CourseTables(schoolyear)
        self.sid2tlist = courses.classSubjects(klass, 'GRADE')
        ## Sort the subject tags into ordered groups
        # CONF.GRADES.ORDERING: {subject group -> [(ordered) sid, ...]}
        subject_ordering = CONF.GRADES.ORDERING
        # For finding missing subjects in the ordering lists:
        subjects = set(self.sid2tlist)
        # Build a mapping {subject group -> [(ordered) sid, ...]}
        self.sgroup2sids = {}
        for group in klass.match_map(subject_ordering.CLASSES).split():
            sidlist = []
            self.sgroup2sids[group] = sidlist
            for sid in subject_ordering[group]:
                # Include only sids relevant for the school-class.
                try:
                    subjects.remove(sid)
                    if self.sid2tlist[sid] != None:
                        sidlist.append(sid)
                except KeyError:
                    pass
        # Entries remaining in <subjects> are not covered in ORDERING.
        for sid in subjects:
            if self.sid2tlist[sid] != None:
                # Report all subjects without a null entry
                REPORT.Error(_UNGROUPED_SID, sid = sid, klass = klass)
        # Extra, non-grade, fields
        try:
            self.xfields = klass.match_map(subject_ordering.EXTRA).split()
        except:
            self.xfields = []


    def validGrades(self):
        return self._GradeManager.VALIDGRADES


    def XNAMES(self):
        return self._GradeManager.XNAMES


    def gradeManager(self, grades):
        return self._GradeManager(self.schoolyear, self.sid2tlist, grades)


    def getTagmap(self, grades, pdata, rtype):
        """Prepare tag mapping for substitution in the report template,
        for the pupil <pdata> (a <PupilData> instance).
        <grades> is a grade manager (<GradeManagerXXX> instance),
        providing a mapping {sid -> grade} and other relevant information.
        Grouped subjects expected by the template get two entries:
        one for the subject name and one for the grade. They are allocated
        according to the numbered slots defined for the predefined ordering
        (config: GRADES/ORDERING).
        <rtype> may be needed to determine the template.
        Return a mapping {template tag -> replacement text}.
        """
        grades.addDerivedEntries()
        tagmap = {}                     # for the result

        # Get template
        try:
            self.template = getGradeTemplate(rtype, self.klassdata)
        except TemplateError:
            REPORT.Fail(_NO_TEMPLATE, ks = self.klassdata, rtype = rtype)

        # Copy the grade mapping, because it will be modified to keep
        # track of unused grade entries:
        gmap = dict(grades)     # this accepts a variety of input types
        for group, sidlist in self.sgroup2sids.items():
            sglist = []
            tagmap[group] = sglist
            for sid in sidlist:
                if self.sid2tlist[sid] == None:
                    continue
                try:
                    g = gmap.pop(sid)
                    if not g:
                        raise ValueError
                except:
                    REPORT.Error(_MISSING_GRADE, pname=pdata.name(), sid=sid)
                    g = ''
                if g == _INVALID:
                    continue
                sname = self.sid2tlist[sid].subject.split('|')[0].rstrip()
                try:
                    g1 = grades.printGrade(g)
                except:
                    REPORT.Bug("Bad grade for {pname} in {sid}: {g}",
                            pname = pdata.name(), sid = sid, g = g)
                sglist.append((sname, g1))
        grades.SET(tagmap)

        # Report unused grade entries
        unused = ["%s: %s" % (sid, g) for sid, g in gmap.items()
                if g != _INVALID]
        if unused:
            REPORT.Error(_UNUSED_GRADES, pname = pdata.name(),
                    grades = "; ".join(unused))
        # Handle "extra" fields
        for x in self.xfields:
            if x[0] == '*':
                continue
            try:
                method = getattr(grades, 'X_' + x)
            except:
                REPORT.Bug("No xfield-handler for %s" % x)
            method(pdata)
        return tagmap



def getTermTypes(klass, term):
    """Get a list of acceptable report types for the given group
    (<Klass> instance) and term. If <term> is not a term, a list for
    "special" reports is returned.
    If there is no match, return <None>.
    """
    t = ('_' + term) if term in CONF.MISC.TERMS else '_X'
    tlist = klass.match_map(CONF.GRADES.TEMPLATE_INFO[t])
    return tlist.split() if tlist else None



GradeDates = namedtuple("GradeDates", ('DATE_D', 'LOCK', 'GDATE_D'))

class CurrentTerm():
    class NoTerm(Exception):
        pass

    def __init__(self, year = None, term = None):
        """Manage the information about the current year and term.
        If <year> and/or <term> are supplied, these will be checked
        against the actual values. If there is a mismatch, a <NoTerm>
        exception will be raised with an appropriate message.
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


    def next(self):
        """Return the next term, or <None> if the current one is the
        final term of the year.
        """
        n = str(int(self.TERM) + 1)
        if n in CONF.MISC.TERMS:
            return n
        return None


    def setTerm(self, term):
        """Set the current term for grade input and reports.
        Also set no groups open for grade input.
        """
        if term not in CONF.MISC.TERMS:
            REPORT.Bug("Invalid school term: %s" % term)
        if self.TERM:
            # Close current term
            dateInfo = self.dates()
            for ks, termDates in dateInfo.items():
                if termDates.LOCK == 0:
                    REPORT.Info(_GROUP_LOCKED, ks = ks)
                    continue
                REPORT.Info(_LOCK_GROUP, ks = ks)
                self.dates(Klass(ks), lock = 0)
        # Start new term
        db = DB()
        db.setInfo('GRADE_DATES', None)
        db.setInfo('TERM', term)
        self.TERM = term
        return term


    def dates(self, group = None, date = None, lock = None, gdate = None):
        """Manage group dates and locking for the current term.
        With no arguments, return a mapping of date/locking info:
            {(string) group -> <GradeDates> instance}
            with empty dates being ''
        Otherwise, <group> (a <Klass> instance) should be provided.
        One or more of the other arguments should then be provided,
        the value being written to the database.
        <lock>, should be 0, 1 or 2.
            0: Lock completely. The dates, etc., should be transferred
               to the individual GRADES entries.
            1: Grade input is only possible for administrators using
               the single-report interface.
            2: Open for grade input (for this there must be a grade
               conference date).
        The dates must be within the schoolyear.
        """
        db = DB()
        gmap = {}
        info = {}
        dstring = db.getInfo('GRADE_DATES')
        if dstring:
            for k2d in dstring.split():
                try:
                    k, d, l, g = k2d.split(':')
                    if l not in ('0', '1', '2'):
                        raise ValueError
                    if d and not Dates.checkschoolyear(self.schoolyear, d):
                        raise ValueError
                    if g and not Dates.checkschoolyear(self.schoolyear, g):
                        raise ValueError
                    info[k] = GradeDates(DATE_D = d, LOCK = int(l),
                            GDATE_D = g)
                except:
                    raise
                    REPORT.Bug("Bad GRADE_DATES entry in master DB: " + k2d)
        for ks in gradeGroups(self.TERM):
            k = str(ks)
            gmap[k] = info.get(k) or GradeDates(DATE_D = '', LOCK = 1,
                    GDATE_D = '')
        if not group:
            return gmap

        # Write value(s)
        k = str(group)
        try:
            data = gmap[k]
        except:
            REPORT.Fail(_BAD_DATE_GROUP, group = k)
        if data.LOCK == 0:
            REPORT.Fail(_UPDATE_LOCKED_GROUP, group = k)

        if date:
            if not Dates.checkschoolyear(self.schoolyear, date):
                REPORT.Fail(_BAD_IDATE_VALUE, group = group, val = date)
            if date != data.DATE_D:
                data = data._replace(DATE_D = date)

        if gdate:
            if not Dates.checkschoolyear(self.schoolyear, gdate):
                REPORT.Fail(_BAD_GDATE_VALUE, group = group, val = gdate)
            if gdate != data.GDATE_D:
                data = data._replace(GDATE_D = gdate)

        if lock != None:
            if lock not in (0, 1, 2):
                REPORT.Fail(_BAD_LOCK_VALUE, group = group, val = lock)
            if lock != data.LOCK:
                data = data._replace(LOCK = lock)

            if lock == 0:
                # Transfer all dates to GRADES table (lock) for all
                # pupils in this group, if they have grades and are
                # not already locked.
                date = data.DATE_D
                if not date:
                    REPORT.Fail(_LOCK_NO_DATE)
                gdate = data.GDATE_D
                try:
                    rtype = getTermTypes(group, self.TERM)[0]
                except:
                    rtype = ''
                dbY = DB(self.schoolyear)
                for pdata in Pupils(self.schoolyear).classPupils(group):
                    # Get existing GRADES entry
                    pid = pdata['PID']
                    gdata = getGradeData(self.schoolyear, pid, self.TERM)
                    if (not gdata) or (not gdata['GRADES']):
                        REPORT.Warn(_NO_GRADES_FOR_PUPIL, pname = pdata.name())
                        continue
                    if gdata['DATE_D']:
                        REPORT.Warn(_PUPIL_ALREADY_LOCKED, pname = pdata.name())
                        continue
                    # If no existing report type, use the default
                    # ... this can be empty.
                    _rtype = gdata['REPORT_TYPE'] or rtype or 'X'
                    dbY.updateOrAdd('GRADES',
                            {   'DATE_D': date,
                                'GDATE_D': gdate,
                                'REPORT_TYPE': _rtype
                            },
                            TERM = self.TERM,
                            PID = pid,
                            update_only = True
                    )
        gmap[k] = data
        # Rewrite master-DB entry
        slist = ['%s:%s:%d:%s' % (g, v.DATE_D, v.LOCK, v.GDATE_D)
                for g, v in gmap.items()]
        gd = '\n'.join(slist)
        db.setInfo('GRADE_DATES', gd)
        return True



##################### Test functions
_testyear = 2016
def test_01 ():
    _term = '2'
    _pid = '200403'
    REPORT.Test("Reading basic grade data for pupil %s" % _pid)
    pgrades = getGradeData(_testyear, _pid, _term)
    klass = Klass.fromKandS(pgrades['CLASS'], pgrades['STREAM'])

    gradedata = GradeReportData(_testyear, klass)
    REPORT.Test("\nGrade groups:\n  %s" % repr(gradedata.sgroup2sids))
    REPORT.Test("\nExtra fields: %s" % repr(gradedata.xfields))

    # Get the report type from the term and klass/stream
    _rtype = getTermTypes(klass, _term)[0]
    REPORT.Test("\nReading template data for class %s (type %s)" %
            (klass, _rtype))

    pupils = Pupils(_testyear)
    gm = gradedata.gradeManager(pgrades['GRADES'])
    tagmap = gradedata.getTagmap(gm, pupils.pupil(_pid), _rtype)
    REPORT.Test("  Grade tags:\n  %s" % repr(tagmap))
    REPORT.Test("\n  Grade data:\n  %s" % repr(gm))

def test_02():
    _term = '1'
    for klass in gradeGroups(_term):
        REPORT.Test("\n ++++ Class %s ++++" % klass)
        rtype = getTermTypes(klass, _term)[0]
        for pid, pname, gmap in db2grades(_testyear, _term, klass, rtype):
            REPORT.Test("GRADES for %s: %s" % (pname, repr(gmap)))

def test_03():
    from glob import glob
    # With term='1' this should fail.
    files = glob(Paths.getYearPath(_testyear, 'FILE_GRADE_TABLE',
                term='*'))
    for filepath in files:
        REPORT.Test("READ " + filepath)
        pgrades = readPSMatrix(filepath)
        try:
            grades2db(pgrades)
        except:
            pass
