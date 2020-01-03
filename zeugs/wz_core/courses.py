#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_core/courses.py

Last updated:  2020-01-02

Handler for the basic course info.

=+LICENCE=============================
Copyright 2017-2020 Michael Towers

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

The main table, with path FILE_SUBJECTS, defines the available subjects
and provides a little information about them. Each class has a column
in this table in which the relevance of each subject for this class can
be defined by an entry including teacher-ids and flags.

The structure of an entry:
--------------------------

The simplest form is a teacher-id. There may also be a comma-separated
list of teacher-ids.

Subjects which are relevant for text reports, but not for grade reports
have their teacher entry prefixed by '*'.

There are entries in the subject table which do not represent taught
subjects. These have tags (first column) which begin with '_'.
One type is "composite subjects", which are for grade reports and
represent "subjects" whose grade results as a combination (average) of
other subjects.
TODO: There may also be entries for special grade information, such as
averages, qualifications, etc.

Teacher entries may also be prefixed by '$', which means the subject is
graded, but no text report is expected.

Finally, a '#' prefix indicates that a subject may be taught, but no
report entry is expected (perhaps relevant for timetabling, etc.).

The course data for all classes is managed by <CourseTables>, which has
the following methods:
    <classes ()>
        returns a sorted list of class names for which subject data
        is available.
    <classSubjects (klass)>
        returns an ordered mapping for the class:
            {sid -> subject info}
        Only subjects with an entry for that class will be included.
    <subjectName (sid)>
        returns the full name of the subject.
    <filterGrades (klass)>
        returns an ordered mapping {sid -> [tid, ...]} for
        the given class, only those subjects relevant for grade reports.
    <filterText (klass)>
        returns an ordered mapping {sid -> [tid, ...]} for
        the given class, only those subjects relevant for text reports.
    <teacherMatrix (klass)>
        returns a mapping {pid -> {sid -> tid}} for "real" subjects
        taken by the pupils.
    <optoutMatrix (klass)>
        generates (or regenerates) a table (spreadsheet files) for
        specifiying opt-outs of optional courses and choosing teachers
        for subjects with teaching groups.
