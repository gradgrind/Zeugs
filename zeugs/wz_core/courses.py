#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_core/courses.py

Last updated:  2019-07-13

Handler for the tables detailing the courses.

=+LICENCE=============================
Copyright 2017-2019 Michael Towers

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

The course data for all classes is managed by <CourseTables>, which has two
basic, low-level methods, very much like the pupil database in <DBase>:
    <classes ()>
        returns a list of class names for which subject data
        is available.
    <classSubjects (klass)>
        returns a list object containing <ClassData> named-tuples for the
        lines in the table for the given class. This list object also has
        an <info> attribute, which is an ordered mapping of the "info"
        lines in the table.

There are methods (<filterText> and <filterGrades>) for extracting the
data needed by reports.

The data is stored in spreadsheet files, one for each class, structured as
a "DBTable". The name of the class is embedded in the filename, but is also
specified in an "info" line. The two names should be identical.
The table files are stored at a location specified in the configuration
file "PATHS" by the entry FILE_CLASSDATA.

The information for each "course" is available in a line of the table, the
first column being a short identifier ("subject tag", in the code
generally <sid>). The other columns contain the information needed for the
various modules dealing with courses/subjects. As these lines are not used
only for the specification of concrete, taught courses, but also for
various other pieces of information – especially for grade reports
("composite" subjects) and special timetable entries – the term "course"
is not always really suitable. So sometimes "subject" is used instead,
but this is also not always suitable ...
A subject tag may have more than one line in a table. This allows separate
definition of courses for different groups, or teachers, etc.

Where there is a "groups" entry (CGROUP), the subject (line) is only
relevant for pupils who have this group in their "groups" field.
It is also possible to specify subgroups – only pupils who are in both
specified groups will be included. This is done by joining the two
groups with a dot, e.g. "A.Gym" – pupils in both group "A" and group "Gym".

There is a field (TEACHER) for the teacher responsible for the course.
Only a single teacher tag may be entered here. If more than one teacher is
to write reports or give grades for the course, separate lines must be
entered for each teacher.

There is also a field (COURSE_NAME) for the course name, but this is
primarily for clarity, it is not used in the reports. The printed name is
fetched from the separate table listing all available course names. A
warning is issued if the two names are not identical.

???
When the text reports for a subject are written by various teachers,
it might be necessary to specify which of the teachers is responsible
for a common header text. This will be the specified by the first line
in the table defining the subject in question. If such a subject is
specified for more than one group of pupils, there will be a separate
header text for each group. The groups may not, however, overlap
(i.e. a pupil for whom the subject is relevant may not be in two groups).

For other attributes of a course there is the "flags" field (FLAGS).
This allows other bits of information about the course to be registered,
for example handwritten reports. If there is a '-' in this field, the line
will not be considered for text reports, 'H' indicates handwritten text
reports.

For text reports, only the above-mentioned fields are relevant. For
other uses of the table, such as grades, further information is
necessary.

Not only "normal", taught courses are defined in the table. There are also
so-called "composite" subjects, which are needed for grades. These group
other (real) subjects together into a single grade (normally the average
of the "components") – they are not themselves taught courses. These lines
are only of interest to the grade modules. They have a special entry in
the "teacher" field: '#'.

Some other "subjects" may be specified which are not taught as such, but
do refer to real teaching situations. These can be slots in the timetable
for block lessons, the contents of which change during the year, for
example. They are of no interest for reports, but are relevant for
timetabling.

