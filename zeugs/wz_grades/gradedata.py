### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/gradedata.py

Last updated:  2020-04-19

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
_INVALID_TERMTAG = "Ungültige Zeugniskategorie für Klasse {ks}: {tag}"
_STREAM_CURRENT = ("Maßstab ({stream} kann im „aktuellen“ Halbjahr nur über"
        " den Schüler ({pname}) eingestellt werden")
_NOT_GRADEGROUP = "Gruppe {group} ist keine „Notengruppe“"
_BAD_STREAM = "Ungültiger Gruppe/Bewertungsmaßstab für {pname}: {stream}"


import os, datetime
from collections import OrderedDict, namedtuple

from wz_core.configuration import Paths, Dates
from wz_core.db import DBT, GRADES_INFO_FIELDS
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_core.teachers import Users
from wz_core.template import getGradeTemplate, getTemplateTags, TemplateError
from wz_compat.gradefunctions import Manager
from wz_compat.grade_classes import gradeGroups, validTermTag, klass2streams
from wz_table.dbtable import readPSMatrix


_INVALID = '/'      # Table entry for cells marked "invalid"


""" OVERVIEW

Grade information is managed by the class <GradeData>. It is based upon
"term" (in the widest sense, including various special, non-term-based
tags) and pupil, the latter via a <PupilData> instance.

Internally there are two levels of grade management. Firstly there is
the GRADES_INFO table, which contains all relevant information except
the subject -> grade mapping itself.

Then there is the GRADES_LOG table, containing the actual grades. These
are indexed by a combination of KEYTAG and SID (subject id).
KEYTAG is the primary key of the GRADES_INFO table.
This table contains not only the latest grades, but also any previously
allocated grades (hence the LOG part of the name).
In this log are also special entries to indicate where class/stream
changes took place.

In addition to the school-class and "stream" of each pupil there is a
class and a stream associated with the grade information. Normally the
class/stream tags of pupil and grade-information are the same, but if
a pupil has switched class/stream there could be a difference. For "old"
data this is no problem, but the class/stream of the grade information
will be taken as primary.

When the "current term" is being handled, such a difference is not
permitted. The class/stream of the pupil is now regarded as primary.

When any update operations are run, the class/stream of the grades-
information will be updated if it differs from the primary values.

A "forced" change of stream for a report's grades entry can be
effected by specifying the <stream_override> parameter to the
constructor. This is, however, not permitted for the "current term".

RETRIEVING GRADES

There are two methods for retrieving grades, returning all
information about either a single subject or all subjects for a pupil
and "term". The all-subjects variant encapsulates its grades in a
"grade manager" (see module "gradefunctions").

UPDATING GRADES

There is a single method for updating grades, but the parameters cater
for a variety of needs. A single grade can be updated, or many. Also
other related information can be updated (the GRADES_INFO fields) by
passing appropriate parameters.

***********************

Grade information is needed on a per pupil basis for individual report
editing and building. This can be retrieved using the <getAllGrades>
method.

Grade information is also needed on a subject basis for teacher-subject
based editing. This is available via the method <getGrade>, though
of course one would need to iterate through the pupils.

Warnings will be issued if "old" grades (from before a class/stream
change) are read.

It may not really be necessary in this case, but it is probably a bit
"cleaner" if updating is done within a locked read/write transaction.

One update function (admin only) needs to accept a set of grades
for a pupil and term, including the possibility of a change of stream
to that of the new data.

For the "current term" a change of class/stream is only possible in the
pupil-data editor.

The second update function (available to all users) would handle grades
for a particular group of pupils, for a subject in the "current term"
only. Because also the user who last entered a grade for a particular
subject is recorded in the log, this information is also available to
the user interface.

A "normal" user may only update a grade if there is no entry at present
or if (s)he was the last person to modify it. In the editor it might
help to make non-editable grades visible, but read-only, and to show
the "owner".
"""


def getGradeEntries(schoolyear, pdata):
    """Return all existing grades-info entries for the given pupil.
    They are returned as an iterator over the <sqlite3.Row> instances.
    """
    with DBT(schoolyear) as db:
        return db.select('GRADES_INFO', PID = pdata['PID'])



