### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/gradedata.py

Last updated:  2020-04-13

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
_BAD_GRADE = "Fehlerhafte Note für {pname} in {sid}: {grade}"
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
_CHANGE_FROM = "{pname} hat die Gruppe gewechselt (von {ks})"


import os, datetime
from collections import OrderedDict, namedtuple

from wz_core.configuration import Paths, Dates
from wz_core.db import DBT, GRADES_INFO_FIELDS
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_core.teachers import Users
from wz_core.template import getGradeTemplate, getTemplateTags, TemplateError
from wz_compat.gradefunctions import Manager
from wz_compat.grade_classes import gradeGroups
from wz_table.dbtable import readPSMatrix


_INVALID = '/'      # Table entry for cells marked "invalid"


""" OVERVIEW

Grade information can be fetched using <getGradeData>. It returns all
information about either a single subject or all subjects for a pupil
and term. It should be constrained to return only valid grades. The
all-subjects mode encapsulates its grades in a "grade manager" (see
module "gradefunctions").

It is possible that there is a conflict between the grade/stream of a
pupil and that of the grade information in the database. This can happen
if the pupil has changed class/stream. How to deal with this depends on
whether we are handling the "current term" or not. If we are, there
should be a warning, but the grades will be passed on if they are valid
in the new scheme (otherwise null).
If we are not handling the "current term", the grades can only be
edited by an administrator anyway, so there is only the single-report
access. Here the pupil effectively takes on the class/stream of the
grade entry, which can, however, be changed.

***********************

Updating grade information has two parts. Firstly there is the general
data: class/group, term, report type and stuff for the report (remarks
and dates). This is common to all subjects for a pupil and term. It is
stored in the GRADES_INFO table.

The actual grades are stored in another table, GRADES_LOG.
These are indexed by a combination of KEYTAG and SID (subject id).
KEYTAG is the primary key of the GRADES_INFO table.

Grade information is needed on a per pupil basis for individual report
editing and building.

Grade information is also needed on a subject basis for teacher-subject
based editing. This is available via the single-subject interface to
<GradeData>, though of course one would need to iterate through the
pupils.

It may not really be necessary in this case, but it is probably a bit
"cleaner" if updating is done within a locked read/write transaction.

One update function (admin only) thus needs to accept a set of grades
for a pupil and term, including the possibility of a change of class/
stream to that of the new data. The possibly new class/stream could be
passed in with the pupil data (it needn't necessarily be the actual
class/stream of the pupil) or separately (***TODO***).

For the "current term" a change of class/stream is only possible in the
pupil-data editor. If there is a GRADES_INFO entry, this must also be
updated and a log-entry made so that the change can be communicated to
the users.

"Current term" only: Reading a GRADES_INFO entry with a class/stream
conflict with the pupil data should be an error – report it (bug?) and
correct it.

The second update function (available to all users) would handle grades
for a particular group of pupils, for a subject in the "current term"
only. Warning of a change of class/stream for a pupil should be logged
in the database, so that it can be signalled to the users – of course
only if there were any grade entries before the change.

The GRADE field of the GRADES_LOG table is not simply a grade. It
includes the change log. Each change of grade adds a line to this
string. Each line is formatted thus:
    grade,user,timestamp
The lines are separated by '\n'.

A "normal" user may only update a grade if there is no entry at present
or if (s)he was the last person to modify it. In the editor it might
help to make non-editable grades visible, but read-only, and to show
the "owner".
"""


#DEPRECATED: remove from abitur.py, used getGradeData instead.
def gradeInfo(schoolyear, term, pid):
    """Return the GRADES table entry for the given year/pupil/term, if
    it exists, otherwise <None>.
    """
    raise DEPRECATED
    with DBT(schoolyear) as tdb:
        ginfo = tdb.select1('GRADES', PID = pid, TERM = term)
    if ginfo:
        # Convert the grade info to a <dict>
        return dict(ginfo)
    else:
        return None


#TODO: Maybe the GRADES_INFO entries should be made when the "term" is
# opened?
class GradeData:
    """Manager for grade data for a particular term and pupil.
    """
    def __init__(self, schoolyear, term, pdata):
        """Get all the data from the database GRADES_INFO table for the
        given pupil and the given "term".
            <term>: Either a term (small integer) or, for "extra"
                reports, a tag (Xnn). It may also may also be any other
                permissible entry in the TERM field of the GRADES_INFO
                table.
            <pdata>: A <PupilData> instance.
        The data is stored as attributes:
            ginfo: the fields of the GRADES_INFO entry
            gklass: a <Klass> instance for the GRADES_INFO entry – if
                the class/stream is updated this will reflect the change
                (ginfo won't)
        """
        self.schoolyear = schoolyear
