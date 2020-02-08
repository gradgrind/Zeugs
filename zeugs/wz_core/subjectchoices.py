# python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_core/subjectchoices.py - last updated 2020-02-08

Create subject choice tables.

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

_NEWCHOICES = "[{year}] Kurswahl für Klasse {klass} aktualisiert."
_MISSING_SUBJECT_CHOICE = "Fach fehlt in Kurswahl-Tabelle für Klasse {klass}: {sid}"
_REMOVED_SUBJECT_CHOICE = "Unerwartetes Fach in Kurswahl-Tabelle für Klasse {klass}: {sid}"
_CHANGED_KLASS = ("Klassenwechsel des Schülers {pid}: {old} -> {new}.\n"
        "  Die Kurswahl-Tabelle muss neu erstellt werden")

from collections import OrderedDict

from .configuration import Paths
from .pupils import Pupils, Klass
from .courses import CourseTables
from .db import DB
from wz_table.matrix import KlassMatrix
from wz_table.dbtable import readPSMatrix


def choiceTable(schoolyear, klass):
    """Build a subject choice table for the given school-class.
    <klass> is a <Klass> instance.
    Unless the school-class has changed, existing choices will be retained.
     """
    template = Paths.getUserPath('FILE_SUBJECT_CHOICE_TEMPLATE')
    table = KlassMatrix(template)
    # Title already set in template:
    #table.setTitle("Kurswahl")

    # "Translation" of info items:
    kmap = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
    info = (
        (kmap['SCHOOLYEAR'], str(schoolyear)),
        (kmap['CLASS'], klass.klass),
    )
    table.setInfo(info)

    ### Manage subjects
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass)
    # <table.headers> is a list of cell values in the header row.
    rsid = table.rowindex - 1       # row index for sid
    rsname = table.rowindex         # row index for subject name
    # Go through the template columns and check if they are needed:
    sid2col = {}        # map sid -> column index
    for sid in sid2tlist:
        if sid[0] != '_':
            sname = courses.subjectName(sid)
            # Add subject
            col = table.nextcol()
            table.write(rsid, col, sid)
            sid2col[sid] = col
            table.write(rsname, col, sname)
    # Delete excess columns
    table.delEndCols(col + 1)

    ### Add pupils
    db = DB(schoolyear)
    pupils = Pupils(schoolyear)
    for pdata in pupils.classPupils(klass):
        pid = pdata['PID']
        pname = pdata.name()
        choices = db.select1('CHOICES', PID=pid)
        if choices:
            if choices['CLASS'] == klass.klass:
                choices = choices2map(choices['CHOICES'])
            else:
                choices = None
                REPORT.Warning(_CHANGED_KLASS, pname=pname,
                        new=klass.klass, old=choices['CLASS'])
        row = table.nextrow()
        table.write(row, 0, pid)
        table.write(row, 1, pname)
        table.write(row, 2, pdata['STREAM'])
        for sid, col in sid2col.items():
            try:
                val = choices[sid]
            except:
                val = '?'
            table.write(row, col, val)
    # Delete excess rows
    table.delEndRows(row + 1)

    ### Save file
    table.protectSheet()
    return table.save()



def choices2db(schoolyear, table):
    """Enter the choices from the given table into the database.
    <schoolyear> is checked against the value in the info part of the
    table (table.info['SCHOOLYEAR']).
    """
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
        plist = pupils.classPupils(klass)
        if not plist:
            raise ValueError
    except:
        REPORT.Fail(_INVALID_KLASS, klass=klass)
    # Go through all pids
    p2choices = {}
    p2stream = {}
    for pdata in plist:
        pid = pdata['PID']
        try:
            p2choices[pid] = table.pop(pid)
        except KeyError:
            # This pupil is not in the choice table
            REPORT.Fail(_MISSING_PUPIL, pname=pdata.name())
        p2stream[pid] = pdata['STREAM']
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
            cstring = ';'.join([sid + '=' + (smap.get(sid) or '')
                    for sid in allsids])