class GradeData:
    """Manager for grade data for a particular term and pupil.
    """
    @staticmethod
    def timestamp():
        return datetime.datetime.now().isoformat(sep='/',
                timespec='seconds')


    def __init__(self, schoolyear, term, pdata, stream_override = None):
        """Get all the data from the database GRADES_INFO table for the
        given pupil and the given "term".
            <term>: Either a term (small integer) or, for "extra"
                reports, a tag (Xnn). It may also may also be any other
                permissible entry in the TERM field of the GRADES_INFO
                table.
            <pdata>: A <PupilData> instance. It may, however, have
                additional attributes.
            <stream_override>: A stream to be used regardless of that of
                pupil or grades-info entry.
        The data is stored as attributes:
            ginfo: the fields of the GRADES_INFO entry. This should be
                read using ".get", in case fields are missing. This is
                not updated when entries are changed!
            gclass: The school-class associated with the grade-info.
            gstream: The "stream" associated with the grade-info.
        """
        self.schoolyear = schoolyear
        # The exclusive parameter is for the case that things are updated,
        # in order to avoid (unlikely, but theoretically possibly) race
        # conditions.
        self.db = DBT(schoolyear, exclusive = True)
        self.term = term
        self.pdata = pdata
        # Ideally the class/stream in the GRADE_INFO entry will be the
        # same as that of the pupil, but if the pupil's class or stream
        # has changed, there could be a difference. In the "current term"
        # (only), the grade class/stream must then be adapted. Otherwise
        # the difference is tolerable, the GRADE_INFO values will be used.
        # A stream override is not permissible in the "current term".
        self.gclass = pdata['CLASS']
        try:
            CurrentTerm(schoolyear, term)
        except CurrentTerm.NoTerm:
            self.current = False
        else:
            self.current = True
        # If not <self.current>, this may be overridden by the GRADES_INFO
        # entry and the <stream_override> parameter:
        self.gstream = pdata['STREAM']

        # "Default" settings
        self.KEYTAG = None
        self.ginfo = {}

        if term != 'X':
            # (A new "special" report has no grades or grades-info yet)
            # Seek an existing GRADES_INFO entry
            with self.db:
                _ginfo = self.db.select1('GRADES_INFO', TERM = term,
                        PID = pdata['PID'])
            if _ginfo:
                self.KEYTAG = _ginfo['KEYTAG']
                self.ginfo = dict(_ginfo)
                if not self.current:
                    # If not "current term" use the grades-info
                    # class and stream
                    self.gclass = _ginfo['CLASS']
                    self.gstream = _ginfo['STREAM']
        if stream_override and stream_override != self.gstream:
            if self.current:
                REPORT.Fail(_STREAM_CURRENT, pname = pdata.name(),
                        stream = stream_override)
            if stream_override not in klass2streams(self.gclass):
                REPORT.Fail(_BAD_STREAM, pname = pdata.name(),
                        stream = stream_override)
            self.gstream = stream_override
        if not self.ginfo:
            # Currently no entry in GRADES_INFO, check validity of <term>.
            if term != 'X' and not validTermTag(self.gclass,
                    self.gstream, term):
                REPORT.Fail(_INVALID_TERMTAG, tag = term,
                        ks = self.gclass + '.' + self.gstream)
        self._GradeManager = Manager(self.gclass, self.gstream, term)


    def validGrades(self):
        return self._GradeManager.VALIDGRADES


    def getGrade(self, sid):
        """Return the grade for the given subject. The user who entered
        the grade is in <self.user>.
        If there is no entry for the subject, return <None>, user <None>.
        """
        self.user = None
        if not self.KEYTAG:
            return None
        with self.db:
            record = self.db.select1('GRADES_LOG',
                    KEYTAG = self.KEYTAG, SID = sid)
        if not record:
            return None
        gentry = record['GRADE']
        # Check for class/group change (pending or prefix)
        cg, sg = self.ginfo['CLASS'], self.ginfo['STREAM']
        if cg != self.gclass or sg != self.gstream:
            REPORT.Warn(_CHANGE_FROM, pname = self.pdata.name(),
                    ks = cg + '.' + sg)
        while gentry[0] == '#':
            change, gentry = gentry.split(None, 1)
            REPORT.Warn(_CHANGE_FROM, pname = self.pdata.name(),
                    ks = change[1:])
        g, self.user, rest = gentry.split(',', 2)
        # Validate grade
        if g in self.validGrades():
            return g
        REPORT.Error(_BAD_GRADE, pname = self.pdata.name(),
                sid = sid, grade = g)
        return None


    def getAllGrades(self):
        """Return a Grade Manager with a complete set of grades.
        """
        self.users, grades = {}, {}
        if self.KEYTAG:
            # Check for pending class/group change
            cg, sg = self.ginfo['CLASS'], self.ginfo['STREAM']
            if cg != self.gclass or sg != self.gstream:
                REPORT.Warn(_CHANGE_FROM, pname = self.pdata.name(),
                        ks = cg + '.' + sg)
            with self.db:
                records = self.db.select('GRADES_LOG', KEYTAG = self.KEYTAG)
            for record in records:
                sid = record['SID']
                gentry = record['GRADE']
                # Check for class/group-change prefix
                while gentry[0] == '#':
                    change, gentry = gentry.split(None, 1)
                    REPORT.Warn(_CHANGE_FROM, pname = self.pdata.name(),
                            ks = change[1:])
                g, user, rest = gentry.split(',', 2)
                self.users[sid] = user
                grades[sid] = g
        # Read all subjects for the class/group
        courses = CourseTables(self.schoolyear)
        sid2tlist = courses.classSubjects(
                Klass.fromKandS(self.gclass, self.gstream), 'GRADE')
        # Use a Grade Manager to validate and complete the grades
        self.grades = self._GradeManager(self.schoolyear, sid2tlist,
                grades, self.pdata)
        return self.grades


    def updateGrades(self, grades, user = None, **xfields):
        """Update the grades of all subjects in <grades> if they have
        changed and the user has permission.
            <grades> is a mapping: {sid -> grade}
        Only administrators can "overwrite" grades entered by someone
        else. If no <user> is supplied, the null user is used, which
        acts like an administrator.
        If <xfields> is supplied, it must be a mapping with values for
        the GRADES_INFO fields.
        """
        # Read all subjects for the class/group
        courses = CourseTables(self.schoolyear)
        sid2tlist = courses.classSubjects(Klass.fromKandS(
                self.gclass, self.gstream), 'GRADE')

        # Use a Grade Manager to validate and complete the grades
        gmap = self._GradeManager(self.schoolyear, sid2tlist, grades,
                self.pdata)
        # First set up <utest>, which is true if the user must be
        # checked when entering a new grade.
        if (not user) or user == 'X':
            utest = False
            user = 'X'
        else:
            try:
                perms = Users().permission(user)
                if 's' in perms:
                    utest = False
                elif 'u' in perms:
                    utest = True
                else:
                    raise ValueError
            except:
                REPORT.Fail(_INVALID_USER, user = user)
        timestamp = self.timestamp()
        with self.db:
            ### Handle grades-info
            if self.KEYTAG:
                ## A grades-info entry exists already
                # Check for class/stream changes
                if (self.ginfo['STREAM'] != self.gstream
                        or self.ginfo['CLASS'] != self.gclass):
                    xfields['STREAM'] = self.gstream
                    xfields['CLASS'] = self.gclass

                    # Prepend the old class/stream to each existing
                    # grade entry, e.g. "#10.RS:<timestamp>\n"
                    for row in self.db.select('GRADES_LOG',
                            KEYTAG = self.KEYTAG):
                        pk = row['ID']
                        g = row['GRADE']
                        self.db.updateOrAdd('GRADES_LOG',
                            {'GRADE': '#%s.%s:%s\n%s' % (self.gclass,
                                    self.gstream, self.timestamp(), g)
                            }, update_only = True, ID = pk
                        )

                if xfields:
                    self.db.updateOrAdd('GRADES_INFO', xfields,
                            update_only = True, KEYTAG = self.KEYTAG)

            else:
                ## There is no grades-info entry
                if self.term == 'X':
                    ### Make new tag
                    xmax = 0
                    rows = self.db.select('GRADES', PID = self.pdata['PID'])
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
                    self.term = 'X%02d' % (xmax + 1)

                ### Add grades-info entry
                xfields.update({
                    'TERM': self.term,
                    'PID': self.pdata['PID'],
                    'CLASS': self.gclass,
                    'STREAM': self.gstream,
                })
                self.KEYTAG = self.db.addEntry('GRADES_INFO', xfields)

            ### Add grades
            for sid, g in gmap.items():
                if not g:
                    # Null grades are ignored
                    continue
                g1 = ','.join((g, user, timestamp))
                # Get previous entry, if any
                record = self.db.select1('GRADES_LOG',
                        KEYTAG = self.KEYTAG, SID = sid)
                if not record:
                    # There is no entry, so a new one is needed
                    self.db.addEntry('GRADES_LOG', {
                            'KEYTAG': self.KEYTAG,
                            'SID': sid,
                            'GRADE': g1
                        }
                    )
                    continue
                gentry = record['GRADE']
                # If there is a class/stream change, enter the new grade
                # whether or not it differs from the old one.
                if gentry[0] != '#':
                    # No class/stream change
                    g0, user0, rest = gentry.split(',', 2)
                    if g == g0:
                        continue
                    # Check that it is really a permissible change
                    if utest and (user != user0):
                        # User permissions inadequate
                        REPORT.Error(_LAST_USER, user0 = user0,
                                sid = sid, pname = pdata.name())
                        continue
                # Prepend a new grade entry
                self.db.updateOrAdd('GRADES_LOG',
                        {'GRADE': '%s\n%s' % (g1, gentry)},
                        update_only = True,
                        KEYTAG = self.KEYTAG, SID = sid)



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
    _GradeManager = None
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
            # Enter the grades
            gradeData = GradeData(schoolyear, term, pdata)
            gradeData.updateGrades(grades)
        REPORT.Info(_NEWGRADES, n = len(pdata_grades),
                klass = klass, year = schoolyear, term = term)
    else:
        REPORT.Warn(_NOPUPILS)


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
            gdata = db.select1('GRADES_INFO', PID = pid, TERM = term)
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
            {(string) group -> <GradeDates> instance},
            with empty dates being ''
        Otherwise, <group> (a <Klass> instance) should be provided. It
        must be one of the <gradeGroups>.
        One or more of the other arguments should then be provided,
        the value being written to the database.
        <lock>, should be 0, 1 or 2.
            0: Lock completely. The dates, etc., should be transferred
               to the individual GRADES_INFO entries.
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
        ggroups = gradeGroups(self.TERM)
        for ks in ggroups:
            k = str(ks)
            gmap[k] = info.get(k) or GradeDates(DATE_D = '', LOCK = 1,
                    GDATE_D = '')
        if group:
            if not group.inlist(ggroups):
                REPORT.Fail(_NOT_GRADEGROUP, group = group)
        else:
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
                    gdata = GradeData(self.schoolyear, self.TERM, pdata)
                    if not gdata.KEYTAG:
                        # This is a very weak test ...
                        REPORT.Warn(_NO_GRADES_FOR_PUPIL, pname = pdata.name())
                        continue
                    if gdata.ginfo['DATE_D']:
                        REPORT.Warn(_PUPIL_ALREADY_LOCKED, pname = pdata.name())
                        continue
                    # If no existing report type, use the default
                    # ... this can be empty.
                    _rtype = gdata.ginfo['REPORT_TYPE'] or rtype or 'X'
                    gdata.updateGrades({}, DATE_D = date,
                            GDATE_D = gdate, REPORT_TYPE = _rtype)

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
    pupils = Pupils(_testyear)
    REPORT.Test("Reading basic grade data for pupil %s" % _pid)
    gdata = GradeData(_testyear, _term, pupils.pupil(_pid))
    klass = Klass.fromKandS(gdata.gclass, gdata.gstream)

    gradedata = GradeReportData(_testyear, klass)
    REPORT.Test("\nGrade groups:\n  %s" % repr(gradedata.sgroup2sids))
    REPORT.Test("\nExtra fields: %s" % repr(gradedata.xfields))

    # Get the report type from the term and klass/stream
    _rtype = getTermTypes(klass, _term)[0]
    REPORT.Test("\nReading template data for class %s (type %s)" %
            (klass, _rtype))

    pupils = Pupils(_testyear)
    gm = gdata.getAllGrades()
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