#TODO: The exclusive parameter is for the case that things are updated.
# If the GRADE_INFO updating is removed, that would remove one reason.
# Then it would only be a question of whether grade updates are covered
# by this class (and why shouldn't they be?)
        self.db = DBT(schoolyear, exclusive = True)
        self.term = term
        self.pdata = pdata
        # Ideally the class/stream in the GRADE_INFO entry will be the
        # same as that of the pupil, but if the pupil's class or stream
        # has changed, there could be a difference. In the "current term"
        # (only) the grade class/stream must then be adapted. Otherwise
        # the difference is tolerable, the GRADE_INFO values will be used.
        self.gklass = pdata.getKlass(withStream = True) # but see below
        self._GradeManager = None
        with self.db:
            self.ginfo = self.db.select1('GRADES_INFO', TERM = term,
                    PID = pdata['PID'])
            try:
                self.KEYTAG = self.ginfo['KEYTAG']
            except:
                self.KEYTAG = None
            else:
                _gklass = Klass.fromKandS(self.ginfo['CLASS'],
                        self.ginfo['STREAM'])
                if (_gklass.klass != self.gklass.klass
                        or _gklass.stream != self.gklass.stream):
                    try:
                        CurrentTerm(schoolyear, term)
                    except CurrentTerm.NoTerm as e:
                        # If not "current term" the difference is
                        # not an error, but use <_gklass>.
                        self.gklass = _gklass
                    else:
                        # Update the class/stream for the grade-info
                        self._updateGradeInfo(CLASS = self.gklass.klass,
                                STREAM = self.gklass.stream)
                        # Prepend the old class/stream to each existing
                        # grade entry, e.g. "#10.RS:"
                        for row in self.db.select('GRADES_LOG',
                                KEYTAG = self.KEYTAG):
                            pk = row['ID']
                            g = row['GRADE']
                            self.db.updateOrAdd('GRADES_LOG',
                                    {'GRADE': '#%s:' % self.gklass},
                                    update_only = True, ID = pk
                            )
#TODO: Shouldn't this rather be an error? even a bug?
# Only an administrator should be able to update a GRADES_INFO entry.
# Also report that it has been "fixed"/"angepasst"
                        REPORT.Warn(_GROUP_CHANGE, pname = pdata.name(),
                                pk = self.gklass, gk = _gklass)
                        # Note that the old values are still available
                        # in <self.ginfo>.


# ?
    def _updateGradeInfo(self, **changes):
        # The transaction is active!
        self.db.updateOrAdd('GRADES_INFO', changes, update_only = True,
                KEYTAG = self.KEYTAG)


# ?
    def addGradeInfo(self):
