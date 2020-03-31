### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/makeabi.py

Last updated:  2020-03-31

Generate final grade reports for the Abitur.

Fields in the template file are replaced by the report information.

The template has grouped and numbered slots for subject names
and the corresponding grades.


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

_ABIGRADES = "Abiturnoten aktualisiert für {pname}"
_NO_GRADES = "Keine Notendaten für {pname}"
_MADEAREPORT = "Abiturzeugnis für {pupil} wurde erstellt"
_MISSING_GRADES = "Abiturnoten fehlen für {pname}"


import os

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Dates
from wz_core.pupils import Klass
from wz_core.courses import CourseTables
from wz_core.db import DB
from wz_grades.gradedata import map2grades, getGradeData
from wz_compat.gradefunctions import AbiCalc, GradeError
from wz_compat.template import openTemplate


def saveGrades(schoolyear, pdata, grades, date):
    """The given grade mapping is saved to the GRADES table, with
    'A' in the TERM field and 'Abitur' in the REPORT_TYPE field.
    """
    db = DB(schoolyear)
    gstring = map2grades(grades)
    klass = pdata.getKlass()
    pid = pdata['PID']
    term = 'A'
    db.updateOrAdd('GRADES',
            {   'CLASS': klass.klass, 'STREAM': pdata['STREAM'],
                'PID': pid, 'TERM': term, 'DATE_D': date,
                'REPORT_TYPE': 'Abitur', 'GRADES': gstring
            },
            TERM = term,
            PID = pid
    )
    REPORT.Info(_ABIGRADES, pname = pdata.name())
    return True


def makeAbi(schoolyear, pdata,):
    """Make an Abitur report. Return it as a byte-stream (pdf).
    """
    # Get grade data: This needs to be an ordered mapping.
    grades = getGradeData(schoolyear, pdata['PID'], term = 'A')
    try:
        sid2grade = grades['GRADES']
        date = grades['DATE_D']
    except:
        REPORT.Fail(_NO_GRADES, pname = pdata.name())

    # Get an ordered list of (sid, sname) pairs
    sid_name = []
    courses = CourseTables(schoolyear)
    for sid in sid2grade:
        try:
            sname = courses.subjectName(sid).split('|')[0].rstrip()
        except:
            continue
        sid_name.append((sid, sname))
    abiCalc = AbiCalc(sid_name, sid2grade)
    try:
        zgrades = abiCalc.getFullGrades()
    except GradeError:
        REPORT.Fail(_MISSING_GRADES, pname = pdata.name())
    # Passed?
    tfile = 'Abitur/Abitur.html' #if zgrades["PASS"] else 'Abitur/AbiturFail.html'
    ### Generate html for the reports
    # Get template
    template = openTemplate(tfile)
    source = template.render(
            DATE_D = date,
            todate = Dates.dateConv,
            pupil = pdata,
            grades = zgrades
        )
    # Convert to pdf
    html = HTML(string=source,
            base_url=os.path.dirname(template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEAREPORT, pupil=pdata.name())
    return pdfBytes





############### TEST functions ###############
_testyear = 2016
def test_01():
    pass
