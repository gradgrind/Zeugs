#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_text/checksubjects.py

Last updated:  2019-11-22

Prepare checklists of subjects for the teachers.

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

from weasyprint import HTML, CSS

from wz_core.configuration import Paths
from wz_core.courses import CourseTables

#Messages
_WRITTEN = "Klassen- und Fachzuordnung der Lehrer:\n  {path}"

_TEXT = """
<h1>Zeugnisse {year}: {teacher}</h1>
<p>Liebe Kolleginnen und Kollegen,</p>
<p>bitte unten stehende Liste kontrollieren:</p>
<p></p>
<ul>
  <li>Sind Fächer angegeben, für die Sie keine Zeugnisse schreiben?</li>
  <li>Fehlen Fächer, für die Sie Zeugnisse schreiben?<li>
  <li>Zeugnisse für Praktika, Jahresarbeiten und andere Projekte nicht
   vergessen!<li>
  <li>Falls Sie Zeugnisse mit der Hand schreiben wollen, bitte die
   betroffenen Fächer klar angeben.<li>
  <li>Die angegebenen Fachbezeichnungen sind so, wie sie im Zeugnis
   erscheinen werden. Sind sie korrekt?<li>
  <li>Ihr Name ist hier so angegeben, wie er im Zeugnis erscheinen wird.
   Möchten Sie das ändern?<li>
  <li>Bitte den Zettel mit Unterschrift in mein Fach im
  Hauptlehrerzimmer legen, auch wenn alles richtig ist.</li>
</ul>
<p>Herzliche Grüße</p>
<p>{manager}, {date}</p>

<hr></hr>

<table>
  <thead>
    <th class="th1">Klasse</th>
    <th class="th2">Fach</th>
  </thead>
  <tbody>
{tbody}
  </tbody>
</table>
"""

_TR = '    <tr><td class="td1">{klass}</td><td>{subject}</td></<tr>'

css = CSS (string='''
    @page { size: A4; margin: 2cm }
    h1 {page-break-before: always; font-size: 120%}
    .td1 {padding-left: 2em}
    .th1 {width: 5em; padding-left: 2em; border-bottom: 1pt solid}
    .th2 {border-bottom: 1pt solid}
    li {line-height: 1.5}
}
''')


def makeSheets (schoolyear, manager, date):
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

#    return tidmap

    noreports = []
    pages = []
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
                lines.append (_TR.format (klass=klass, subject=sname))
        pages.append (_TEXT.format (year=schoolyear, teacher=tname,
                manager=manager, date=date,
                tbody="\n".join (lines))
            )

    html = HTML (string="\n\n".join (pages))
    fpath = Paths.getYearPath (schoolyear, 'FILE_TEACHER_REPORT_LISTS')
    html.write_pdf (fpath, stylesheets=[css])
    REPORT.Info (_WRITTEN, path=fpath)

    return noreports



_year = 2020
_manager = "Michael Towers"
def test_01 ():
    from datetime import date
    _date = date.today ().strftime ("%d.%m.%Y")
#    tidmap = makeSheets (_year)
#    print (tidmap)
    noreports = makeSheets (_year, _manager, _date)
    REPORT.Test ("\n**** Folgende Lehrkräfte haben keine Zeugnisse:\n")
    for tname in noreports:
        REPORT.Test ("   --- %s" % tname)
