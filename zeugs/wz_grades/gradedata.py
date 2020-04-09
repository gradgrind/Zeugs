### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/gradedata.py

Last updated:  2020-04-08

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
_INVALID_USER = "Benutzer {user} hat keinen Zugriff auf die Noten"
_MISSING_GRADE = "Keine Note für {pname} im Fach {sid}"
_UNUSED_GRADES = "Noten für {pname}, die nicht im Zeugnis erscheinen:\n  {grades}"
_INVALID_YEAR = "Ungültiges Schuljahr: '{val}'"
_INVALID_KLASS = "Ungültige Klasse: {klass}"
_UNKNOWN_PUPIL = "In Notentabelle: unbekannte Schüler-ID – {pid}"
_NOPUPILS = "Keine (gültigen) Schüler in Notentabelle"
_NEWGRADES = "Noten für {n} Schüler aktualisiert ({year}/{term}: {klass})"
#_BAD_GRADE_DATA = "Fehlerhafte Notendaten für {pname}, TERM={term}"
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
_LAST_USER = ("Note im Fach {sid} für {pname} zuletzt durch Benutzer {user0}"
        " geändert, Zugang verweigert")
_INVALID_STREAM = ("{pname}: Gruppe {pstream} stimmt nicht mit Tabelle"
        " {tstream} überein")


import os, datetime
from collections import OrderedDict, namedtuple

from wz_core.configuration import Paths, Dates
from wz_core.db import DBT, UpdateError
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_core.teachers import Users
from wz_core.template import getGradeTemplate, getTemplateTags, TemplateError
from wz_compat.gradefunctions import Manager
from wz_compat.grade_classes import gradeGroups
from wz_table.dbtable import readPSMatrix


_INVALID = '/'      # Table entry for cells marked "invalid"


#TODO: 1) user handling, 2) rebase on DBT


def gradeInfo(schoolyear, term, pid):
    """Return the GRADES table entry for the given year/pupil/term, if
    it exists, otherwise <None>.
    """
    with DBT(schoolyear) as tdb:
        ginfo = tdb.select1('GRADES', PID = pid, TERM = term)
    if ginfo:
        # Convert the grade info to a <dict>
        return dict(ginfo)
    else:
        return None


def getGradeData(schoolyear, pid, term, sid = None):
    """Return all the data from the database GRADES table for the
    given pupil and the given "term" as a mapping.
        <term>: Either a term (small integer) or, for "extra"
            reports, a tag (Xnn). It may also may also be any other
            permissible entry in the TERM field of the GRADES table.
    Return a mapping containing the basic grade-info for this year/term/
    pupil.
    If no <sid> is given, there will also be a 'GRADES' item, which is
    a mapping {sid -> grade} for all subjects appropriate to the class.
    Note that class and stream of the grade info entry are used, which
    may differ from those of the pupil (if the pupil has changed
    class/group).
    If <sid> is supplied, there will be a 'GRADE' item, which is just
    the grade of the given subject.
    """
    gmap = gradeInfo(schoolyear, pid, term)
    if not gmap:
        return None

    db = DBT(schoolyear)
    gkey = gmap['KEYTAG']
    if sid:
        gmap['GRADE'] = _readGradeSid(db, gkey, sid)
        return gmap
    # Read all subjects
    klass = Klass.fromKandS(gmap['CLASS'], gmap['STREAM'])
    sid2tlist = CourseTables(schoolyear).classSubjects(klass, 'GRADE')
    gmap['GRADES'] = {sid: _readGradeSid(db, gkey, sid)
            for sid in sid2tlist}
    return gmap


def _readGradeSid(db, gkey, sid, withuser = False):
    """If there are entries for this key and sid, return the latest.
    If no entries, return <None>.
    If <withuser> is true, return a tuple (grade, user), otherwise
    just return the grade.
    """
    with db:
        # This might be faster with "fetchone" instead of "LIMIT",
        # because of the "DESC" order.
        records = db.select('GRADE_LOG',
                order = 'TIMESTAMP', reverse = True, limit = 1,
                KEYTAG = gkey, SID = sid)
    try:
        row = records[0]
        return (row['GRADE'], row['USER']) if withuser else row['GRADE']
    except:
        return None


# What about changed class/group? For the current term, I would probably
# want pupils currently in the group. If there is a class/group mismatch
# with the grades, certainly warn. Keep the grades IF they are valid?
# For non-current terms I would rather want to act according to the
# class/group stored with the grades. So search GRADES for class/group
# and only include pupils with entries (as it is old data, these should
# be complete).


def updateGrades(schoolyear, pdata, term, grades, user = None):
    """Update (only) the grades for year/pupil/term which have changed
    in the mapping <grades>: {sid -> grade}.
    <pdata> is a <PupilData> instance, supplying class and stream for
    new GRADES entries.
    This updating is achieved by adding a new record to the GRADE_LOG
    table.
    Only administrators can "overwrite" grades entered by someone else.
    If no <user> is supplied, the null user is used, which acts like an
    administrator.
    """
    # Because of potential (though unlikely) race conditions,
    # there needs to be a single EXCLUSIVE transaction for adding a
    # record if the grade has changed.
