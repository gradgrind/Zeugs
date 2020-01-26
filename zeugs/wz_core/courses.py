# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_core/courses.py

Last updated:  2020-01-26

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
from .pupils import Pupils, Klass
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
                try:
                    # Check and normalize class name
                    classes [Klass(f).klass] = col
                except:
                    REPORT.Fail(_INVALID_KLASS, klass=f)
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
        """Return a sorted list of normalized school-class names.
        """
        return sorted (self._classes)


    def classSubjects (self, klass):
        """Return the subject list for the given class.
        <klass> is a <Klass> instance.
            {[ordered] sid -> <TeacherList> instance}
        """
        return self._classes [klass.klass]


    def subjectName (self, sid):
        """Return the full name of the given subject (sid).
        """
        return self._names [sid]


    def filterGrades (self, klass):
        """Return the subject mapping for the given class including only
        those subjects relevant for a grade report.
        <klass> is a <Klass> instance.
        Return {[ordered] sid -> teacher list}
        """
        sids = OrderedDict ()
        for sid, tlist in self.classSubjects (klass).items ():
            if tlist.GRADE:
                sids [sid] = tlist
        return sids


    def filterText (self, klass):
        """Return the subject mapping for the given class including only
        those subjects relevant for a text report.
        <klass> is a <Klass> instance.
        Return {[ordered] sid -> teacher list}
        """
        sids = OrderedDict ()
        for sid, tlist in self.classSubjects (klass).items ():
            if tlist.TEXT:
                sids [sid] = tlist
        return sids



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
        subjects = ctables.classSubjects (Klass(klass))
        REPORT.Test ("  -- %s: %s" % (klass, repr (subjects)))

    klass = '10'
    REPORT.Test ("\nCLASS %s:" % klass)
    for sid, sinfo in ctables.classSubjects (Klass(klass)).items ():
        REPORT.Test ("  ++ %s (%s): %s" % (ctables.subjectName (sid),
                sid, sinfo))

    REPORT.Test ("\nClass %s, grade subjects:" % klass)
    for sid, sinfo in ctables.filterGrades (Klass(klass)).items ():
        REPORT.Test ("  ++ %s (%s): %s" % (ctables.subjectName (sid),
                sid, sinfo))

    REPORT.Test ("\nClass %s, text subjects:" % klass)
    for sid, sinfo in ctables.filterText (Klass(klass)).items ():
        REPORT.Test ("  ++ %s (%s): %s" % (ctables.subjectName (sid),
                sid, sinfo))
