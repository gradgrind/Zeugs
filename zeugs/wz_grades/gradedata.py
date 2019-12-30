#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_grades/gradedata.py

Last updated:  2019-12-30

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
_WRONG_TERM = "In Tabelle, falsches Halbjahr / Kennzeichen: {termf} (erwartet {term})"
_INVALID_TERM = "Ungültiges Halbjahr: '{term}' (vgl. MISC.TERMS)"
_INVALID_YEAR = "Ungültiges Schuljahr: '{val}'"
_WRONG_YEAR = "Falsches Schuljahr: '{year}'"
_INVALID_KLASS = "Ungültige Klasse: {ks}"
#_MISSING_PUPIL = "In Notentabelle: keine Noten für {pname}"
_UNKNOWN_PUPIL = "In Notentabelle: unbekannte Schüler-ID – {pid}"
_NOPUPILS = "Keine (gültigen) Schüler in Notentabelle"
_NEWGRADES = "Noten für {n} Schüler aktualisiert ({year}/{term}: {klass})"
_BAD_GRADE_DATA = "Fehlerhafte Notendaten für Schüler PID={pid}, TERM={term}"


import os
from collections import OrderedDict

from wz_core.configuration import Paths
from wz_core.db import DB
from wz_core.pupils import Pupils
from wz_core.courses import CourseTables
from wz_compat.config import KlassData #, getTemplateTags
from wz_compat.config import toKlassStream
from wz_table.dbtable import readDBTable
#from wz_grades.makereports import makeReports


_INVALID = '/'      # Table entry for cells marked "invalid"
_SUBJECTSCOL = 3    # First column (0-based index) with subject-info
def readGradeTable(filepath):
    """Read the given file as a grade table (xlsx/ods).
    Return a mapping {[ordered] pupil-id -> {subject-id -> value}}.
    The returned mapping also has an "info" attribute, which is a key-value
    mapping of the info-lines from the grade table.
    """
    gtable = readDBTable(filepath)
    pupils = OrderedDict()  # build result here
    # "Translate" the info items, where possible
    kvrev = {v: k for k, v in CONF.TABLES.COURSE_PUPIL_FIELDNAMES.items()}
    pupils.info = {kvrev.get(key, key): value
            for key, value in gtable.info.items()}
    # The subject tags are in the columns starting after the one with
    # '#' as header.
    sids = {}            # {sid -> table column}
    for sid, col in gtable.headers.items():
        if col >= _SUBJECTSCOL:
            sids[sid] = col
    # Read the pupil rows
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



def grades2db(schoolyear, gtable, term=None):
    """Enter the grades from the given table into the database.
    """
    t = gtable.info.get('TERM', '–––')
    if term:
        if term != t:
            REPORT.Fail(_WRONG_TERM, term=term, termf=t)
    else:
        term = t
        if term not in CONF.MISC.TERMS:
            REPORT.Fail(_INVALID_TERM, term=term)
    try:
        y = gtable.info.get('SCHOOLYEAR', '–––')
        yn = int(y)
    except:
        REPORT.Fail(_INVALID_YEAR, val=y)
    if yn != schoolyear:
        REPORT.Fail(_WRONG_YEAR, year=y)
    klass = gtable.info.get('CLASS', '–––')
    # Check validity
    pupils = Pupils(schoolyear)
    try:
        plist = pupils.classPupils(klass)
        if not plist:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, ks=klass)
    p2grades = {}
    p2_ks = {}
    for pdata in plist:
        pid = pdata['PID']
        try:
            p2grades[pid] = gtable.pop(pid)
        except KeyError:
            # The table may include just a subset of the pupils
            continue
        p2_ks[pid] = toKlassStream(klass, pdata['STREAM'])
    for pid in gtable:
        REPORT.Error(_UNKNOWN_PUPIL, pid=pid)
    # Now enter to database
    if p2grades:
        db = DB(schoolyear)
        for pid, grades in p2grades.items():
            gstring = ';'.join([g + '=' + v for g, v in grades.items()])
            db.updateOrAdd('GRADES',
                    {   'CLASS_STREAM': p2_ks[pid], 'PID': pid, 'TERM': term,
                        'REPORT_TYPE': None, 'DATE_D': None, 'GRADES': gstring
                    },
                    TERM=term,
                    PID=pid
            )
        REPORT.Info(_NEWGRADES, n=len(p2grades),
                klass=klass, year=schoolyear, term=term)
    else:
        REPORT.Warn(_NOPUPILS)



