# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/grade_classes.py

Last updated:  2020-03-14

For which school-classes and streams are grade reports possible?


=+LICENCE=============================
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

=-LICENCE========================================
"""

# Messages
_INVALID_GROUP = "Ungültige Zeugnis-Gruppe für das {term}. Halbjahr: {group}"
_WRONG_YEAR = "Falsches Schuljahr: '{year}'"
_INVALID_YEAR = "Ungültiges Schuljahr: '{year}'"
_INVALID_KLASS = "Ungültige Klasse: '{klass}'"
_MISSING_PUPIL = "Schüler {pname} ist nicht in der Kurswahltabelle"
_UNKNOWN_PUPIL = "Unbekannter Schüler: {pid}"
_NEWCHOICES = "[{year}] Kurswahl für Klasse {klass} aktualisiert."
_NOPUPILS = "Keine Schüler"
_NSUBJECTS = "Für {pname} sind nicht genau 8 Fächer markiert"
_ABI_CHOICES = "{pname} muss genau 8 Fächer für das Abitur wählen"


from wz_core.db import DB
from wz_core.configuration import Paths
from wz_core.pupils import Klass, Pupils
from wz_core.courses import CourseTables
from wz_table.dbtable import readPSMatrix
from wz_table.matrix import KlassMatrix


def gradeGroups(term):
    return g2groups[term]

g2groups = {
# Use <Klass> to normalise multi-stream groups
## 1. Halbjahr
    "1": [str(Klass(k)) for k in
            ("13", "12.Gym", "12.RS-HS", "11.Gym", "11.RS-HS")],

## 2. Halbjahr
    "2": [str(Klass(k)) for k in
            ("13", "12.Gym", "12.RS-HS", "11.Gym", "11.RS-HS", "10")],

## Einzelzeugnisse: alle Großklassen ab der 5.
    "X": ["%02d" % n for n in range(13, 4, -1)]
}


def setDateOfIssue(schoolyear, term, klass, date):
    if str(klass) not in gradeGroups(term):
        REPORT.Fail(_INVALID_GROUP, term = term, group = klass)
    streams = klass.streams or klass.klassStreams(schoolyear)
    for s in streams:
        g = klass.klass + '.' + s
        DB(schoolyear).setInfo('GRADE_DATE_%s_%s' % (term, g), date)


def getDateOfIssue(schoolyear, term, klass):
    db = DB(schoolyear)
    if klass.stream:
        return db.getInfo('GRADE_DATE_%s_%s' % (term, klass))
    group = str(klass)
    if group in gradeGroups(term):
        if klass.streams:
            return db.getInfo('GRADE_DATE_%s_%s' % (term,
                    klass.klass + '.' + klass.streams[0]))
        return db.getInfo('GRADE_DATE_%s_%s' % (term,
                    klass.klass + '.' + klass.klassStreams(schoolyear)[0]))
    REPORT.Fail(_INVALID_GROUP, term = term, group = group)



def abi_sids(schoolyear, pid, report = True):
    row = DB(schoolyear).select1('ABI_SUBJECTS', PID = pid)
    try:
        choices = row['SUBJECTS'].split(',')
        if len(choices) == 8:
            return choices
    except:
        pass
    if report:
        REPORT.Fail(_ABI_CHOICES, pname = Pupils.pid2name(schoolyear, pid))
    return None



def choiceTable(schoolyear, klass):
    """Build a subject choice table for the given school-class.
    <klass> is a the class name.
    Unless the school-class has changed, existing choices will be retained.
     """
    ks = Klass(klass)
    pupils = Pupils(schoolyear)
    try:
        if klass.startswith('12') or klass.startswith('13'):
            plist = pupils.classPupils(ks)
            if not plist:
                raise ValueError
        else:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, klass=klass)
    template = Paths.getUserPath('FILE_SUBJECT_CHOICE_TEMPLATE')
    table = KlassMatrix(template)
    # Title already set in template:
    #table.setTitle("Kurswahl")

    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass),
    )
    table.setInfo(info)

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(ks, filter_ = 'GRADE')
    # <table.headers> is a list of cell values in the header row.
    rsid = table.rowindex - 1       # row index for sid
    rsname = table.rowindex         # row index for subject name
    # Go through the template columns and check if they are needed:
    sid2col = {}        # map sid -> column index
    for sid in sid2tlist:
        try:
            s, tag = sid.rsplit('_', 1)
            if s:
                # Don't include "components" of "composite" subjects
                continue
        except ValueError:
            pass
        sname = courses.subjectName(sid)
        # Add subject
        col = table.nextcol()
        table.write(rsid, col, sid)
        sid2col[sid] = col
        table.write(rsname, col, sname)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    # Go through all pids (with stream 'Gym')
    p2choices = {}
    for pdata in plist:
        if pdata['STREAM'] != 'Gym':
            continue
        pid = pdata['PID']
        pname = pdata.name()
        choices = abi_sids(schoolyear, pid, report = False)
        row = table.nextrow()
        table.write(row, 0, pid)
        table.write(row, 1, pname)
        table.write(row, 2, pdata['STREAM'])
        for sid, col in sid2col.items():
            try:
                if sid in choices:
                    table.write(row, col, 'X')
            except:
                pass
    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()



def choices2db(schoolyear, filepath):
    """Enter the choices from the given table into the database.
    <schoolyear> is checked against the value in the info part of the
    table (table.info['SCHOOLYEAR']).
    """
    table = readPSMatrix(filepath)
    # Check school-year
    try:
        y = table.info.get('SCHOOLYEAR', '–––')
        yn = int(y)
    except ValueError:
        REPORT.Fail(_INVALID_YEAR, val=y)
    if yn != schoolyear:
        REPORT.Fail(_WRONG_YEAR, year=y)
    # Check klass
    klass = Klass(table.info.get('CLASS', '–––'))
    # Check validity
    pupils = Pupils(schoolyear)
    try:
        if klass.klass.startswith('12') or klass.klass.startswith('13'):
            plist = pupils.classPupils(klass)
            if not plist:
                raise ValueError
        else:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, klass=klass)
    # Go through all pids (with stream 'Gym')
    p2choices = {}
    for pdata in plist:
        if pdata['STREAM'] != 'Gym':
            continue
        pid = pdata['PID']
        try:
            p2choices[pid] = table.pop(pid)
        except KeyError:
            # This pupil is not in the choice table
            REPORT.Fail(_MISSING_PUPIL, pname=pdata.name())
    # Anything left unhandled in <table>?
    for pid in table:
        REPORT.Error(_UNKNOWN_PUPIL, pid=pid)

    # Now enter to database.
    # To recognize new subjects in the subject matrix, also non-chosen
    # subjects must be included.
    if p2choices:
        allsids = table.sids
        db = DB(schoolyear)
        for pid, smap in p2choices.items():
            slist = [sid for sid in table.sids if smap.get(sid)]
            if len(slist) != 8:
                REPORT.Fail(_NSUBJECTS, pname = plist.pidmap[pid].name())
            cstring = ','.join(slist)
            db.updateOrAdd('ABI_SUBJECTS',
                    {   'PID': pid,
                        'SUBJECTS': cstring
                    },
                    PID=pid
            )
        REPORT.Info(_NEWCHOICES, klass=klass, year=schoolyear)
    else:
        REPORT.Warn(_NOPUPILS)



##################### Test functions
_testyear = 2016

def test_01():
    for key in g2groups:
        REPORT.Test("\n Term %s: %s" % (key, repr(gradeGroups(key))))

def test_02():
    for _klass in ('13', '12'):
        filepath0 = Paths.getYearPath(_testyear, 'FILE_SUBJECT_CHOICE_TABLE')
        filepath = filepath0.replace('*', _klass)
        choices2db(_testyear, filepath)

def test_03():
    _klass = '12'
    bytefile = choiceTable(_testyear, _klass)
    filepath = Paths.getYearPath(_testyear, 'FILE_SUBJECT_CHOICE_NEW',
            make=-1).replace('*', _klass) + '.xlsx'
    with open(filepath, 'wb') as fh:
        fh.write(bytefile)
    REPORT.Test(" --> %s" % filepath)
