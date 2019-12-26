#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_grades/gradedata.py

Last updated:  2019-12-24

Handle the data for grade reports.


=+LICENCE=============================
Copyright 2019 Michael Towers

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
_EXCESS_SUBJECTS = "Fachkürzel nicht in Konfigurationsdatei GRADES/ORDERING:\n  {tags}"
_TOO_MANY_SUBJECTS = "Zu wenig Platz für Fachgruppe {group} in Vorlage:\n  {template}"
_MISSING_GRADE = "Keine Note für Schüler {pid} im Fach {sid}"
_UNUSED_GRADES = "Noten für Schüler {pid}, die nicht im Zeugnis erscheinen:\n  {grades}"
_NO_MAPPED_GRADE = "Keine Textform für Note '{grade}'"


import os
from collections import OrderedDict

from wz_core.configuration import Paths
from wz_core.courses import CourseTables
from wz_compat.config import klassData, getTemplateTags
from wz_table.dbtable import readDBTable
from wz_grades.makereports import makeReports


def grade_data(schoolyear, termn, klass_stream):
#TODO: Consider how the grade data is stored for the various streams.
# If a stream is supplied, but there is no file for that stream, a
# whole-klass file should be sought.
# However, perhaps there should only be whole-class files here?
# That would require an uploader to merge individual stream files ...
    filepath = Paths.getYearPath(schoolyear, 'FILE_GRADE_TABLE',
                term=termn).replace('*', klass_stream.replace('.', '-'))
    try:
        return readGradeTable(filepath)
    except FileNotFoundError:
        return None


_INVALID = '/'      # Table entry for cells marked "invalid"
_SUBJECTSCOL = 3    # First column (0-based index) with subject-info
def readGradeTable(filepath):
    """Read the given file as a grade table (xlsx/ods).
    Return a mapping {[ordered] pupil-id -> {subject-id -> value}}.
    The returned mapping also has an "info" attribute, which is a key-value
    mapping of the info-lines from the grade table.
    """
    gtable = readDBTable(filepath)
    # The subject tags are in the columns starting after that with
    # '#' as header.
    sids = {}            # {sid -> table column}
    for sid, col in gtable.headers.items():
        if col >= _SUBJECTSCOL:
            sids[sid] = col
    # Read the pupil rows
    pupils = OrderedDict()
    pupils.info = gtable.info
    for row in gtable:
        pid = row[0]
        pname = row[1]
        stream = row[2]
        grades = {}
        pupils[pid] = grades
        for sid, col in sids.items():
            g = row[col]
            if g:
                grades[sid] = g
    return pupils









class GradeData:
    def __init__(self, schoolyear, term, klass_stream, report_type):
        self.schoolyear = schoolyear
        self.term = term
        self.klass_stream = klass_stream
        self.klassdata = KlassData(klass_stream)

        #### Set up categorized, ordered lists of grade fields for insertion
        #### in a report template.
        self.courses = CourseTables(schoolyear)
        subjects = self.courses.filterGrades(self.klassdata.klass)
        self.template = self.klassdata.template
        alltags = getTemplateTags(self.template)
        # Extract grade-entry tags, i.e. those matching <str>_<int>:
        gtags = {}
        for tag in alltags:
            try:
                group, index = tag.split('_')
                i = int(index)
            except:
                continue
            try:
                gtags[group].append(i)
            except:
                gtags[group] = [i]

        # Check courses and tags against ordering data
        cmap = {tag.split('.')[0]: tag for tag in subjects}
        self.tags = {}       # ordered subject tags for subject groups
        self.indexes = {}    # ordered index lists for subject groups
        for group, otags in CONF.GRADES.ORDERING.items():
            try:
                self.indexes[group] = sorted(gtags[group], reverse=True)
            except KeyError:
                continue
            tlist = []
            self.tags[group] = tlist
            for tag in otags:
                # Pick out the subject tags which are relevant for the klass
                try:
                    tlist.append(cmap.pop(tag))
                except:
                    continue
        if cmap:
            REPORT.Fail(_EXCESS_SUBJECTS, tags=repr(list(cmap)))