def db2grades(schoolyear, term, klass_stream, checkonly=False):
    """Fetch the grades for the given klass, term, schoolyear.
    Return a list [(pid, pname, {subject -> grade}), ...]
    """
    plist = []
    # Get the pupils from the pupils db and search for grades for these.
    pupils = Pupils(schoolyear)
    db = DB(schoolyear)
    for pdata in pupils.classPupils(klass_stream):
        pid = pdata['PID']
        pk = pdata['CLASS']
        ps = pdata['STREAM']
        if pk != klass_stream:
            pks = toKlassStream(pk, ps)
            if pks != klass_stream:
                # Pupil has switched klass and/or stream.
                # This can only be handled via individual view.
                continue
        gdata = db.select1('GRADES', PID=pid, TERM=term)
        if gdata:
            gstring = gdata['GRADES'] or None
        else:
            gstring = None
        if gstring and not checkonly:
            plist.append((pid, pdata.name(), grades2map(gstring)))
        else:
            plist.append((pid, pdata.name(), gstring))
    return plist



def getGradeData(schoolyear, pid, term):
    db = DB(schoolyear)
    gdata = db.select1('GRADES', PID=pid, TERM=term)
    if gdata:
        # Convert the grades to a <dict>
        gmap = dict(gdata)
        gstring = gdata['GRADES']
        gmap['GRADES'] = grades2map(gstring) if gstring else None
        return gmap
    return None



def grades2map(gstring):
    try:
        grades = {}
        for item in gstring.split(';'):
            k, v = item.split('=')
            grades[k.strip()] = v.strip()
        return grades
    except:
        if gstring:
            REPORT.Fail(_BAD_GRADE_DATA, pid=pid, term=term)
        # There is an entry, but no data
        return None



class GradeReportData:
    # <klass_stream> should probably be from the grade entry, to ensure
    # that the correct template and klass-related data is used.
    def __init__(self, schoolyear, rcat, klass_stream):
        """<rcat> is the report category, a key to the mapping GRADE_TEMPLATES.
        """
        self.schoolyear = schoolyear
        self.rcat = rcat
        self.klass_stream = klass_stream
        self.klassdata = KlassData(klass_stream)

        #### Set up categorized, ordered lists of grade fields for insertion
        #### in a report template.
        self.courses = CourseTables(schoolyear)
        subjects = self.courses.filterGrades(self.klassdata.klass)
#????:
        self.klassdata.setTemplate(rcat)


#        self.template = self.klassdata.template
        alltags = getTemplateTags(self.klassdata.template)
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


    def getTagmap(self, grades, pid, grademap='GRADES'):
        """Prepare tag mapping for substitution in the report template,
        for the pupil <pid>.
        <grades> is a mapping {sid -> grade}
        <grademap> is the name of a configuration file (in 'GRADES')
        providing a grade -> text mapping.
        Expected subjects get two entries, one for the subject name and
        one for the grade. They are allocated according to the numbered
        slots according to the predefined ordering (config: GRADES/ORDERING).
        "Grade" entries whose tag begins with '_' and which are not covered
        by the subject allocation are copied directly to the mapping.
        """
        gmap = grades.copy() # keep track of unused grade entries
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
    from glob import glob
    files = glob(Paths.getYearPath(_testyear, 'FILE_GRADE_TABLE',
                term='*'))
    for filepath in files:
        pgrades = readGradeTable(filepath)
        grades2db(_testyear, pgrades)

def test_03():
    return

    from wz_table.dbtable import dbTable
    fmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_TABLE',
                term=_term).replace('*', _klass.replace('.', '-'))
    pgrades = dbTable(filepath, fmap)
# This contains empty entries (None)
    REPORT.Test(" ++ INFO: %s" % repr(pgrades.info))
    for pid, grades in pgrades.items():
        REPORT.Test("\n  -- %s: %s" % (pid, repr(grades)))
    return

    REPORT.Test("Build reports for class %s" % _klass)
    gradedata = GradeData(_testyear, _term, _klass, 'Zeugnis')
    pdfBytes = makeReports(gradedata, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test("  -> %s" % fpath)