"""

# Special subject information
_NOTTEXT = '$'
_NOTGRADE = '*'
_NOREPORT = '#'

_OPTOUT = '---'
_INVALID = '-----'


_MATRIXTITLE = 'Fachbelegung (Fach+Schüler -> Lehrer oder "nicht gewählt")'

# Messages
_COURSEMATRIX = ("Fach-Schüler-Belegungsmatrix erstellt für Klasse {klass}:\n"
            "  {path}")
_NOPUPILS = "Keine Schüler in Klasse {klass}"
_UNKNOWN_STREAM = "In Fachtabelle, unbekannte Maßstabsgruppe: {stream} in {entry}"
_INVALID_STREAM = "In Fachtabelle, ungültige Angabe der Maßstabsgruppen: {entry}"
_INVALID_TEACHER = "In Fachtabelle, ungültige Angabe der Lehrer: {entry}"
_EMPTY_COMPOSITE = "In Fachtabelle, Sammelfach fehlt: {entry}"
_EMPTY_TEACHER = "In Fachtabelle, kein Lehrer für Fach {sid} in Klasse {klass}"
#_TEXT_GRADE_CONFLICT = "Fach {sid}, Klasse {klass}: ungültiger Eintrag: {entry}"
_BAD_COMPOSITE = "Klasse {klass}, Fach '{sid}': ungültiges Sammelfach '{c}'"
_NO_COMPOSITE = "Klasse {klass} hat kein Sammelfach '{sid}'"
_NO_COMPONENTS = "Sammelfach {composite}, Klasse {klass} hat keine Komponenten"
_BAD_TEACHER = ("Klasse {klass}: Unerwarteter Lehrer ({tid}) für"
        " Schüler {pid} im Fach {sid}")
_NO_TEACHER = "Klasse {klass}: Kein Lehrer für Schüler {pid} im Fach {sid}"
_TEACHER_CLASH = ("Klasse {klass}, Wahltabelle: Lehrer für Schüler {pid}"
        " im Fach {sid} überflüssig")


from collections import OrderedDict, UserList

from .configuration import Paths
from .pupils import Pupils
from .teachers import TeacherData
# To read subject table:
from wz_table.dbtable import readDBTable
# To (re)write class-course matrix
from wz_table.formattedmatrix import FormattedMatrix


class TeacherList(list):
    """A list of teacher-ids.
    There are also flag attributes to indicate whether the list is
    relevant for particular report types: <TEXT> and <GRADE>.
    """
    def __init__(self, commasep, rowflag):
        """Convert a comma-separated string into a list.
        <rowflag> is the default flag for the subject:
            <None>, <_NOTTEXT>, <_NOTGRADE> or <_NOREPORT>
        """
        super().__init__()
        for item in commasep.split (','):
            i = item.strip ()
            if i:
                self.append (i)
        i0 = self[0][0]
        if i0.isalpha():
            i0 = rowflag
        else:
            self[0] = self[0][1:]
        self.TEXT = i0 not in (_NOTTEXT, _NOREPORT)
        self.GRADE = i0 not in (_NOTGRADE, _NOREPORT)


_CLASSESCOL = 3 # First column with class-info
class CourseTables:
    def __init__ (self, schoolyear):
        """Read the subject table for the year.
        The first column is the subject id, the second the subject name.
        The third column (header '#') is for flags which can specify that
        a subject is not relevant for certain reports:
            <_NOTGRADE>: not relevant for grade reports
            <_NOTTEXT>: not relevant for text reports
            <_NOREPORT>: not relevant for any reports
        The flags may also be prepended to the teacher lists for individual
        classes – in case the handling of the subject varies from class
        to class.
        Two mappings are built:
        <self._names>: {sid -> subject name}
        <self._classses>: {class -> {[ordered] sid -> <TeacherList> instance}
        In the latter there are only entries for non-empty cells (the
        teacher list may, however, be empty).
        """
        self.schoolyear = schoolyear
        self.teacherData = TeacherData (schoolyear)
        fpath = Paths.getYearPath (schoolyear, 'FILE_SUBJECTS')
        data = readDBTable (fpath)
        # The class entries are in the columns after that with '#' as header.
        classes = {}            # {class -> table column}
        for f, col in data.headers.items ():
            if col >= _CLASSESCOL:
                classes [f] = col
        # Read the subject rows
        self._classes = {}
        self._names = {}
        for row in data:
            sid = row [0]
            self._names [sid] = row [1]
            flag = row [2]
            # Add to affected classes ({[ordered] sid -> teacher list})
            for klass, col in classes.items ():
                # Handle the teacher tags
                val = row [col]
                if val:
                    tlist = TeacherList(val, flag)
                    try:
                        self._classes [klass] [sid] = tlist
                    except:
                        self._classes [klass] = OrderedDict ([(sid, tlist)])


    def classes (self):
        return sorted (self._classes)


    def classSubjects (self, klass):
        """Return the subject list for the given class:
            {[ordered] sid -> <TeacherList> instance}
        """
        return self._classes [klass]


    def subjectName (self, sid):
        """Return the full name of the given subject (sid).
        """
        return self._names [sid]


    def filterGrades (self, klass):
        """Return the subject mapping for the given class including only
        those subjects relevant for a grade report:
            {[ordered] sid -> teacher list}
        """
        sids = OrderedDict ()
        for sid, tlist in self.classSubjects (klass).items ():
            if tlist.GRADE:
                sids [sid] = tlist
        return sids


    def filterText (self, klass):
        """Return the subject mapping for the given class including only
        those subjects relevant for a text report:
            {[ordered] sid -> teacher list}
        """
        sids = OrderedDict ()
        for sid, tlist in self.classSubjects (klass).items ():
            if tlist.TEXT:
                sids [sid] = tlist
        return sids


#TODO?
    def optoutMatrix (self, klass):
        """Build a class-course matrix of teachers for each pupil and
        subject combination.
        This is for specifiying opt-outs of optional courses and choosing
        a teacher for subjects with multiple teachers in the main subject
        matrix. Also, teachers not specified in the main matrix
        (<_NNTEACHER>) should be specified here.
        The contents of an existing table should be taken into account.
        All "taught" subjects should be included, that means all subjects
        that are relevant for text or grade reports (with at least one
        teacher entry in the subject matrix).
        """
        tmatrix = self.teacherMatrix (klass)
        sid2info = tmatrix.sid2info
        subjects = [(sid, self._names [sid])
                for sid, sinfo in sid2info.items ()]
        build = FormattedMatrix (self.schoolyear, 'FILE_CLASS_SUBJECTS',
                klass)
        # Manage subjects affected by stream
        pupils = []
#TODO: Validation lists?
        for pid, sid2tid in tmatrix.items ():
            pdata = sid2tid.pupilData
            pupils.append (pdata)
            pstream = pdata ['STREAM']
            for sid, sname in subjects:
                sinfo = sid2info [sid]
                if sinfo.STREAMS and pstream not in sinfo.STREAMS:
                    sid2tid [sid] = _INVALID
                    continue
                tid = sid2tid.get (sid)
                tid0 = sid2info [sid].TIDS
                if not tid:
                    sid2tid [sid] = _OPTOUT
                elif tid == _NNTEACHER:
                    # Error -> no entry in opt-out table
                    sid2tid [sid] = None
                elif tid == sid2info [sid].TIDS:
                    # The tid is taken from the main table.
                    sid2tid [sid] = None

        build.build (_MATRIXTITLE, pupils, subjects, tmatrix)
        fpath = build.save ()
        REPORT.Info (_COURSEMATRIX, klass=klass, path=fpath)

#?
    def teacherMatrix (self, klass):
        """Return a mapping {[ordered] pid -> {sid -> tid}} for "real"
        subjects taken by the pupils, those that are represented in text
        or grade reports.
        This mapping has the subject info as attribute <sid2info>.
        A further attribute is <filepath>, giving the path of the option
        table (<None> if there isn't one).
        The {sid -> tid} sub-mappings have the associated pupil data as
        attribute <pupilData>.
        If there is an invalid entry, an error is reported and <_NNTEACHER>
        is returned for that subject.
        """
        class _adict (dict): pass   # a <dict> with extra attributes

        pupils = Pupils (self.schoolyear).classPupils (klass)
        if len (pupils) == 0:
            REPORT.Error (_NOPUPILS, klass=klass)
            return None
        pid2tids = OrderedDict ()   # build result mapping here
        # Get the subject info for the class:
        sid2info = OrderedDict ()
        for sid, sinfo in self.classSubjects (klass).items ():
            if sinfo.NOTGRADE and sinfo.NOTTEXT:
                continue
            if sinfo.TIDS:
                sid2info [sid] = sinfo
        # Retain all (relevant) subject info in the result:
        pid2tids.sid2info = sid2info
        # Read the opt-out matrix (if it exists):
        optout = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_SUBJECTS', klass)
        try:
            # Path of opt-out table, if there is one. This is needed to
            # make back-ups of the opt-out files:
            pid2tids.filepath = optout.filepath
        except:
            pid2tids.filepath = None
        # Iterate through the pupils:
        for pdata in pupils:
            pid = pdata ['PID']
            sid2tid = _adict ()
            sid2tid.pupilData = pdata
            pid2tids [pid] = sid2tid
            try:
                popts = optout [pid]
            except:
                popts = None
            for sid, sinfo in sid2info.items ():
                # Manage subjects affected by stream
                try:
                    # If <sinfo.STREAMS> is <None> there will be an exception
                    if pdata ['STREAM'] not in sinfo.STREAMS:
                        continue
                except:
                    pass
                # Check entry in opt-out matrix
                tids = sinfo.TIDS
                try:
                    otid = popts [sid]
                except:
                    # No entry in opt-out matrix
                    otid = None
                # Manage teacher "wild card"
                if otid:
                    # <otid> is the opt-out entry
                    if otid == _OPTOUT:
                        continue
                    if type (tids) == list:
                        # Check tid is in main list
                        if otid in tids:
                            tids = otid
                        else:
                            REPORT.Error (_BAD_TEACHER, klass=klass,
                                    pid=pid, sid=sid, tid=otid)
                            tids = _NNTEACHER
                    elif tids == _NNTEACHER:
                        if self.teacherData.checkTeacher (otid):
                            tids = otid
                    else:
                        REPORT.Error (_TEACHER_CLASH, klass=klass,
                                    pid=pid, sid=sid)
                        tids = _NNTEACHER
                elif tids == _NNTEACHER:
                    REPORT.Error (_NO_TEACHER, klass=klass,
                            pid=pid, sid=sid)
                sid2tid [sid] = tids
        return pid2tids






##################### Test functions
_testyear = 2016
def test_01 ():
    REPORT.Test ("Reading basic subject data for %d" % _testyear)
    ctables = CourseTables (_testyear)
    REPORT.Test ("\nSUBJECTS:")
    for sid, sname in ctables._names.items ():
        REPORT.Test ("  -- %s: %s" % (sid, sname))

    clist = ctables.classes ()
    REPORT.Test ("\nCLASSES: " + repr (clist))

    REPORT.Test ("\nSubject lists:")
    for klass in clist:
        subjects = ctables.classSubjects (klass)
        REPORT.Test ("  -- %s: %s" % (klass, repr (subjects)))

    klass = '10'
    REPORT.Test ("\nCLASS %s:" % klass)
    for sid, sinfo in ctables.classSubjects (klass).items ():
        REPORT.Test ("  ++ %s (%s): %s" % (ctables.subjectName (sid),
                sid, sinfo))

    REPORT.Test ("\nClass %s, grade subjects:" % klass)
    for sid, sinfo in ctables.filterGrades (klass).items ():
        REPORT.Test ("  ++ %s (%s): %s" % (ctables.subjectName (sid),
                sid, sinfo))

    REPORT.Test ("\nClass %s, text subjects:" % klass)
    for sid, sinfo in ctables.filterText (klass).items ():
        REPORT.Test ("  ++ %s (%s): %s" % (ctables.subjectName (sid),
                sid, sinfo))

"""
def test_02 ():
    _klass = '12'
    ctables = CourseTables (_testyear)
    REPORT.Test ("Lehrermatrix, Klasse %s" % _klass)
    for pid, sid2tid in ctables.teacherMatrix (_klass).items ():
        REPORT.Test ("Schüler %s: %s" % (pid, repr (sid2tid)))

def test_03 ():
    ctables = CourseTables (_testyear)
    for _klass in '10', '11', '12', '13':
        REPORT.Test ("Kursbelegungsmatrix, Klasse %s" % _klass)
        ctables.optoutMatrix (_klass)
"""
