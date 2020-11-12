### python >= 3.7
# -*- coding: utf-8 -*-
"""
grades/gradetable.py - last updated 2020-11-11

Access grade data, read and build grade tables.

==============================
Copyright 2020 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

### Grade table header items
_SCHOOLYEAR = 'Schuljahr'
_CLASS = 'Klasse'
_TERM = 'Anlass'
_ISSUE_D = 'Ausgabedatum'      # or 'Ausstellungsdatum'?
_GRADES_D = 'Notendatum'
_TID = 'Lehrkraft'


### Messages
_NO_GRADES_ENTRY = "Keine Noten für Schüler {pid} zum {zum}"
_EXCESS_SUBJECTS = "Unerwartete Fachkürzel in der Notenliste: {sids}"
_TEACHER_MISMATCH = "Fach {sid}: Alte Note wurde von {tid0}," \
        " neue Note von {tid}"
_BAD_GRADE = "Ungültige Note im Fach {sid}: {g}"


#TODO:
# Title for grade tables
#_TITLE0 = "Noten"
#_TITLE = "Noten, bis {date}"
_TITLE2 = "Tabelle erstellt am {time}"
#_TTITLE = "Klausurnoten"


import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

import datetime
from fractions import Fraction

from core.db import DB
from core.base import str2list, Dates
from core.pupils import Pupils
from core.courses import Subjects
from tables.spreadsheet import Spreadsheet, DBtable
from tables.matrix import KlassMatrix
from local.base_config import DECIMAL_SEP
from local.grade_config import GradeBase, UNCHOSEN, NO_GRADE


class GradeTableError(Exception):
    pass


#TODO: What about unscheduled reports?
class TermGrade:
    """Manage the grade data for a term (etc.) and group.
    With old data (past reports), the entries in the GRADES table are
    primary as far as the pupils are concerned. The class, stream and
    pupil list can differ from the "current" state.
    For current (not yet issued) reports, the entries in the GRADES
    table should adapt to the current pupil data.
    """
    def __init__(self, schoolyear, term, group,
            with_composites = False, force_open = False):
        self.schoolyear = schoolyear
        self.term = term
        self.group = group
        ### Pupil data
        pupils = Pupils(schoolyear)
        # Needed here for pupil names, can use pupils.pid2name(pid)
        # Fetching the whole class may not be good enough, as it is vaguely
        # possible that a pupil has changed class.

        ### Subject data (for whole class)
        _courses = Subjects(schoolyear)
        self.klass, self.streams = Grades.group2klass_streams(group)
        self.sdata_list = _courses.grade_subjects(self.klass)

        # If the "term" refers to a special grade collection, allow the
        # data to be modified
        try:
            int(term)
        except ValueError:
            Grades.special_term(self)

        ### Collect rows
        self.grades_info = self.get_grade_info(schoolyear, term, group)
        self.gdata_list = []
        if (not force_open) and self._grades_closed():
            for gdata in Grades.forGroupTerm(schoolyear, term, group):
                # Get all the grades, possibly including composites.
                gdata.get_full_grades(self.sdata_list, with_composites)
                gdata.set_pupil_name(pupils.pid2name(gdata['PID']))
                self.gdata_list.append(gdata)
        else:
            date = self.grades_info['ISSUE_D']
            for pdata in pupils.classPupils(self.klass, date = date):
                if self.streams and (pdata['STREAM'] not in self.streams):
                    continue
                pname = pupils.pdata2name(pdata)
                try:
                    gdata = Grades.forPupil(schoolyear, term, pdata['PID'])
                except GradeTableError:
                    # No entry in database table
                    gdata = Grades.newPupil(schoolyear, TERM = term,
                            CLASS = pdata['CLASS'], STREAM = pdata['STREAM'],
                            PID = pdata['PID'], ISSUE_D = '*', GRADES_D = '*',
                            REPORT_TYPE = self.default_report_type(
                                    term, group))
                else:
                    # Check for changed pupil stream and class
                    changes = {}
                    if pdata['CLASS'] != gdata['CLASS']:
                        changes['CLASS'] = pdata['CLASS']
                    if pdata['STREAM'] != gdata['STREAM']:
                        changes['STREAM']  = pdata['STREAM']
                    if changes:
                        REPORT(_GROUP_CHANGE.format(
                                pname = pname,
                                delta = repr(changes)))
                        gdata.update(**changes)
                # Get all the grades, possibly including composites
                gdata.get_full_grades(self.sdata_list, with_composites)
                gdata.set_pupil_name(pname)
                self.gdata_list.append(gdata)
#
    def _grades_closed(self):
        idate = self.grades_info['ISSUE_D']
        return idate and Dates.today() > idate
#
    @staticmethod
    def default_report_type(term, group):
        for grp, rtype in Grades.term2group_rtype_list(term):
            if grp == group:
                return rtype
        raise Bug("No report type for term {term}, group {group}".format(
                term = term, group = group))
#
    @classmethod
    def get_grade_info(cls, schoolyear, term, group):
        """Fetch general information for the term/group.
        If necessary, initialize the entries.
        """
        kb = cls.info_keybase(term, group)
        ginfo = {}
        with DB(schoolyear) as dbconn:
            row = dbconn.select1('INFO', K = kb.format(field = 'ISSUE_D'))
            if row:
                ginfo['ISSUE_D'] = row['V']
                ginfo['GRADES_D'] = dbconn.select1('INFO',
                        K = kb.format(field = 'GRADES_D'))['V']
            else:
                # Initialize the information
                try:
                    date = dbconn.select1('INFO',
                            K = 'CALENDAR_TERM_%d' % (int(term) + 1))['V']
                except:
                    date = dbconn.select1('INFO',
                            K = 'CALENDAR_LAST_DAY')['V']
                else:
                    # Previous day, ensure that it is a weekday
                    td = datetime.timedelta(days = 1)
                    d = datetime.date.fromisoformat(date)
                    while True:
                        d -= td
                        if d.weekday() < 5:
                            date = d.isoformat()
                            break
                kb = cls.info_keybase(term, group)
                ginfo = {'ISSUE_D': date, 'GRADES_D': None}
                for key, value in ginfo.items():
                    dbconn.updateOrAdd('INFO',
                            {'K': kb.format(field = key), 'V': value},
                            K = key)
        return ginfo
#
    @staticmethod
    def info_keybase(term, group):
        """Return the base for the INFO table key.
        """
        return 'GRADES_%s.%s_{field}' % (group, term)

###

class Grades(GradeBase):
    """A <Grades> instance manages the set of grades in the database for
    a pupil and "term". It is primarily used for fetching the grades
    from the database.
    There are a few static/class methods for accessing the appropriate
    entries, for individual pupils or for groups.
    """
    @classmethod
    def forGroupTerm(cls, schoolyear, term, group):
        """Return a list of <Grades> instances for the given group and term.
        This is not intended for 'Single' reports.
        """
        klass, streams = cls.group2klass_streams(group)
        with DB(schoolyear) as dbconn:
            rows = dbconn.select('GRADES', CLASS = klass, TERM = term)
        if streams:
            return [cls(schoolyear, row) for row in rows
                    if row['STREAM'] in streams]
        else:
            return [cls(schoolyear, row) for row in rows]
#
    @staticmethod
    def list_pupil(schoolyear, pid):
        """List all grade entries for the given pupil.
        """
        with DB(schoolyear) as dbconn:
            return list(dbconn.select('GRADES', PID = pid))
#
#TODO: handling of 'S' reports not yet ok!
    @classmethod
    def forPupil(cls, schoolyear, term_or_date, pid):
        """Return <Grades> instance for the given pupil and term. If
        an unscheduled report is sought, <term_or_date> should be the
        date (YYYY-MM-DD) of the report.
        """
        # Determine whether <term_or_date> is a date
        for c, t in cls.categories():
            if c == term_or_date:
                # not a date
                with DB(schoolyear) as dbconn:
                    row = dbconn.select1('GRADES', PID = pid,
                            TERM = term_or_date)
                if not row:
                    raise GradeTableError(_NO_GRADES_ENTRY.format(
                            pid = pid, zum = t))
                break
        else:
            # date
            with DB(schoolyear) as dbconn:
                row = dbconn.select1('GRADES', PID = pid, TERM = 'S',
                        ISSUE_D = term_or_date)
            if not row:
                raise GradeTableError(_NO_GRADES_ENTRY.format(
                        pid = pid, zum = term_or_date))
        return cls(schoolyear, row)
#
    @classmethod
    def newPupil(cls, schoolyear, **fields):
        """Add a new grade entry for the given term and pupil.
        """
#TODO: What about "unscheduled" reports?
        with DB(schoolyear) as dbconn:
            rowid = dbconn.addEntry('GRADES', fields)
            row = dbconn.select1('GRADES', id = rowid)
        return cls(schoolyear, row)
#
    def __init__(self, schoolyear, grade_row):
        self.schoolyear = schoolyear
        self.grade_row = grade_row
        super().__init__(grade_row)
        self._grades = None
        self._sid2tid = None
#
    def __getitem__(self, key):
        return self.grade_row[key]
#
    def update(self, **changes):
        """Update the fields of the grade entry.
        """
        with DB(self.schoolyear) as dbconn:
            rowid = self.grade_row['id']
            dbconn.updateOrAdd('GRADES', changes, update_only = True,
                    id = rowid)
            row = dbconn.select1('GRADES', id = rowid)
        # Reinitialize the instance
        self.__init__(self.schoolyear, row)
#
    def get_raw_grades(self):
        """Return the mapping {sid -> grade} for the "real" grades.
        In addition, the call to <self.filter_grade> also enters numerical
        grades (as integers) into the mapping <self.i_grade>:
            {sid -> grade value}.
        Non-numerical grades are not entered into <self.i_grade>.
        """
        if self._grades == None:
            self._grades = {}
            self._sid2tid = {}
            self.empty_grades = []
            for sg in str2list(self.grade_row['GRADES']):
                sid, g, tid = sg.split(':')
                self._grades[sid] = self.filter_grade(sid, g)
                self._sid2tid[sid] = tid
        return self._grades
#
    def sid2tid(self, sid):
        """Return the tag for the teacher who graded the given subject.
        If there is no entry for this subject, return <None>.
        """
        if self._sid2tid == None:
            self.grades()   # Ensure cache is loaded
        return self._sid2tid.get(sid)
#
    def get_full_grades(self, sdata_list, with_composites = False):
        """Return the full grade mapping including all subjects in
        <sdata_list>, a list of <SubjectData> instances. If
        <with_composites> is true, also the "composite" subjects will be
        processed and included.
        All subjects relevant for grades in the class are included.
        A <SubjectData> tuple has the following fields:
            sid: the subject tag;
            tids: a list of teacher ids, empty if the subject is a composite;
            composite: if the subject is a component, this will be the
                sid of its composite; if the subject is a composite, this
                will be the list of components, each is a tuple
                (sid, weight); otherwise the field is empty;
            report_groups: a list of tags representing a particular block
                of grades in the report template;
            name: the full name of the subject.
        The result is also saved as <self.full_grades>.
        """
        raw_grades = self.get_raw_grades()
        # Add subjects missing from GRADES field, process composites
        grades = {}
        for sdata in sdata_list:
            sid = sdata.sid
            if sdata.tids:
                g = raw_grades.pop(sid, '')
                grades[sid] = g
            elif with_composites:
                # A composite subject, calculate the component-average,
                # if possible. If there are no numeric grades, choose
                # NO_GRADE, unless all components are UNCHOSEN (in
                # which case also the composite will be UNCHOSEN).
                asum = 0
                ai = 0
                non_grade = UNCHOSEN
                for csid, weight in sdata.composite:
                    try:
                        gi = self.i_grade[csid]
                    except KeyError:
                        if raw_grades.get(csid) != UNCHOSEN:
                            non_grade = NO_GRADE
                    else:
                        ai += weight
                        asum += gi * weight
                if ai:
                    g = Frac(asum, ai).round()
                    grades[sid] = self.grade_format(g)
                    self.i_grade[sid] = int(g)
                else:
                    grades[sid] = non_grade
        if raw_grades:
            REPORT(_EXCESS_SUBJECTS.format(sids = ', '.join(raw_grades)))
        self.full_grades = grades
        return grades
#
    def set_pupil_name(self, name):
        """The pupil name can be set externally. This avoids having this
        module deal with pupil data.
        """
        self._pname = name
#
    def pupil_name(self):
        return self._pname

###

class Frac(Fraction):
    """A <Fraction> subclass with custom <truncate> and <round> methods
    returning strings.
    """
    def truncate(self, decimal_places = 0):
        if not decimal_places:
            return str(int(self))
        v = int(self * 10**decimal_places)
        sval = ("{:0%dd}" % (decimal_places+1)).format(v)
        return (sval[:-decimal_places] + DECIMAL_SEP + sval[-decimal_places:])
#
    def round(self, decimal_places = 0):
        f = Fraction(1,2) if self >= 0 else Fraction(-1, 2)
        if not decimal_places:
            return str(int(self + f))
        v = int(self * 10**decimal_places + f)
        sval = ("{:0%dd}" % (decimal_places+1)).format(v)
        return (sval[:-decimal_places] + DECIMAL_SEP + sval[-decimal_places:])

###

class GradeTable(dict):
    def __init__(self, filepath, tid = None):
        """Read the header info and pupils' grades from the given table file.
        The "spreadsheet" module is used as backend so .ods, .xlsx and .tsv
        formats are possible. The filename may be passed without extension –
        <Spreadsheet> then looks for a file with a suitable extension.
        <Spreadsheet> also supports in-memory binary streams (io.BytesIO)
        with attribute 'filename' (so that the type-extension can be read).
        The class instance is a mapping: {pid -> {sid -> grade}}.
        Additional information is available as attributes:
            <tid>: teacher-id
            <klass>: school-class
            <term>: school-term
            <schoolyear>: school-year
            <issue_d>: date of issue
            <grades_d>: date of grade finalization
            <subjects>: [sid, ...]
            <name>: {pid -> (short) name}
            <stream>: {pid -> stream}
        Most of these are taken from the <info> mapping, which should
        contain the keys:
            'SCHOOLYEAR', 'CLASS', 'TERM', 'ISSUE_D', 'GRADES_D'
        """
        super().__init__()
        ss = Spreadsheet(filepath)
        dbt = ss.dbTable()
        info = {row[0]: row[1] for row in dbt.info if row[0]}
        self.tid = tid
        self.klass = info.get(_CLASS)
        self.term = GradeBase.text2category(info.get(_TERM))
        self.schoolyear = info.get(_SCHOOLYEAR)
        self.issue_d = info.get(_ISSUE_D)
        self.grades_d = info.get(_GRADES_D)
        sid2col = []
        col = 0
        for f in dbt.fieldnames():
            if col > 2:
                if f[0] != '$':
                    # This should be a subject tag
                    sid2col.append((f, col))
            col += 1
        self.name = {}
        self.stream = {}
        for row in dbt:
            pid = row[0]
            if pid:
                self.name[pid] = row[1]
                self.stream[pid] = row[2]
                self[pid] = {sid: row[col] for sid, col in sid2col}
        self.subjects = [sid for sid, col in sid2col]

###

def makeBasicGradeTable(schoolyear, term, group,
        empty = False, force_open = False):
    """Build a basic pupil/subject table containing the existing grades
    (initially empty).
    <term> is a string representing a valid "term".
    <group> is a grade-report group as specified in
    <GradeBase._REPORT_GROUPS>.
    If <empty> is true, the table will be empty even if there are
    existing grades.
    <force_open> is only for testing purposes, it causes old data sets
    to be treated as current (still "open").
    """
    # Get data set.
    termGrade = TermGrade(schoolyear, term, group, force_open = force_open)

    # Get template file
    try:
        template = GradeBase.GRADE_TABLES[group]
    except KeyError:
        template = GradeBase.GRADE_TABLES['*']
    template_path = os.path.join(RESOURCES, 'templates',
                *template.split('/'))
    table = KlassMatrix(template_path)

    # Set title line
#    table.setTitle("???")
    table.setTitle2(_TITLE2.format(time = datetime.datetime.now().isoformat(
                sep=' ', timespec='minutes')))

    # Translate and enter general info
    info = (
        (_SCHOOLYEAR,    str(schoolyear)),
        (_CLASS,         termGrade.klass),
        (_TERM,          GradeBase.category2text(term)),
        (_GRADES_D,      termGrade.grades_info['GRADES_D']),
        (_ISSUE_D,       termGrade.grades_info['ISSUE_D'])
    )
    table.setInfo(info)

    ### Manage subjects
    sdata = [(sd.sid, sd.name) for sd in termGrade.sdata_list if sd.tids]
#    print ("???", sdata)
    # Go through the template columns and check if they are needed:
    sidcol = []
    col = 0
    rowix = table.row0()    # index of header row
    for sid, sname in sdata:
        # Add subject
        col = table.nextcol()
        sidcol.append((sid, col))
        table.write(rowix, col, sid)
        table.write(rowix + 1, col, sname)
    # Enforce minimum number of columns
    while col < 18:
        col = table.nextcol()
        table.write(rowix, col, None)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    for gdata in termGrade.gdata_list:
        row = table.nextrow()
        pid = gdata['PID']
        table.write(row, 0, pid)
        table.write(row, 1, gdata.pupil_name())
        table.write(row, 2, gdata['STREAM'])
        if not empty:
            grades = gdata.full_grades
            for sid, col in sidcol:
                g = grades.get(sid)
                if g:
                    table.write(row, col, g)
    # Delete excess rows
    row = table.nextrow()
    table.delEndRows(row)

    ### Save file
    table.protectSheet()
    return table.save()

###

def update_grades(schoolyear, term, pid, tid = None, grades = None, **fields):
    """Compare the existing GRADES entry with the data passed in.
    Update the database entry if there is a (permissible) change.
    The GRADES entry is keyed by <pid> and <term>.
    """
#TODO
    gdata = Grades.forPupil(schoolyear, term, pid)
    gdata.get_full_grades()

    if grades:
        # Compare the contained grades with those in gdata.full_grades.
        # Check that the teacher is permitted to perform the update.
        for sid, g in gdata.full_grade.items():
            try:
                g1 = grades[sid]
                if g1 not in gdata.valid_grades:
                    raise GradeTableError(_BAD_GRADE.format(
                            sid = sid, g = g1))
            except KeyError:
                continue
            if tid:
                tid0 = gdata.sid2tid(sid)
                if tid0 and tid0 != tid:
                    raise GradeTableError(_TEACHER_MISMATCH.format(
                            sid = sid, tid0 = tid0, tid = tid))
            if g1 != g:
                gdata.full_grade[sid] = g
#TODO: GradeBase.set_tid(sid, tid)
                gdata.set_tid(sid, tid)
#TODO: build the new grades entry. Use (gdata.sid2tid(sid) or '-') for the
# tid part.
#        newgrades = ...


    if fields:
        # Only the administrator may perform these updates?
        pass

# This is old code:
    gt = GradeTable(os.path.join(fpath, f))
    print ("\n*** READING: %s.%s, class %s, teacher: %s" % (
            gt.schoolyear, gt.term or '-',
            gt.klass, gt.tid or '-'))
    for pid, grades in gt.items():
        print(" ::: %s (%s):" % (gt.name[pid], gt.stream[pid]), grades)
        # <grades> is a mapping: {sid -> grade}
        glist = ['%s:%s:%s' % (sid, g, gt.tid or '-')
                for sid, g in grades.items() if g]

        # The GRADES table has the fields:
        #   (id – Integer, primary key), PID, CLASS, STREAM,
        #   TERM, GRADES, REPORT_TYPE, ISSUE_D, GRADES_D,
        #   QUALI, COMMENT
        valmap = {
            'PID': pid,
            'CLASS': gt.klass,
            'STREAM': gt.stream[pid],
            'TERM': gt.term,
            'GRADES': ','.join(glist)
        }

# At some point the class, stream and pupil subject choices should be checked,
# but maybe not here?

        # Enter into GRADES table
        with dbconn:
            dbconn.updateOrAdd('GRADES', valmap,
                    PID = pid, TERM = gt.term)




#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')
    _schoolyear = 2016

#    if True:
    if False:
        print("NEW ROW:", Grades.newPupil(_schoolyear, TERM = 'S1',
                CLASS = '12', STREAM = 'Gym', PID = '200888'))

        with DB(_schoolyear) as dbconn:
            row = dbconn.select1('GRADES', PID = '200888', TERM = 'S1')
        g = Grades(_schoolyear, row)

        g.update(STREAM = 'RS')
        print("CHANGED TO:", dict(g.grade_row))

        with DB(_schoolyear) as dbconn:
            dbconn.deleteEntry ('GRADES', id = g['id'])

#    if True:
    if False:
        _term = '2'
        _group = '12.R'
        print("\n ****", _group)
        term_grade = TermGrade(_schoolyear, _term, _group)
        for _gdata in term_grade.gdata_list:
            print("\nid:", _gdata['id'])
            print(":::", _gdata['PID'])
            print(_gdata.full_grades)

        _group = '12.G'
        print("\n ****", _group)
        term_grade = TermGrade(_schoolyear, _term, _group, with_composites = True)
        for _gdata in term_grade.gdata_list:
            print("\nid:", _gdata['id'])
            print(":::", _gdata['PID'])
            print(_gdata.full_grades)

        _group = '13'
        print("\n ****", _group)
        term_grade = TermGrade(_schoolyear, 'A', _group, force_open = True)
        for _gdata in term_grade.gdata_list:
            print("\nid:", _gdata['id'])
            print(":::", _gdata['PID'])
            print(_gdata.full_grades)

    if True:
#    if False:
#        print("\nGRADES 10/2:")
#        gt = GradeTable(os.path.join(DATA, 'testing', 'Noten_2', 'Noten_10'))
        print("\nGRADES 11.G/2:")
        gt = GradeTable(os.path.join(DATA, 'testing', 'Noten_2', 'Noten_11.G'))
        print("   TID:", gt.tid)
        print("   CLASS:", gt.klass)
        print("   TERM:", gt.term)
        print("   SCHOOL-YEAR:", gt.schoolyear)
        print("   ISSUE_D:", gt.issue_d)
        print("   GRADES_D:", gt.grades_d)

        print("\nSUBJECTS:", gt.subjects)
        print("\nGRADES:")
        for pid, grades in gt.items():
            print(" ::: %s (%s):" % (gt.name[pid], gt.stream[pid]), grades)

    if True:
        print("\n=============== Make Grade Table 13/1 ===============")
        xlsx_bytes = makeBasicGradeTable(_schoolyear, '1', '13',
                empty = True, force_open = True)
        dpath = os.path.join(DATA, 'testing', 'tmp')
        os.makedirs(dpath, exist_ok = True)
        filepath = os.path.join(dpath, 'Grades-13-1.xlsx')
        with open(filepath, 'wb') as fh:
            fh.write(xlsx_bytes)
        print(" --> %s" % filepath)


    quit(0)

    from core.db import DB
    _year = 2016
    dbconn = DB(_year)

    for folder in 'Noten_1', 'Noten_2':
        fpath = os.path.join(DATA, 'testing', folder)
        for f in os.listdir(fpath):
            if f.rsplit('.', 1)[-1] in ('xlsx', 'ods', 'tsv'):
                gt = GradeTable(os.path.join(fpath, f))
                print ("\n*** READING: %s.%s, class %s, teacher: %s" % (
                        gt.schoolyear, gt.term or '-',
                        gt.klass, gt.tid or '-'))
                for pid, grades in gt.items():
                    print(" ::: %s (%s):" % (gt.name[pid], gt.stream[pid]), grades)
                    # <grades> is a mapping: {sid -> grade}
                    glist = ['%s:%s:%s' % (sid, g, gt.tid or '-')
                            for sid, g in grades.items() if g]

                    # The GRADES table has the fields:
                    #   (id – Integer, primary key), PID, CLASS, STREAM,
                    #   TERM, GRADES, REPORT_TYPE, ISSUE_D, GRADES_D,
                    #   QUALI, COMMENT
                    valmap = {
                        'PID': pid,
                        'CLASS': gt.klass,
                        'STREAM': gt.stream[pid],
                        'TERM': gt.term,
                        'GRADES': ','.join(glist)
                    }

# At some point the class, stream and pupil subject choices should be checked,
# but maybe not here?

                    # Enter into GRADES table
                    with dbconn:
                        dbconn.updateOrAdd('GRADES', valmap,
                                PID = pid, TERM = gt.term)