#?
        # The transaction is active!
        self.KEYTAG = self.db.addEntry('GRADES_INFO', {
                'TERM': self.term,
                'PID': self.pdata['PID'],
                'CLASS': self.gklass.klass,
                'STREAM': self.gklass.stream,
            }
        )


    def getGrade(self, sid):
        """Return a tuple: (grade, user) for the given subject.
        If there is no entry for the subject, return <None>.
        """
        if self.KEYTAG:
            with self.db:
                record = self.db.select1('GRADES_LOG',
                        KEYTAG = self.KEYTAG, SID = sid)
            try:
                g, user, rest = record['GRADE'].split(',', 2)
            except:
                pass
            else:
                self.user = user
                # Check for class/group-change prefix
                while g[0] == '#':
                    pre, g = g.split(':', 1)
                    REPORT.Warn(_CHANGE_FROM, pname = self.pdata.name(),
                            ks = pre[1:])
                # Validate grade
                if not self._GradeManager:
                    self._GradeManager = Manager(self.gklass)
                if g in self._GradeManager.VALIDGRADES:
                    return g
                REPORT.Warn(_BAD_GRADE, pname = self.pdata.name(),
                        sid = sid, grade = g)
                return None

        self.user = None
        return None


    def getAllGrades(self):
        self.users = {}
        with self.db:
            records = self.db.select('GRADES_LOG', KEYTAG = self.KEYTAG)
        grades, self.users = {}, {}
        for record in records:
            sid = record['SID']
            g, user, rest = record['GRADE'].split(',', 2)
            self.users[sid] = user
            # Check for class/group-change prefix
            while g[0] == '#':
                pre, g = g.split(':', 1)
                REPORT.Warn(_CHANGE_FROM, pname = self.pdata.name(),
                        ks = pre[1:])
            grades[sid] = g
        # Read all subjects for the class/group
        courses = CourseTables(self.schoolyear)
        sid2tlist = courses.classSubjects(self.gklass, 'GRADE')
        # Use a Grade Manager to validate and complete the grades
        if not self._GradeManager:
            self._GradeManager = Manager(self.gklass)
        self.grades = self._GradeManager(self.schoolyear, sid2tlist, grades)
        return self.grades


    def updateGrades(self, grades, user = None):
        """Read existing grades of all subjects in <grades> and update
        if they have changed and the user has permission.
            <grades> is a mapping: {sid -> grade}
        Only administrators can "overwrite" grades entered by someone
        else. If no <user> is supplied, the null user is used, which
        acts like an administrator.
        """
        # First set up <utest>, which is true if the user must be
        # checked when entering a new grade.
        if user:
            perms = Users().permission(user)
            if 's' in perms:
                utest = False
            elif 'u' in perms:
                utest = True
            else:
                REPORT.Fail(_INVALID_USER, user = user)
        else:
            utest = False
            user = 'X'
        timestamp = datetime.datetime.now().isoformat(
                sep=' ', timespec='seconds')
        # Keep separate lists for completely new entries and for those
        # which must be updated.
        new_entries, update_entries = [], []
        with self.db:
            for sid, g in grades.items():
                g0 = None # Existing grade string (default)
                if not g:
                    # Null grades are ignored
                    continue
                if self.KEYTAG:
                    # Get previous entry, if any
                    record = self.db.select1('GRADES_LOG',
                            KEYTAG = self.KEYTAG, SID = sid)
                    try:
                        g0, user0, rest = record['GRADE'].split(',', 2)
                    except:
                        pass
                    else:
                        # Check for class/group-change prefix
                        if g0[0] == '#':
                            # Do an update anyway
                            pass
                        elif g == g0:
                            continue
                        # Check that it is really a permissible change
                        if utest and (user != user0):
                            # User permissions inadequate
                            REPORT.Error(_LAST_USER, user0 = user0,
                                    sid = sid, pname = pdata.name())
                            continue
                # Add a new grade entry
                g1 = ','.join((g, user, timestamp))
                if g0:
                    update_entries.append((sid, g1 + '\n' + g0))
                else:
                    new_entries.append((self.KEYTAG, sid, g1))

            if new_entries:
                if not self.KEYTAG:
                    self.addGradeInfo()
                self.db.addRows('GRADES_LOG', ('KEYTAG', 'SID', 'GRADE'),
                        new_entries)

            if update_entries:
                if not self.KEYTAG:
                    self.addGradeInfo()
                for sid, grade in update_entries:
                    self.db.updateOrAdd('GRADES_LOG', {'GRADE': grade},
                        update_only = True,
                        KEYTAG = self.KEYTAG, SID = sid)


#TODO: update to new GRADE_LOG structure
def _updateGrades(schoolyear, term, pdata, grades, user = None):
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
    raise TODO

    gradeData = GradeData(schoolyear, term, pdata)
    # Because of potential (though unlikely) race conditions,
    # there needs to be a single EXCLUSIVE transaction for adding a
    # record if the grade has changed.
#TODO: What if there is a clash between pupil data and GRADES data?
# Perhaps this function assumes that the info in GRADES is correct,
# modifying that being the task of another function?
    ## First fetch (creating if necessary) the entry in the GRADES table.
    # Only the KEYTAG field is needed (-> <gkey>).
    db = DBT(schoolyear, exclusive = True)
    with db:
        ginfo = db.select1('GRADES_INFO', PID = pdata['PID'], TERM = term)
        if ginfo:
            gkey = ginfo['KEYTAG']
#TODO: Check class and stream?
# If current term, update entry? Else error?
# OR assume that has been handled previously, just update if necessary?
        else:
            ### Create entry
