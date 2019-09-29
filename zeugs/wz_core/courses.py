#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_core/courses.py

Last updated:  2019-09-29

Handler for the basic course info.

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

##########
#TODO: rewrite all this – it is very out of date!

The course data for all classes is managed by <CourseTables>, which has two
basic, low-level methods, very much like the pupil database:
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

# Subject type tags
_GTAG = 'n'
_TTAG = 't'

_MATRIXTITLE = 'Kursbelegung (Fach+Schüler -> Lehrer)'

# Messages
_FIELD_UNKNOWN = "Unerwartetes Feld in Fachliste: {field}"
_NO_SID_FIELD = "Kein SID-Feld in Fachliste: {field}"
_COURSEMATRIX = ("Kurs-Schüler-Belegungsmatrix erstellt für Klasse {klass}:\n"
            "  {path}")
_NOPUPILS = "Keine Schüler in Klasse {klass}"


from collections import OrderedDict, namedtuple

from .configuration import Paths
from .pupils import Pupils
# To read subject table:
from wz_table.dbtable import readDBTable
# To (re)write class-course matrix
from wz_table.optiontable import makeOptionsTable


class CourseTables:
    def __init__ (self, schoolyear):
        self.schoolyear = schoolyear
        fpath = Paths.getYearPath (schoolyear, 'FILE_SUBJECTS')
        data = readDBTable (fpath)
        fields = CONF.TABLES.COURSES_FIELDNAMES
        rfields = {v: k for k, v in fields.items ()}
        fmap = OrderedDict ()   # {field -> column}
        classes = {}            # {class -> column}
        flag = False
        sidcol = None
        for f, col in data.headers.items ():
            if f == '#':
                flag = True
                continue
            if flag:
                classes [f] = col
            else:
                try:
                    f1 = rfields [f]
                except:
                    REPORT.Fail (_FIELD_UNKNOWN, field=f)
                if f1 == 'SID':
                    sidcol = col
                else:
                    fmap [f1] = col
        if sidcol == None:
            try:
                sidfield = fields ['SID']
            except:
                sidfield = '???'
            REPORT.Fail (_NO_SID_FIELD, field=sidfield)

        #### Subject data structure:
        self.sdata = namedtuple ('Subject', fmap)

        self.class2subjects = {}
        self.subject2info = {}
        for row in data:
            sid = row [sidcol]
            # Build course data structure (namedtuple)
            # Empty cells have ''
            sbj = self.sdata (*[row [col] or '' for col in fmap.values ()])
            self.subject2info [sid] = sbj

            # Add to affected classes ({sid -> tags})
            for klass, col in classes.items ():
                val = row [col]
                if val:
                    try:
                        self.class2subjects [klass] [sid] = val
                    except:
                        self.class2subjects [klass] = OrderedDict ([(sid, val)])


    def classes (self):
        return sorted (self.class2subjects)


    def classSubjects (self, klass):
        """Return the subject list for the given class:
            {sid -> tag}
        The tag is a string containing <_GTAG> if a grade report is expected
        and <_TTAG> if a text report is expected.
        """
        return self.class2subjects [klass]


    def subjectInfo (self, sid):
        """Return the information for the given subject, as a
        namedtuple ('Subject').
        """
        return self.subject2info [sid]


    def filterTexts (self, klass):
        """Return the subject list for the given class including only
        those subjects for which a text report is expected:
            {sid -> subject info}
        """
        sids = OrderedDict ()
        for sid, sdata in self.classSubjects (klass).items ():
            sinfo = self.subjectInfo (sid)
            if _TTAG in sdata:
                sids [sid] = sinfo
        return sids


    def filterGrades (self, klass, realonly=False):
        """Return the subject list for the given class including only
        those subjects relevant for a grade list:
            {sid -> subject info}
        That can include "unreal" subjects, e.g. composite grades. These
        are marked by '*' in the FLAGS field.
        If <realonly> is true, only "real" subjects will be included, i.e.
        those actually taught in courses.
        """
        sids = OrderedDict ()
        for sid, sdata in self.classSubjects (klass).items ():
            sinfo = self.subjectInfo (sid)
            if _GTAG in sdata:
                if realonly and '*' in sinfo:
                    continue
                sids [sid] = sinfo
        return sids


    def _courseMatrix (self, klass):
        """Build a class-course matrix of teachers for each pupil and
        subject combination.
        The contents of an existing table should be taken into account.
        """
        pupils = Pupils (self.schoolyear).classPupils (klass)
        if len (pupils) == 0:
            REPORT.Warn (_NOPUPILS, klass=klass)
        subjects = []
        for sid, sdata in self.classSubjects (klass).items ():
            sinfo = self.subjectInfo (sid)
            if _GTAG in sdata or _TTAG in sdata:
                if '*' in sinfo.FLAGS:
                    continue
                subjects.append ((sid, sinfo.COURSE_NAME))
        fpath = makeOptionsTable (_MATRIXTITLE, self.schoolyear, klass,
                pupils, subjects, 'FILE_CLASS_SUBJECTS')
        REPORT.Info (_COURSEMATRIX, klass=klass, path=fpath)


    def courseMatrices (self):
        """Build a class-course matrix of teachers for each class.
        """
        for klass in self.classes ():
            self._courseMatrix (klass)



##################### Test functions
_testyear = 2016
def test_01 ():
    REPORT.Test ("Reading basic subject data for %d" % _testyear)
    ctables = CourseTables (_testyear)
    REPORT.Test ("\nSUBJECTS:")
    for sid, info in ctables.subject2info.items ():
        REPORT.Test ("  -- %s: " % sid + repr (info))

    clist = ctables.classes ()
    REPORT.Test ("\nCLASSES: " + repr (clist))

    REPORT.Test ("\nSubject lists:")
    for klass in clist:
        subjects = ctables.classSubjects (klass)
        REPORT.Test ("  -- %s: " % klass + repr (subjects))

    REPORT.Test ("\nCLASS 10:")
    for sid, sdata in ctables.classSubjects ('10').items ():
        REPORT.Test ("  ++ %s (%s): %s" % (sid, repr (sdata),
                repr (ctables.subjectInfo (sid))))

    REPORT.Test ("\nClass 10, real only for grades:")
    for sid, sinfo in ctables.filterGrades ('10', realonly=True).items ():
        REPORT.Test ("  ++ %s: %s" % (sid, repr (sinfo)))

    REPORT.Test ("\nClass 10, for text reports:")
    for sid, sinfo in ctables.filterTexts ('10').items ():
        REPORT.Test ("  ++ %s: %s" % (sid, repr (sinfo)))


def test_02 ():
    ctables = CourseTables (_testyear)
    REPORT.Test ("Kursbelegungsmatrizen")
    ctables.courseMatrices ()
