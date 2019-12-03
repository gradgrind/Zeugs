#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_text/print_klass_subject_teacher.py

Last updated:  2019-11-22

Prepare checklists of subject-teacher mapping for each school-class.

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

#TODO: Rather reportlab (or even something else?)?
from weasyprint import HTML, CSS

from wz_core.configuration import Paths
from wz_core.courses import CourseTables

#Messages
_WRITTEN = "Fach-Lehrer-Zuordnung der Klassen:\n  {path}"

#TODO: Mark for hand-written?
_TEXT = """
<h1>Kontrollblatt Klasse {klass}</h1>
<p>Korrekturen bitte an {manager}.</p>
<p>Stand {date}</p>
<hr></hr>

<table>
  <thead>
    <th class="th1">Fach</th>
    <th class="th2">Lehrer</th>
  </thead>
  <tbody>
{tbody}
  </tbody>
</table>
"""

_TR = '    <tr><td class="td1">{subject}</td><td class="td2">{teacher}</td></<tr>'

_css = '''
    @page { size: A4; margin: 2cm;

        @top-right {
            content: "Zeugnisse {{year}}: " string(heading);
        }
    }

    h1 {
        page-break-before: always;
        font-size: 120%;
        string-set: heading content();
    }
    .td1 {padding-left: 2em}
    .td2 {padding-left: 2em}
    .th1 {width: 5em; padding-left: 2em; border-bottom: 1pt solid}
    .th2 {border-bottom: 1pt solid; padding-left: 2em}
    li {line-height: 1.5}
}
'''


def makeSheets (schoolyear, manager, date):
    courses = CourseTables (schoolyear)
    tidmap = {tid: courses.teacherData.getTeacherName (tid)
            for tid in courses.teacherData}

    pages = []
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
                lines.append (_TR.format (subject=sname,
                        teacher=tidmap [tid]))

        pages.append (_TEXT.format (year=schoolyear, klass=klass,
                manager=manager, date=date,
                tbody="\n".join (lines)))

    html = HTML (string="\n\n".join (pages))
    fpath = Paths.getYearPath (schoolyear, 'FILE_CLASS_REPORT_LISTS')
    html.write_pdf (fpath, stylesheets=[CSS (string=_css.replace ('{{year}}',
            str (schoolyear)))])
    REPORT.Info (_WRITTEN, path=fpath)



_year = 2020
_manager = "Michael Towers"
def test_01 ():
    from datetime import date
    _date = date.today ().strftime ("%d.%m.%Y")
    makeSheets (_year, _manager, _date)