The GRADEINFO field of a subject table provides additional information
for grade reports.
'-' indicates that the line is not to be used for grade reports.
A single letter indicates that the subject can be used in areas of the
report form reserved for subjects whose name is not explicitly given in
the form. Each such area has a series of entries for subjects with a
particular letter.
"""

DOTSEP = '.'            # Separator in cgroup fields
INVALID_CELL = '/'      # "Invalid" cell value
# Flags (can be extended)
FLAG_NOREPORT = '-'
FLAG_HAND = 'H'


# Messages
_MISSINGDBFIELD = "Feld fehlt in Fach-Tabelle {filepath}:\n  {field}"
_MISSINGDBFIELD2 = "Feld fehlt in Fachnamen-Tabelle {filepath}:\n  {field}"
_BADCLASS = "Falsche Klasse in Fach-Tabelle {filepath}"
_UNKNOWNSID = ("Fachkürzel {sid} ({iname}) ist in der Fachnamentabelle"
               " nicht vorhanden. Klassentabelle:\n  {path}")
_REPEATSID = "Fach-Kürzel '{sid}' mehrfach definiert in {filepath}"
_BADGRADEINFO = "Fach-Kürzel '{sid}': Notenzeugnis-Feld ({ginfo}) ungültig"
_NAMEMISMATCH       = ("Kursname ({iname}) für Fachkürzel {sid} stimmt mit"
                    " Fachnamentabelle ({name}) nicht überein:\n  {path}"
                    "   '{name}' wird benutzt.")
_BADHASHPGROUP = "Klasse {klass}: {pname} in ungültiger Gruppe ({group})"
_BADHASHPGROUPTID = "Klasse {klass}, {pname}: ungültiger Lehrer in Gruppe ({group})"
_UNKNOWNGROUP = "Fachgruppe {group} ist nicht in Konfigurationsdatei GROUPS"
_NOREALTEXT = "Klasse {klass}: Keine Lehrkraft für Textzeugnis im Fach {sid}"
_SIDREALANDNONREAL = "Klasse {klass}: Fach {sid} ist nicht eindeutig (Lehrkraft '#')"


import os
from glob import glob
from collections import UserDict, OrderedDict, namedtuple, UserList

from .configuration import Paths
from .dbase import DBase
from .teachers import TeacherData
# To read subject tables:
from wz_table.dbtable import readDBTable


# Course data, the index is the subject tag:
TextCourse = namedtuple('TextCourse',
        ['sid', 'name', 'cgroup', 'teacher', 'flags'])
GradeCourse = namedtuple('GradeCourse',
        ['sid', 'name', 'cgroup', 'teacher', 'flags', 'ginfo'])
# ginfo:
#  · empty: a subject with a named slot in grade report templates.
#  · otherwise a letter coding for a block of unnamed entries in grade
#    report templates.


def groupSets ():
    return [gs.split () for gs in CONF.GROUPS.GROUPS]


class CourseTables:
    def __init__ (self, schoolyear):
        self.schoolyear = schoolyear
        self.teacherData = TeacherData (schoolyear)
        self.pupilData = DBase (schoolyear)
        self.courseMaster = CourseMaster (schoolyear)


    def classes (self):
        files = glob (Paths.getYearPath (self.schoolyear, 'FILE_CLASSDATA'))
        return sorted ([f.rsplit ('_', 1) [1].split ('.') [0]
                for f in files])


    @staticmethod
    def classFields ():
        """Get ordered field list for the class tables.
        The config file has: internal name -> table name.
        """
        return CONF.TABLES.DB_COURSE_FIELDNAMES.values ()

    @staticmethod
    def ClassData ():
        return namedtuple ('ClassData', CONF.TABLES.DB_COURSE_FIELDNAMES)


    def classSubjects (self, klass):
        """Read in a table containing subject data for the given class.
        Return an ordered list of <ClassData> named tuples.
        Only lines with non-empty teacher field are included. If the
        teacher-field doesn't start with '#' it must be a teacher tag in
        the teacher table.
        """
        filepath = Paths.getYearPath (self.schoolyear,
                'FILE_CLASSDATA').replace ('*', klass)

        # An exception is raised if there is no file:
        table = readDBTable (filepath)

#TODO: There is no schoolyear in the info ... should I add it?
#        try:
#            if int (table.info [_SCHOOLYEAR]) != self.schoolyear:
#                raise ValueError
#        except:
#            REPORT.Fail (_BADSCHOOLYEAR, filepath=filepath)
        _KLASS = CONF.TABLES.PUPIL_COURSE_FIELDNAMES ['%CLASS']
        try:
            if table.info [_KLASS] != klass:
                raise ValueError
        except:
            REPORT.Fail (_BADCLASS, filepath=filepath)

        # Ordered field list for the table.
        rfields = self.classFields ()
        # Rebuild the list with <ClassData> instances.
        rows = UserList ()
        rows.info = table.info
        colmap = []
        for f in rfields:
            try:
                colmap.append (table.headers [f])
            except:
                # Field not present
                REPORT.Warn (_MISSINGDBFIELD, filepath=filepath,
                        field=f)
                colmap.append (None)

        ### Read the row data
        classData = self.ClassData ()    # namedtuple
        for row in table:
            rowdata = []
            for col in colmap:
                rowdata.append (None if col == None else row [col])
            cdata = classData (*rowdata)

            # Check teacher tag
            tid = cdata.TEACHER
            if not tid:
                # Any line with an empty teacher field will be ignored.
                continue
            if tid [0] != '#' and not self.teacherData.checkTeacher (tid):
                # Invalid teacher tag
                continue

            # Check subject name against master name table, "normalise" the group:
            sid, iname = cdata.SID, cdata.COURSE_NAME
            try:
                name = self.courseMaster [sid]
            except:
                REPORT.Fail (_UNKNOWNSID, sid=sid, iname=iname, path=filepath)
                assert False

            if name != iname:
                REPORT.Warn (_NAMEMISMATCH, sid=sid, iname=iname, name=name,
                        path=filepath)
                cdata = cdata._replace (COURSE_NAME=name)

            # Normalise <group>
            cgroup = cdata.CGROUP
            if cgroup and DOTSEP in cgroup:
                cdata = cdata._replace (CGROUP=DOTSEP.join (
                        sorted (cgroup.split (DOTSEP))))

            rows.append (cdata)

        return rows


    def filterTexts (self, klass):
        """Preprocess the data for use in text report generation.
        Return a list of <TextCourse> instances.
        For compatibility with grade courses, an empty result attribute
        <nonreal> is added.
        Only courses for which a text report is expected are included in
        the result list.
        These may not have a '-' in the FLAGS field (and also expect a
        "real" teacher in the TEACHER field).
        """
        courses = UserList ()
        courses.nonreal = []
        for cdata in self.classSubjects (klass):
            tid = cdata.TEACHER
            flags = cdata.FLAGS or ''
            if flags == FLAG_NOREPORT:
                continue
            if tid [0] == '#':
                REPORT.Error (_NOREALTEXT, klass=klass, sid=cdata.SID)
                continue
            courses.append (TextCourse (
                    cdata.SID,
                    cdata.COURSE_NAME,
                    cdata.CGROUP,
                    tid,
                    flags))
        return courses


    def filterGrades (self, klass, realonly=False):
        """Preprocess the data for use in grade report generation.
        Return a list of <GradeCourse> instances.
        If <realonly> is true, only "real" subjects will be included, i.e.
        a real teacher must be given (not starting with '#').
        A <sid> may not be both a "real" and a nonreal course.
        Nonreal courses are listed in the result attribute <nonreal>.
        The information in the GRADEINFO field is included. If this field
        is '-', the line will not be included. The information in the
        FLAGS field is included, but has no effect on the inclusion of
        the line.
        """
        courses = UserList ()
        courses.nonreal = []
        cset = set ()           # For checking ambiguous '#'-teachers
        for cdata in self.classSubjects (klass):
            tid = cdata.TEACHER
            flags = cdata.FLAGS or ''
            ginfo = cdata.GRADEINFO or ''
            if ginfo == FLAG_NOREPORT:
                continue
            sid = cdata.SID
            if tid [0] == '#':
                if sid not in courses.nonreal:
                    if sid in cset:
                        REPORT.Fail (_SIDREALANDNONREAL, klass=klass, sid=sid)
                    if realonly: continue
                    courses.nonreal.append (sid)
            else:
                if sid in courses.nonreal:
                    REPORT.Fail (_SIDREALANDNONREAL, klass=klass, sid=sid)
            if ginfo and (len (ginfo) != 1 or not ginfo.isalpha ()):
                REPORT.Error (_BADGRADEINFO, sid=cdata.SID, ginfo=ginfo)
                continue
            cset.add (sid)
            courses.append (GradeCourse (
                                cdata.SID,
                                cdata.COURSE_NAME,
                                cdata.CGROUP,
                                tid,
                                flags,
                                ginfo))
        return courses


    def courseMatrix (self, klass, date=None, text=False, group=None):
        """Build a matrix of possible teachers for each pupil and subject
        combination.
        If <text> is true, courses relevant for text reports are included
        (which must be "real" courses, with a teacher), otherwise courses
        for grade reports.
        A subject without a subject group is (potentially) relevant for
        all pupils. For subject groups including subgroups (e.g. 'A.Gym')
        a pupil must be in all the member groups.
        If a date is given, only pupils registered for that date will be
        included.
        If <group> is supplied, only pupils in that group (and subjects
        for that group) will be included.
        A pupil without any groups specified will be assumed to participate
        only in courses for which no group is specified ("whole class").
        A tuple is returned:
            sid_name: ordered mapping: {sid -> Subject name}
               ... this takes on the attribute <nonreal> from the course list.
            pmatrix: [( <PupilData>,
                        pupil's short name,
                        ordered mapping: {sid -> {tid, ...}}),
                ...]
        """
        # Data for all relevant course table entries:
        # {ordered: sid -> {cgroup -> {tid, ...}}
        courses = OrderedDict ()
        clist = self.filterTexts (klass) if text else self.filterGrades (klass)
        sid_name = OrderedDict ()           # Mapping: sid -> subject name
        sid_name.nonreal = clist.nonreal    # With tid [0] == '#'
        # Get mutually exclusive group set
        nongroups = []
        if group:
            for gset in groupSets ():
                if group in gset:
                    nongroups = [g for g in gset if g != group]
                    break
            else:
                REPORT.Warn (_UNKNOWNGROUP, group=group)

        for course in clist:
            sid = course.sid
            cgroup = course.cgroup
            if group and cgroup:
                # Check that the subject group is compatible with <group>
                notcompat = False
                for cg in cgroup.split (DOTSEP):
                    if cg in nongroups:
                        notcompat = True
                        break
                if notcompat:
                    continue

            # (Not every subject will necessary have pupils)
            sid_name [sid] = course.name
            try:
                sid_group = courses [sid]
            except:
                courses [sid] = {cgroup: {course.teacher}}
                continue
            try:
                sid_group [cgroup].add (course.teacher)
            except:
                sid_group [cgroup] = {course.teacher}

        # Build list containing (for each pupil):
        #    <PupilData>, short name, ordered mapping: {sid -> {tid, ...}}
        plist = []
        # For each pupil:
        for pdata in self.pupilData.classPupils (klass, date=date, group=group):
            psname = self.pupilData.shortName (pdata)
            sid_tids = OrderedDict ()
            plist.append ((pdata, psname, sid_tids))
            pgsplit = []    # groups to which the pupil belongs
            pchoice = {}    # choice mapping: {sid -> tid}
            if pdata.GROUPS:
                for pg in pdata.GROUPS.split ():
                    if pg [0] == '#':
                        try:
                            sid, tid = pg [1:].rsplit (DOTSEP, 1)
                            if sid not in sid_name:
                                continue
                        except:
                            REPORT.Error (_BADHASHPGROUP, klass=klass,
                                    pname=psname, group=pg)
                            continue
                        pchoice [sid] = tid
                    else:
                        pgsplit.append (pg)
            for sid, cgroup_tids in courses.items ():
                tids = set ()
                for cg, gtids in cgroup_tids.items ():
                    if cg:
                        # A subject group is given.
                        if pgsplit:
                            if cg not in pgsplit:
                                cg2 = cg.split ('.')
                                if len (cg2) == 1:
                                    continue
                                use = True
                                for cg in cg2:
                                    if cg not in pgsplit:
                                        use = False
                                        break
                                if not use:
                                    continue
                        else:
                            # Pupil not in any groups.
                            continue
                    #else: no <cg>
                    tids.update (gtids)
                if tids:
                    try:
                        ctid = pchoice [sid]
                    except:
                        sid_tids [sid] = tids
                    else:
                        if ctid in tids:
                            sid_tids [sid] = ctid
                        else:
                            REPORT.Error (_BADHASHPGROUPTID, klass=klass,
                                    pname=psname, group=pg)
                            sid_tids [sid] = tids

        return sid_name, plist


#TODO: Is this used?
    @staticmethod
    def pupilMissing (klass, pid, report):
        report (_PUPILNOTINCHOICETABLE, klass=klass, pid=pid)


#TODO: Is this used?
    @staticmethod
    def courseMissing (klass, pid, key, report):
        report (_KEYNOTINCHOICETABLE, klass=klass, pid=pid, key=key)



class CourseMaster (UserDict):
    """Manage the master table of course information.
    It is basically a mapping {sid -> name}, but has additional information:
    <self.info> is a mapping containing any "info" data from the master
    file:
        {field: value, ...}
    <self.fields> is a mapping containing any other fields contained
    in the master table:
        {sid -> {field: value, ...}
    """
    def __init__ (self, schoolyear):
        super ().__init__ ()
        filepath = Paths.getYearPath (schoolyear, 'FILE_COURSE_MASTER')
        # An exception is raised if there is no file:
        table = readDBTable (filepath)
        self.info = table.info
        self.fields = {}
        colmap = {}
        for f, ft in CONF.TABLES.COURSENAMES.items ():
            try:
                fi = table.headers [ft]
                if f == 'COURSE_NAME':
                    iname = fi
                else:
                    colmap [f] = fi
            except:
                # Field not present
                REPORT.Fail (_MISSINGDBFIELD2, filepath=filepath,
                        field=ft)

        for row in table:
            sid = row [0]
            if sid in self:
                REPORT.Fail (_REPEATSID, sid=sid, filepath=filepath)
                assert False
            self [sid] = row [iname]
            if len (colmap) > 0:
                fmap = {}
                self.fields [sid] = fmap
                for f, i in colmap.items ():
                    fmap [f] = row [i]



##################### Test functions
def test_01 ():
    REPORT.PRINT ("Groups:", groupSets ())

def test_02 ():
    # Test course table reading
    schoolyear = 2016
    ctables = CourseTables (schoolyear)

    REPORT.PRINT ("Classes:", ctables.classes ())

def test_03 ():
    schoolyear = 2016
    klass = '10'
    date = '2016-06-15'
    ctables = CourseTables (schoolyear)
    REPORT.PRINT ("\n -=========== class %s ===========-" % klass)
    sidname, pmatrix = ctables.courseMatrix (klass, date=date, text=True)
    for pdata, pname, st in pmatrix:
        REPORT.PRINT ("\n ::::", pdata.PID, st)
    REPORT.PRINT ("\n +++++ Subjects:")
    for sid, sname in sidname.items ():
        REPORT.PRINT (" --", sid, sname)

def test_04 ():
    schoolyear = 2016
    ctables = CourseTables (schoolyear)
    for klass in ctables.classes ():
        entries = ctables.classSubjects (klass)
        REPORT.PRINT ("\n  ==========", klass)
        for sdata in entries:
            REPORT.PRINT ("§§§", sdata)

def test_05 ():
    schoolyear = 2016
    klass = '12'
    ctables = CourseTables (schoolyear)
    REPORT.PRINT ("\n --===============================--\n")
    courses = ctables.filterGrades (klass=klass)
    for cdata in courses:
        REPORT.PRINT ("==>>", cdata, "\n")
