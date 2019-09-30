#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_core/courses.py

Last updated:  2019-09-30

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

The main table, with path FILE_SUBJECTS, defines the available subjects
and provides a little information about them. Each class has a column
in this table in which the relevance of each subject for this class can
be defined by tags.
Most of the additional information about the subjects – as well as
entries for "unreal" subjects (ones that are not taught but relevant in
some context) – is connected with grade reports. "Unreal" subjects are
marked by a "*" in the FLAGS field. The CGROUPS field is used for
computing combined grades and averages, etc. for grade reports.

Together with the pupils database, a second table can be generated with
entries for each pupil/subject pair (only the subjects which are actually
taught – for which grades are given or texts are written). Here the
responsible teacher (as teacher-tag) can be entered. It is also possible
to enter a list of teachers (comma-separated) if it is not (yet) clear
who is responsible for a particular pupil. This must be taken into
account when collating texts/grades. There is a table for each class,
with path FILE_CLASS_SUBJECTS.

The course data for all classes is managed by <CourseTables>, which has
the following methods:
    <classes ()>
        returns a sorted list of class names for which subject data
        is available.
    <classSubjects (klass)>
        returns an ordered mapping for the class:
            {sid -> tags}
        The tags specify the relevance of the subject (e.g. for text
        reports and/or grade reports).
    <subjectInfo (sid)>
        returns the general information for the subject as a
        <namedtuple> ('Subject').
    <filterText (klass)>
        returns an ordered mapping {sid -> subject info ('Subject')} for
        the given class, only those subjects relevant for text reports.
    <filterGrades (klass, realonly=False)>
        returns an ordered mapping {sid -> subject info ('Subject')} for
        the given class, only those subjects relevant for grade reports.
        If <realonly> is true, only subjects which are actually taught
        are included.
    <courseMatrices>
        generates (or regenerates) tables (spreadsheet files) for mapping
        pupil and subject to the responsible teacher(s).
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
from wz_table.formattedmatrix import FormattedMatrix


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
        build = FormattedMatrix (self.schoolyear, 'FILE_CLASS_SUBJECTS',
                klass)
        build.build (_MATRIXTITLE, pupils, subjects, infolines=None)
        fpath = build.save ()
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