#            print("$$$", pid, cstring)
#            continue
            db.updateOrAdd('CHOICES',
                    {   'CLASS': klass.klass,
                        'PID': pid,
                        'CHOICES': cstring
                    },
                    PID=pid
            )
        REPORT.Info(_NEWCHOICES, klass=klass, year=schoolyear)
    else:
        REPORT.Warn(_NOPUPILS)



def pupilSubjects(schoolyear, pid, TEXT=False, GRADE=False):
    """Return a subject-teacher mapping for all subjects relevant for
    this pupil (in the subject table):
        {[ordered] sid -> <TeacherList> instance}
    If <TEXT> is true, return subjects for text reports.
    If <GRADE> is true, return subjects for grade reports.
    Otherwise don't filter at all.
    """
    pupils = Pupils(schoolyear)
    pdata = pupils.pupil(pid)
    klass = pdata['CLASS']
    courses = CourseTables(schoolyear)
    sidmap = courses.classSubjects(Klass(klass))
#TODO: should <courses> be cached? Or should the subject
# table be in the db?

    ok = True   # flag to catch unrecoverable errors
    db = DB(schoolyear)
    choices = db.select1('CHOICES', PID=pid)
    if choices:
        if choices['CLASS'] != klass:
            REPORT.Error(_CHANGED_KLASS, pname=pdata.name(),
                    new=klass, old=choices['CLASS'])
            return None
        cmap = choices2map(choices['CHOICES'])
        _cmap = cmap.copy()
        smap = OrderedDict()
        for sid, tlist in sidmap.items():
            try:
                if _cmap.pop(sid):
                    smap[sid] = tlist
            except:
                REPORT.Error(_MISSING_SUBJECT_CHOICE, klass=klass, sid=sid)
                ok = False
        # Check for removed subjects
        if _cmap:
            for sid in _cmap:
                REPORT.Warning(_REMOVED_SUBJECT_CHOICE, klass=klass, sid=sid)
                # Actually remove the subject
                del(cmap[sid])
            # Rewrite the db entry
            cstring = ';'.join([sid + '=' + val
                    for sid, val in cmap.items()])
            db.update ('CHOICES', 'CHOICES', cstring, PID=pid)
        if not ok:
            return None
    else:
        ## No choice table.
        smap = sidmap
    # Filter the sid mapping for GRADE / TEXT
    sidmap = OrderedDict()
    for sid, val in smap.items():
        if GRADE and not val.GRADE:
            continue
        if TEXT and not val.TEXT:
            continue
        sidmap[sid] = val
    return sidmap
#TODO: Might want to redirect to choice editor if failed?



def choices2map(cstring):
    """Convert a choices string from the database to a mapping:
        {sid -> choice}
    """
    try:
        choices = {}
        for item in cstring.split(';'):
            k, v = item.split('=')
            choices[k.strip()] = v.strip()
        return choices
    except:
        if cstring:
            raise ValueError
        # There is an entry, but no data
        return None




##################### Test functions
_testyear = 2016
def test_01():
    klass = Klass('13') # Only full classes
    bytefile = choiceTable(_testyear, klass)
    filepath = Paths.getYearPath(_testyear, 'FILE_SUBJECT_CHOICE_NEW',
            make=-1).replace('*', str(klass)) + '.xlsx'
    with open(filepath, 'wb') as fh:
        fh.write(bytefile)
    REPORT.Test(" --> %s" % filepath)

def test_02():
    klass = Klass('13')
    filepath0 = Paths.getYearPath(_testyear, 'FILE_SUBJECT_CHOICE_TABLE')
    filepath = filepath0.replace('*', str(klass))
    table = readPSMatrix(filepath)
    choices2db(_testyear, table)

def test_03():
    _klass = 13
    _pid='200305'
    p2tlist = pupilSubjects(_testyear, _pid, GRADE=True)
    print(_klass, _pid, "(GRADE)-->", p2tlist)
    p2tlist = pupilSubjects(_testyear, _pid, TEXT=True)
    print(_klass, _pid, "(TEXT)-->", p2tlist)
