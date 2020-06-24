### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/makeabi.py

Last updated:  2020-06-24

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
from wz_core.courses import CourseTables
from wz_core.db import DBT
from wz_core.template import openTemplate
from wz_grades.gradedata import GradeData
from wz_compat.gradefunctions import AbiCalc, GradeError


def saveGrades(schoolyear, pdata, grades, date):
    """The given grade mapping is saved to the GRADES table, with
    'A' in the TERM field and 'Abitur' in the REPORT_TYPE field.
    """
    gdata = GradeData(schoolyear, 'A', pdata)
    gdata.updateGrades(grades, REPORT_TYPE = 'Abitur', DATE_D = date)
    REPORT.Info(_ABIGRADES, pname = pdata.name())
    return True


def makeAbi(schoolyear, pdata):
    """Make an Abitur report. Return it as a byte-stream (pdf).
    """
    # Get grade data: This needs to be an ordered mapping.
    gdata = GradeData(schoolyear, 'A', pdata)
    if gdata.KEYTAG:
        sid2grade = gdata.getAllGrades()
        date = gdata.ginfo['DATE_D']
    else:
        REPORT.Fail(_NO_GRADES, pname = pdata.name())
    abiCalc = AbiCalc(sid2grade)
    try:
        zgrades = abiCalc.getFullGrades()
    except GradeError:
        REPORT.Fail(_MISSING_GRADES, pname = pdata.name())
#####
#    REPORT.Test("??? %s" % repr(zgrades))

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
#    return
#TODO

    from wz_core.pupils import Pupils
    _date = '2016-06-10'
    _grades = {
        '200305': {
            'De.e': '14',
            'N_De.e': '*',
            'En.e': '10',
            'N_En.e': '*',
            'Ges.e': '08',
            'N_Ges.e': '14',
            'Ma.g': '03',
            'N_Ma.g': '06',
            'Fr.m': '05',
            'Bio.m': '06',
            'Ku.m': '08',
            'Sp.m': '11'
        },
        '200302': {
            'De.e': '15',
            'N_De.e': '*',
            'Ges.e': '15',
            'N_Ges.e': '*',
            'Bio.e': '15',
            'N_Bio.e': '*',
            'Ma.g': '15',
            'N_Ma.g': '*',
            'En.m': '15',
            'Fr.m': '15',
            'Mu.m': '15',
            'Ku.m': '15'
        },
        '200301': {
            'De.e': '03',
            'N_De.e': '06',
            'En.e': '04',
            'N_En.e': '05',
            'Ges.e': '02',
            'N_Ges.e': '06',
            'Ma.g': '09',
            'N_Ma.g': '*',
            'Fr.m': '08',
            'Bio.m': '04',
            'Mu.m': '13',
            'Ku.m': '12'
        }
    }
    pupils = Pupils(_testyear)
    for _pid, grades in _grades.items():
        pdata = pupils.pupil(_pid)
        saveGrades(_testyear, pdata, grades, _date)

def test_02():
    from wz_core.pupils import Pupils
    from wz_core.configuration import Paths
#    _pids = ('200305', '200302', '200301')
    _pids = ('200302',)
    pupils = Pupils(_testyear)
    for _pid in _pids:
        pdata = pupils.pupil(_pid)
        pdfBytes = makeAbi(_testyear, pdata)
        if pdfBytes:
            ptag = pdata['PSORT'].replace(' ', '_')
            fpath = Paths.getYearPath(_testyear, 'FILE_GRADE_REPORT',
                    make = -1).replace('*', ptag + '.pdf')
            with open(fpath, 'wb') as fh:
                fh.write(pdfBytes)
