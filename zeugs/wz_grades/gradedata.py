# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/gradedata.py

Last updated:  2020-01-26

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
_TOO_MANY_SUBJECTS = ("Zu wenig Platz für Fachgruppe {group} in Vorlage:"
        "\n  {template}\n  {pname}: {sids}")
_MISSING_GRADE = "Keine Note für {pname} im Fach {sid}"
_UNUSED_GRADES = "Noten für {pname}, die nicht im Zeugnis erscheinen:\n  {grades}"
_NO_MAPPED_GRADE = "Keine Textform für Note '{grade}'"
_WRONG_TERM = "In Tabelle, falsches Halbjahr / Kennzeichen: {termf} (erwartet {term})"
_INVALID_YEAR = "Ungültiges Schuljahr: '{val}'"
_WRONG_YEAR = "Falsches Schuljahr: '{year}'"
_INVALID_KLASS = "Ungültige Klasse: {klass}"
#_MISSING_PUPIL = "In Notentabelle: keine Noten für {pname}"
_UNKNOWN_PUPIL = "In Notentabelle: unbekannte Schüler-ID – {pid}"
_NOPUPILS = "Keine (gültigen) Schüler in Notentabelle"
_NEWGRADES = "Noten für {n} Schüler aktualisiert ({year}/{term}: {klass})"
_BAD_GRADE_DATA = "Fehlerhafte Notendaten für Schüler PID={pid}, TERM={term}"
_UNGROUPED_SID = ("Fach fehlt in Fachgruppen (in GRADES.ORDERING): {sid}"
        "\n  Vorlage: {tfile}")


import os
from collections import OrderedDict