#????
    def _setTemplate(self, report_type='text', term=None):
        self.klassdata.setTemplate(report_type, term)


    def getGrades(self):
        """Read all stored grades for the given klass/stream.
        <schoolyear> is an <int>, the year in which the school-year ends.
        <term> determines the school-term/semester/etc. for which the grades
        are given. It is an integer.
        """
        filepath = Paths.getYearPath(self.schoolyear, 'FILE_GRADE_TABLE',
                    term=self.term).replace('*',
                            self.klass_stream.replace('.', '-'))
        gtable = readDBTable(filepath)
        # The subject tags are in the columns starting after that with
        # '#' as header.
        sids = {}            # {sid -> table column}
        for sid, col in gtable.headers.items():
            if col >= _SUBJECTSCOL:
                sids[sid] = col
        # Read the pupil rows
        pupils = OrderedDict()
        for row in gtable:
            pid = row[0]
            pname = row[1]
            stream = row[2]
            grades = {}
            pupils[pid] = grades
            for sid, col in sids.items():
                g = row[col]
                if g:
                    grades[sid] = g
        return pupils


    def getTagmap(self, pgrades, pid, grademap='GRADES'):
        """Prepare tag mapping for substitution – one pupil.
        <pgrades> is a mapping as returned by <getGrades>.
        <pid> is the pupil-id.
        <grademap> is the name of a configuration file (in 'GRADES')
        providing a grade -> text mapping.
        Expected subjects get two entries, one for the subject name and
        one for the grade. They are allocated according to the numbered
        slots according to the predefined ordering (config: GRADES/ORDERING).
        "Grade" entries whose tag begins with '_' and which are not covered
        by the subject allocation are copied directly to the mapping.
        """
        # Get grade info for given pupil
        gmap = pgrades[pid].copy() # keep track of unused grade entries
        tagmap = {}
        for group, taglist in self.tags.items():
            ilist = self.indexes[group].copy()
            for tag in taglist:
                try:
                    g = gmap.pop(tag)
                    if g == _INVALID:
                        continue
                except:
                    REPORT.Error(_MISSING_GRADE, pid=pid, sid=tag)
                    g = '?'
                try:
                    i = ilist.pop()
                except:
                    REPORT.Fail(_TOO_MANY_SUBJECTS, group=group,
                            template=self.template.filename)
                tagmap["%s_%d_N" % (group, i)] = self.courses.subjectName(tag)
                try:
                    tagmap["%s_%d" % (group, i)] = CONF.GRADES[grademap][g]
                except:
                    REPORT.Fail(_NO_MAPPED_GRADE, grade=g)
            # Process superfluous indexes
            NONE = CONF.GRADES[grademap].NONE
            for i in ilist:
                tagmap["%s_%d_N" % (group, i)] = NONE
                tagmap["%s_%d" % (group, i)] = NONE
        unused = []
        for sid, g in gmap.items():
            if g == _INVALID:
                continue
            if sid[0] == '_':
                tagmap[sid] = g
            else:
                unused.append("%s: %s" % (sid, g))
        if unused:
            REPORT.Error(_UNUSED_GRADES, pid=pid, grades="; ".join(unused))
        return tagmap



##################### Test functions
_testyear = 2016
_klass = '12.RS'
_term = 1
_pid = '200403'
_date = '2016-06-22'
def test_01 ():
    REPORT.Test("Reading basic grade data for class %s" % _klass)
#TODO: This might not be the optimal location for this file.
    filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_TABLE',
                term=_term).replace('*', _klass.replace('.', '-'))
    pgrades = readGradeTable(filepath)
    REPORT.Test(" ++ INFO: %s" % repr(pgrades.info))
    for pid, grades in pgrades.items():
        REPORT.Test("\n  -- %s: %s" % (pid, repr(grades)))
    return

    REPORT.Test("\nReading template data for class %s" % _klass)
    REPORT.Test("  Grade tags:\n  %s" % repr(gradedata.tags))
    REPORT.Test("  Indexes:\n  %s" % repr(gradedata.indexes))

    REPORT.Test("\nTemplate grade map for pupil %s, class %s" % (_pid, _klass))
    tagmap = gradedata.getTagmap(pgrades, _pid)
    REPORT.Test("  Grade tags:\n  %s" % repr(tagmap))

def test_02():
    return

    REPORT.Test("Build reports for class %s" % _klass)
    gradedata = GradeData(_testyear, _term, _klass, 'Zeugnis')
    pdfBytes = makeReports(gradedata, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test("  -> %s" % fpath)
