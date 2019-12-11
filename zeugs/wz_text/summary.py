#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_text/summary.py

Last updated:  2019-12-11

Prepare checklists of classes/subjects for the teachers.
Prepare checklists of subjects/teachers for the classes.

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

import os

import jinja2
from weasyprint import HTML, CSS

from wz_core.configuration import Paths, Dates
from wz_core.courses import CourseTables
from wz_compat.config import printSchoolYear

_NOTEMPLATE = "Vorlagedatei (Lehrer-Zeugniskontrolle) fehlt:\n  {path} "

def tSheets (schoolyear, manager, date):
    courses = CourseTables (schoolyear)
    tidmap = {}

    for klass in courses.classes ():
        if klass < '13':
            tmatrix = courses.teacherMatrix (klass)
            for pid, sid2tids in tmatrix.items ():
                for sid, tids in sid2tids.items ():
                    if tmatrix.sid2info [sid].NOTTEXT:
                        continue
                    if type (tids) == str:
                        tids = [tids]
                    for tid in tids:
                        try:
                            tmap = tidmap [tid]
                        except:
                            tidmap [tid] = {klass: {sid}}
                            continue
                        try:
                            tmap [klass].add (sid)
                        except:
                            tmap [klass] = {sid}

    noreports = []
    teachers = []
    for tid in courses.teacherData:
        lines = []
        tname = courses.teacherData.getTeacherName (tid)
        try:
            tmap = tidmap [tid]
        except:
            noreports.append (tname)
            continue
        for klass in sorted (tmap):
            for sid in tmap [klass]:
                sname = courses.subjectName (sid)
                lines.append ((klass, sname))
        teachers.append ((tname, lines))

    tpdir = Paths.getUserPath('DIR_TEXT_REPORT_TEMPLATES')
    templateLoader = jinja2.FileSystemLoader(searchpath=tpdir)
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
    tpfile = 'summary-teachers.html'
    try:
        template = templateEnv.get_template(tpfile)
    except:
        REPORT.Fail(_NOTEMPLATE, path=os.path.join(tpdir, tpfile))
    source = template.render(
            year = printSchoolYear(schoolyear),
            manager = manager,
            date = Dates.dateConv (date),
            teachers = teachers,
            noreports = noreports
        )
    html = HTML (string=source)
    pdfBytes = html.write_pdf()
    return pdfBytes



def ksSheets (schoolyear, manager, date):
    courses = CourseTables (schoolyear)
    tidmap = {tid: courses.teacherData.getTeacherName (tid)
            for tid in courses.teacherData}

    klasses = []
    for klass in courses.classes ():
        if klass >= '13':
            continue
        sidmap = {}
        tmatrix = courses.teacherMatrix (klass)
        for pid, sid2tids in tmatrix.items ():
            for sid, tids in sid2tids.items ():
                if tmatrix.sid2info [sid].NOTTEXT:
                    continue
                if type (tids) == str:
                    tids = [tids]
                for tid in tids:
                    try:
                        sidmap [sid].add (tid)
                    except:
                        sidmap [sid] = {tid}
        lines = []
        for sid, tids in sidmap.items ():
            sname = courses.subjectName (sid)
            for tid in tids:
                lines.append ((sname, tidmap [tid]))
        klasses.append ((klass, lines))

    tpdir = Paths.getUserPath('DIR_TEXT_REPORT_TEMPLATES')
    templateLoader = jinja2.FileSystemLoader(searchpath=tpdir)
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
    tpfile = 'summary-classes.html'
    try:
        template = templateEnv.get_template(tpfile)
    except:
        REPORT.Fail(_NOTEMPLATE, path=os.path.join(tpdir, tpfile))
    source = template.render(
            year = printSchoolYear(schoolyear),
            manager = manager,
            date = Dates.dateConv (date),
            klasses = klasses
        )
    html = HTML (string=source)
    pdfBytes = html.write_pdf()
    return pdfBytes



_year = 2016
_manager = "Anton Admin"
_date = '2016-06-22'
def test_01 ():
    pdfBytes = tSheets (_year, _manager, _date)
    fpath = Paths.getYearPath (_year, 'FILE_TEACHER_REPORT_LISTS')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Info ("Class and subject lists for each teacher:\n  {path}",
            path=fpath)

def test_02 ():
    pdfBytes = ksSheets (_year, _manager, _date)
    fpath = Paths.getYearPath (_year, 'FILE_CLASS_REPORT_LISTS')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Info ("Fach-Lehrer-Zuordnung der Klassen:\n  {path}",
            path=fpath)