from wz_core.configuration import Paths
from wz_core.db import DB, UpdateError
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_compat.template import getGradeTemplate, getTemplateTags
from wz_table.dbtable import readDBTable


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
    <schoolyear> is checked against the value in the info part of the
    table (gtable.info['SCHOOLYEAR']).
    <term>, if given, is only used as a check against the value in the
    info part of the table (gtable.info['TERM']).
    """
    # Check school-year
    try:
        y = gtable.info.get('SCHOOLYEAR', '–––')
        yn = int(y)
    except ValueError:
        REPORT.Fail(_INVALID_YEAR, val=y)
    if yn != schoolyear:
        REPORT.Fail(_WRONG_YEAR, year=y)
    # Check term
    rtag = gtable.info.get('TERM', '–––')
    if term:
        if term != rtag:
            REPORT.Fail(_WRONG_TERM, term=term, termf=rtag)
    # Check klass
    klass = Klass(gtable.info.get('CLASS', '–––'))
    # Check validity
    pupils = Pupils(schoolyear)
    try:
        plist = pupils.classPupils(klass)
        if not plist:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, klass=klass)
    # Filter the relevant pids
    p2grades = {}
    p2stream = {}
    for pdata in plist:
        pid = pdata['PID']
        try:
            p2grades[pid] = gtable.pop(pid)
        except KeyError:
            # The table may include just a subset of the pupils
            continue
        p2stream[pid] = pdata['STREAM']
    # Anything left unhandled in <gtable>?
    for pid in gtable:
        REPORT.Error(_UNKNOWN_PUPIL, pid=pid)

#TODO: Sanitize input ... only valid grades?

    # Now enter to database
    if p2grades:
        db = DB(schoolyear)
        for pid, grades in p2grades.items():
            gstring = map2grades(grades)
            db.updateOrAdd('GRADES',
                    {   'KLASS': klass.klass, 'STREAM': p2stream[pid],
                        'PID': pid, 'TERM': rtag, 'REPORT_TYPE': None,
                        'DATE_D': None, 'GRADES': gstring
                    },
                    TERM=rtag,
                    PID=pid
            )
        REPORT.Info(_NEWGRADES, n=len(p2grades),
                klass=klass, year=schoolyear, term=rtag)
    else:
        REPORT.Warn(_NOPUPILS)



def singleGrades2db(schoolyear, pid, klass, term, date, rtype, grades):
    """Add or update GRADES table entry for a single pupil and date.
    <term> is the date of the entry, which may already exist: the TERM field.
    <date> is the new date, which may be the same as <term>, but can also
    indicate a change, in which case also the TERM field will be changed.
    <rtype> is the report type.
    <grades> is a mapping {sid -> grade}.
    """
    db = DB(schoolyear)
    gstring = map2grades(grades)
    db.updateOrAdd('GRADES',
            {   'KLASS': klass.klass, 'STREAM': klass.stream, 'PID': pid,
                'TERM': term if term.isdigit() else date,
                'REPORT_TYPE': rtype, 'DATE_D': date, 'GRADES': gstring
            },
            TERM=term,
            PID=pid
    )



def updateGradeReport(schoolyear, pid, term, date, rtype):
    """Update grade database when building reports.
    <pid> (pupil-id) and <term> (term or extra date) are used to key the
    entry in the GRADES table.
    For term reports, update only DATE_D and REPORT_TYPE fields.
    This is not used for "extra" reports.
    """
    db = DB(schoolyear)
    termn = int(term)   # check that term (not date) is given
    try:
        # Update term. This only works if there is already an entry.
        db.updateOrAdd ('GRADES',
                {'DATE_D': date, 'REPORT_TYPE': rtype},
                update_only=True,
                PID=pid, TERM=term
        )
    except UpdateError:
        REPORT.Bug("No entry in db, table GRADES for: PID={pid}, TERM={term}",
                pid=pid, term=term)



def db2grades(schoolyear, term, klass, checkonly=False):
    """Fetch the grades for the given school-class/group, term, schoolyear.
    Return a list [(pid, pname, {subject -> grade}), ...]
    <klass> is a <Klass> instance, which can include a list of streams
    (including '_' for pupils without a stream). If there are streams,
    only grades for pupils in one of these streams will be included.
    """
    slist = klass.streams
    plist = []
    # Get the pupils from the pupils db and search for grades for these.
    pupils = Pupils(schoolyear)
    db = DB(schoolyear)
    for pdata in pupils.classPupils(klass):
        # Check pupil's stream if there is a stream filter
        pstream = pdata['STREAM']
        if slist and (pstream not in slist):
            continue
        pid = pdata['PID']
        gdata = db.select1('GRADES', PID=pid, TERM=term)
        if gdata:
            gstring = gdata['GRADES'] or None
            if gstring:
                if gdata['KLASS'] != klass.klass or gdata['STREAM'] != pstream:
                    # Pupil has switched klass and/or stream.
                    # This can only be handled via individual view.
                    gstring = None
        else:
            gstring = None
        if gstring and not checkonly:
            try:
                gmap = grades2map(gstring)
            except ValueError:
                REPORT.Fail(_BAD_GRADE_DATA, pid=pid, term=term)
            plist.append((pid, pdata.name(), gmap))
        else:
            plist.append((pid, pdata.name(), gstring))
    return plist



def getGradeData(schoolyear, pid, term):
    """Return all the data from the database GRADES table for the
    given pupil as a mapping. Either term or – in the case of "extra"
    reports – date is supplied to key the entry.
    The string in field 'GRADES' is converted to a mapping. If there is
    grade data, its validity is checked. If there is no grade data, this
    field is <None>.
    """
    db = DB(schoolyear)
    gdata = db.select1('GRADES', PID=pid, TERM=term)
    if gdata:
        # Convert the grades to a <dict>
        gmap = dict(gdata)
        try:
            gmap['GRADES'] = grades2map(gdata['GRADES'])
        except ValueError:
            REPORT.Fail(_BAD_GRADE_DATA, pid=pid, term=term)
        return gmap
    return None



def grades2map(gstring):
    """Convert a grade string from the database to a mapping:
        {sid -> grade}
    """
    try:
        grades = {}
        for item in gstring.split(';'):
            k, v = item.split('=')
            grades[k.strip()] = v.strip()
        return grades
    except:
        if gstring:
            raise ValueError
        # There is an entry, but no data
        return None



def map2grades(gmap):
    """Convert a mapping {sid -> grade} to a grade string for the GRADES
    field in the GRADES table.
    """
    return ';'.join([g + '=' + v for g, v in gmap.items()])



class GradeReportData:
    """Manage data connected with a school-class, stream and report type.
    When referring to old report data, bear in mind that a pupil's stream,
    or even school-class, may have changed. The grade data includes the
    class and stream associated with the data.
    """
    def __init__(self, schoolyear, rtype, klass):
        """<rtype> is the report type, a key to the mapping
        GRADE.REPORT_TEMPLATES.
        <klass> is a <Klass> object, which may include stream tags.
        All streams passed in must map to the same template.
        """
        self.schoolyear = schoolyear
        self.klassdata = klass

        ### Set up categorized, ordered lists of grade fields for insertion
        ### in a report template.
        # If there is a list of streams in <klass> this will probably
        # only match '*' in the template mapping:
        self.template = getGradeTemplate(rtype, klass)
        self.alltags = getTemplateTags(self.template)
        # Extract grade-entry tags, i.e. those matching <str>_<int>:
        gtags = {}      # {subject group -> [(unsorted) index<int>, ...]}
        for tag in self.alltags:
            try:
                _group, index = tag.split('_')
                group = _group.split('.')[-1]
                i = int(index)
            except:
                continue
            try:
                gtags[group].append(i)
            except:
                gtags[group] = [i]
        # Build a sorted mapping of index lists:
        #   {subject group -> [(reverse sorted) index<int>, ...]}
        # The reversal is for popping in correct order.
        self.sgroup2indexes = {group: sorted(gtags[group], reverse=True)
                for group in gtags}
#        print("\n??? self.alltags", self.alltags)
#        print("\n??? self.sgroup2indexes", self.sgroup2indexes)

        ### Sort the subject tags into ordered groups
        self.courses = CourseTables(schoolyear)
        subjects = self.courses.filterGrades(klass)
        # Build a mapping: {subject group -> [(ordered) sid, ...]}
        self.sgroup2sids = {}
        for group in self.sgroup2indexes:
            sidlist = []
            self.sgroup2sids[group] = sidlist
            # CONF.GRADES.ORDERING: {subject group -> [(ordered) sid, ...]}
            for sid in CONF.GRADES.ORDERING[group]:
                # Include only sids relevant for the klass.
                try:
                    del(subjects[sid])
                    sidlist.append(sid)
                except:
                    pass
        # Entries remaining in <subjects> are not covered in ORDERING.
        for sid in subjects:
            REPORT.Error(_UNGROUPED_SID, sid=sid, tfile=self.template.filename)


    def getTagmap(self, grades, pname, grademap='GRADES'):
        """Prepare tag mapping for substitution in the report template,
        for the pupil <pname>.
        <grades> is a mapping {sid -> grade}, or something similar which
        can be handled by <dict(grades)>.
        <grademap> is the name of a configuration file (in 'GRADES')
        providing a grade -> text mapping.
        Grouped subjects expected by the template get two entries:
        one for the subject name and one for the grade. They are allocated
        according to the numbered slots defined for the predefined ordering
        (config: GRADES/ORDERING).
        "Grade" entries whose tag begins with '_' and which are not covered
        by the data in GRADES/ORDERING are copied directly to the output
        mapping.
        Return a mapping {template tag -> replacement text}.
        """
        tagmap = {}                     # for the result
        g2text = CONF.GRADES[grademap]  # grade -> text representation
        # Copy the grade mapping, because it will be modified to keep
        # track of unused grade entries:
        gmap = dict(grades)     # this accepts a variety of input types
        for group, sidlist in self.sgroup2sids.items():
            # Copy the indexes because the list is modified here (<pop()>)
            indexes = self.sgroup2indexes[group].copy()
            for sid in sidlist:
                try:
                    g = gmap.pop(sid)
                except:
                    REPORT.Error(_MISSING_GRADE, pname=pname, sid=sid)
                    g = '?'
                if g == _INVALID:
                    continue
                try:
                    i = indexes.pop()
                except:
                    REPORT.Fail(_TOO_MANY_SUBJECTS, group=group,
                            pname=pname, sids=repr(sidlist),
                            template=self.template.filename)
                sname = self.courses.subjectName(sid).split('|')[0].rstrip()
                tagmap["%s_%d_N" % (group, i)] = sname
                g1 = g2text.get(g)
                if not g1:
                    REPORT.Error(_NO_MAPPED_GRADE, grade=g)
                    g1 = '?'
                tagmap["%s_%d" % (group, i)] = g1
            # Process superfluous indexes
            for i in indexes:
                tagmap["%s_%d_N" % (group, i)] = g2text.NONE
                tagmap["%s_%d" % (group, i)] = g2text.NONE
        # Report unused grade entries
        unused = []
        for sid, g in gmap.items():
            if g == _INVALID:
                continue
            if sid[0] == '_':
                tagmap[sid] = g
            else:
                unused.append("%s: %s" % (sid, g))
        if unused:
            REPORT.Error(_UNUSED_GRADES, pname=pname, grades="; ".join(unused))
        return tagmap




##################### Test functions
_testyear = 2016
def test_01 ():
    _term = '1'
    _date = '2016-01-29'
    for _klass, _pid in ('13', '200301'), ('12.RS', '200403'):
        klass = Klass(_klass)
        REPORT.Test("Reading basic grade data for class %s" % klass)
#TODO: This might not be the optimal location for this file.
        filepath = Paths.getYearPath(_testyear, 'FILE_GRADE_TABLE',
                    term=_term).replace('*', str(klass).replace('.', '-'))
        pgrades = readGradeTable(filepath)
        REPORT.Test(" ++ INFO: %s" % repr(pgrades.info))
        for pid, grades in pgrades.items():
            REPORT.Test("\n  -- %s: %s\n" % (pid, repr(grades)))

        REPORT.Test("\nReading template data for class %s" % klass)

        # Get the report type from the term and klass/stream
        _rtype = klass.match_map(CONF.GRADES.REPORT_TEMPLATES['_' + _term])
        gradedata = GradeReportData(_testyear, _rtype, klass)
        REPORT.Test("  Indexes:\n  %s" % repr(gradedata.sgroup2indexes))
        REPORT.Test("  Grade tags:\n  %s" % repr(gradedata.sgroup2sids))

        grademap = klass.match_map(CONF.MISC.GRADE_SCALE)
        REPORT.Test("\nTemplate grade map for pupil %s (using %s)" %
                (_pid, grademap))
        tagmap = gradedata.getTagmap(pgrades[_pid], "Pupil_%s" % _pid, grademap)
        REPORT.Test("  Grade tags:\n  %s" % repr(tagmap))

def test_02():
    from glob import glob
    files = glob(Paths.getYearPath(_testyear, 'FILE_GRADE_TABLE',
                term='*'))
    for filepath in files:
        pgrades = readGradeTable(filepath)
        grades2db(_testyear, pgrades)