#TODO: What if there is a clash between pupil data and GRADES data?
# Perhaps this function assumes that the info in GRADES is correct,
# modifying that being the task of another function?
    ## First fetch (creating if necessary) the entry in the GRADES table.
    # Only the KEYTAG field is needed (-> <gkey>).
    tdb = DBT(schoolyear, exclusive = True)
    with tdb:
        ginfo = tdb.select1('GRADES', PID = pid, TERM = term)
        if ginfo:
            # Convert the grade info to a <dict>
            gmap = dict(ginfo)
            gkey = gmap['KEYTAG']
#TODO: Check class and stream?
# If current term, update entry? Else error?
# OR assume that has been handled previously, just update if necessary?
        else:
            gmap = None
            ### Create entry
# If creating a new GRADES entry, the pupil data must be used.
# But is this the right place for this? Should it rather raise an error?
# It should possibly only work in the current term, but I suppose that
# could be handled externally? In a closed term, there is no sure way
# of knowing the correct class and stream.
            gkey = tdb.addEntry('GRADES', {
                    'PID': pdata['PID'],
                    'TERM': term,
                    'CLASS': pdata['CLASS'],
                    'STREAM': pdata['STREAM']}
            )

    ## Read existing grades of all subjects in <grades> and update if
    ## they have changed and the user is permitted.
    perms = Users().permission(user)
    if 's' in perms:
        utest = False
    elif 'u' in perms:
        utest = True
    else:
        REPORT.Fail(_INVALID_USER, user = user)
    timestamp = datetime.datetime.now().isoformat(
            sep=' ', timespec='seconds')
    for sid, g in grades.items():
        # Null grades are ignored
        if not g:
            continue
        with tdb:
            if gmap:
                # Check that it is really a permissible change
                records = db.select('GRADE_LOG', order = 'TIMESTAMP',
                        reverse = True, limit = 1,
                        KEYTAG = gkey, sid = sid)
                if records:
                    row = records[0]
                    if g == row['GRADE']:
                        # Grade unchanged
                        continue
                    u0 = row['USER']
                    if utest and (user != u0):
                        # User permissions inadequate
                        REPORT.Error(_LAST_USER, user0 = u0, sid = sid,
                                pname = pdata.name())
                        continue
            # Add a new grade entry
            tdb.addEntry('GRADE_LOG', {
                    'KEYTAG': gkey,
                    'SID': sid,
                    'GRADE': g,
                    'USER': user,
                    'TIMESTAMP': timestamp
                }
            )



def grades2db(gtable):
    """Enter the grades from the given table into the database.
    Only tables for the current year/term are accepted (check
    gtable.info['SCHOOLYEAR'] and gtable.info['TERM']).
    This update doesn't pay attention to user permissions – it is
    performed as the "null" user, who may update any grade.
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
    pdata_grades = []
    for pdata in plist:
        pid = pdata['PID']
        try:
            pgrades = gtable.pop(pid)
        except KeyError:
            # The table may include just a subset of the pupils
            continue
        # Check stream against entry in table
        pstream = pdata['STREAM']
        if pgrades.stream != pstream:
            REPORT.Fail(_INVALID_STREAM, pname = pdata.name(),
                    pstream = pstream, tstream = pgrades.stream)
        pdata_grades.append((pdata, pgrades))
    # Anything left unhandled in <gtable>?
    for pid in gtable:
        REPORT.Error(_UNKNOWN_PUPIL, pid = pid)

    # Now enter to database
    if pdata_grades:
        sid2tlist = CourseTables(schoolyear).classSubjects(klass, 'GRADE')
        for pdata, grades in pdata_grades:
            ks = pdata.getKlass(withStream = True)
            # The grade manager "sanitizes" the grades and ensures that
            # there are entries for all subject (a grade can be null).
            gradeManager = Manager(ks)(schoolyear, sid2tlist, grades)
            # Enter the grades
            updateGrades(schoolyear, pdata, term, grades)
            REPORT.Info(_NEWGRADES, n=len(pdata_grades),
                    klass = klass, year = schoolyear, term = term)
    else:
        REPORT.Warn(_NOPUPILS)



#TODO: new db scheme
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
    raise TODO
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



def getPupilList(schoolyear, term, klass, rtype):
    """Return a list: [(pid, pname, ok), ...] for the group <klass>.
    All pupils in <klass> are included. Those without grades, or whose
    class/stream has changed or whose report type doesn't match will
    have <ok = False>, otherwise <ok = True>.
    <klass> is a <Klass> instance, which can include a list of streams
    (including '_' for pupils without a stream).
    """
    plist = []
    # Get the pupils from the pupils db and search for grades for these.
    pupils = Pupils(schoolyear)
    db = DBT(schoolyear)
    for pdata in pupils.classPupils(klass):
        pid = pdata['PID']
        gdata = db.select1('GRADES', PID = pid, TERM = term)
        ok = False
        if gdata:
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
                    ok = True
        plist.append((pid, pdata.name(), ok))
    return plist



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
        db = DBT()
        self.schoolyear = db.schoolyear
        if year and year != self.schoolyear:
            raise self.NoTerm(_WRONG_YEAR.format(year = year))
        with db:
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
        with DBT() as db:
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
        db = DBT()
        gmap = {}
        info = {}
        with db:
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
                dbY = DBT(self.schoolyear)
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
                    with dbY:
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
        with db:
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
