### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_text/summary.py

Last updated:  2020-06-07

Prepare checklists of classes/subjects for the teachers.
Prepare checklists of subjects/teachers for the classes.

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

_nn = 'nn'  # Unknown teacher id

import os

import jinja2
from weasyprint import HTML, CSS

from wz_core.configuration import Paths, Dates
from wz_core.courses import CourseTables
from wz_core.pupils import Klass
from wz_compat.config import printSchoolYear

_NOTEMPLATE = "Vorlagedatei (Lehrer-Zeugniskontrolle) fehlt:\n  {path} "


#TODO: extract a basic teacher->data function and put it in CourseTables
# (as with ksSheets, below).
def tSheets (schoolyear, manager, date):
    courses = CourseTables (schoolyear)
    tidmap = {}
    for k in courses.classes ():
        klass = Klass(k)
        sid2tids = courses.classSubjects(klass, 'TEXT')
        for sid, tids in sid2tids.items ():
            if tids.TEXT:
                if not tids:
                    tids = [_nn]
                for tid in tids:
                    try:
                        tmap = tidmap [tid]
                    except:
                        tidmap [tid] = {klass.klass: {sid}}
                        continue
                    try:
                        tmap [klass.klass].add (sid)
                    except:
                        tmap [klass.klass] = {sid}

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
        for k in sorted (tmap):
            for sid in tmap [k]:
                sname = courses.subjectName (sid)
                lines.append ((k, sname))
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
    """Prepare checklists of subjects/teachers for the classes.
    """
    klasses = CourseTables(schoolyear).klass2subject_teachers()
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