# If creating a new GRADES_INFO entry, the pupil data must be used.
# But is this the right place for this? Should it rather raise an error?
# It should possibly only work in the current term, but I suppose that
# could be handled externally? In a closed term, there is no sure way
# of knowing the correct class and stream.
            gkey = db.addEntry('GRADES_INFO', {
                    'PID': pdata['PID'],
                    'TERM': term,
                    'CLASS': pdata['CLASS'],
                    'STREAM': pdata['STREAM']}
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

    # Check class validity
    klass = Klass(gtable.info.get('CLASS', '–––'))
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
            gradeData = GradeData(schoolyear, term, pdata)
            gradeData.updateGrades(gradeManager)
        REPORT.Info(_NEWGRADES, n = len(pdata_grades),
                klass = klass, year = schoolyear, term = term)
    else:
        REPORT.Warn(_NOPUPILS)


#TODO?
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
    db = DBT(schoolyear)
    pid = pdata['PID']
    if rtag == 'X':
        # Make new tag
        xmax = 0
        with db:
            rows = db.select('GRADES', PID = pid)
        for row in rows:
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
    with db:
        db.updateOrAdd('GRADES_INFO',
            {   'CLASS': pdata.GKLASS.klass,
                'STREAM': pdata.GKLASS.stream,
                'PID': pdata['PID'],
                'TERM': rtag,
                'REPORT_TYPE': pdata.RTYPE,
                'REMARKS': pdata.REMARKS,
                'DATE_D': date,
                'GDATE_D': gdate
            },
            TERM = rtag,
            PID = pid
    )
    # Add grades
    updateGrades(schoolyear, rtag, pdata, grades)



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
        with db:
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


#############################

#DEPRECATED
def getGradeData(schoolyear, pid, term, sid = None):
    """Return all the data from the database GRADES_INFO table for the
    given pupil and the given "term" as a mapping.
        <term>: Either a term (small integer) or, for "extra"
            reports, a tag (Xnn). It may also may also be any other
            permissible entry in the TERM field of the GRADES_INFO table.
    Return a mapping containing the basic grade-info for this year/term/
    pupil.
    If no <sid> is given, there will also be a 'GRADES' item, which is
    a Grade Manager object (primarily a mapping {sid -> grade} for all
    subjects appropriate to the class).
    Note that class and stream of the GRADES_INFO entry may differ from
    those of the pupil (if the pupil has changed class/stream).
    There will also be a 'USERS' item, which is a mapping {sid -> user}
    for all subjects relevant for real grades in the GRADES_INFO item's
    class/stream.
#TODO?: Different for the current term? Here the pupil's group should
# be primary?
    If <sid> is supplied, there will be a 'GRADE' item, which is just
    the grade of the given subject. There will also be a 'USER' item,
    the user who last updated this grade.
    """
    raise DEPRECATED
    db = DBT(schoolyear)
    with db:
        ginfo = db.select1('GRADES_INFO', PID = pid, TERM = term)
    if not ginfo:
        return None
    # Convert the grade info to a <dict>
    gmap = dict(ginfo)

    gkey = gmap['KEYTAG']
    if sid:
        with db:
            record = db.select1('GRADES_LOG', KEYTAG = gkey, SID = sid)
        g, user, rest = record['GRADE'].split(',', 2)
        gmap['GRADE'] = g
        gmap['USER'] = user
    else:
        # Include all subjects
        with db:
            records = db.select1('GRADE_LOG', KEYTAG = gkey)
        grades, users = {}, {}
        for record in records:
            sid = record['SID']
            g, user, rest = record['GRADE'].split(',', 2)
            grades[sid] = (g, user)
        # Read all subjects for the class/group


# Use a grade-manager here? instead of the following lines ...
# That needs a sid2tlist too, so I need to decide on class & stream.

#TODO: different for "current" term?
# Yes, probably: I think I would need the pupil data.
        klass = Klass.fromKandS(gmap['CLASS'], gmap['STREAM'])
        for sid in CourseTables(schoolyear).classSubjects(klass, 'GRADE'):
            try:
                allgrades[sid], allusers[sid] = allgrades[sid]
            except:
                allgrades[sid], allusers[sid] = None, None
        gmap['GRADES'] = allgrades
        gmap['USERS'] = allusers
    return gmap


#DEPRECATED, adjust gradetable.py line 187
def setGrades(schoolyear, gmap):
    raise DEPRECATED
    # Read all subjects
    klass = Klass.fromKandS(gmap['CLASS'], gmap['STREAM'])
    # Read the grades
    db = DBT(schoolyear)
    gkey = gmap['KEYTAG']
    sid2tlist = CourseTables(schoolyear).classSubjects(klass, 'GRADE')
    gmap['GRADES'] = {sid: _readGradeSid(db, gkey, sid)
            for sid in sid2tlist}


#DEPRECATED, see abitur.py ll. 273, 276
def getGrade(schoolyear, ginfo, sid):
    """Fetch the grade for the given subject referenced by the given
    grade-info item.
    """
    raise DEPRECATED
    with DBT(schoolyear) as db:
        # This might be faster with "fetchone" instead of "LIMIT",
        # because of the "DESC" order.
        records = db.select('GRADE_LOG',
                order = 'TIMESTAMP', reverse = True, limit = 1,
                KEYTAG = ginfo['KEYTAG'], SID = sid)
    try:
        return records[0]['GRADE']
    except:
        return None


#DEPRECATED
def _readGradeSid(db, gkey, sid, withuser = False):
    """If there are entries for this key and sid, return the latest.
    If no entries, return <None>.
    If <withuser> is true, return a tuple (grade, user), otherwise
    just return the grade.
    """
    raise DEPRECATED
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





##################### Test functions
_testyear = 2016
def test_01 ():
###
    return
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
        pupils = Pupils(_testyear)
        for pdata in pupils.classPupils(klass):
            gradeData = GradeData(_testyear, _term, pdata)
            gmap = gradeData.getAllGrades()
            REPORT.Test("GRADES for %s: %s" % (pdata.name(), repr(gmap)))

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
            raise
            REPORT.Error("*** grades2db failed ***")
