### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/maketables.py

Last updated:  2020-04-02

Build result tables for the grade groups, including evaluation, etc.

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

#TODO ...




## Messages
_BAD_GROUP_TERM = "Ungültige Gruppe ({group}) und Halbjahr ({term})"
_WRONG_CLASS = "{pname} hat die Klasse gewechselt"
_WRONG_GROUP = "{pname} hat die Gruppe gewechselt"
_WRONG_RTYPE = "Zeugnistyp für {pname} ist {rtype}"
_NO_GRADES = "Keine Noten für {pname}"


#???
_NOPUPILS = "Notenzeugnisse: keine Schüler"


#TODO: check imports
import os

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils, Klass
from wz_core.db import DB
from wz_compat.config import printSchoolYear, printStream
from wz_compat.grade_classes import getGradeGroup
from wz_compat.template import openTemplate
from wz_grades.gradedata import (GradeReportData, CurrentTerm,
        getGradeData, updateGradeReport, getTermTypes)


#TODO
def makeTable(schoolyear, term, ggroup):
    """Build a result table for the given year, term and grade group.
    <ggroup> is a <Klass> instance.
    """
    try:
        rtype = getTermTypes(ggroup, term)[0]
    except:
        REPORT.Fail(_BAD_GROUP_TERM, group = ggroup, term = term)
    pupils = Pupils(schoolyear)
#?
    ### Get a tag mapping for the grade data of each pupil
    # <GradeReportData> manages the report template, etc.:
    reportData = GradeReportData(schoolyear, ggroup, rtype)
    plist = []
    db = DB(schoolyear)
    for pdata in pupils.classPupils(ggroup):
        pid = pdata['PID']
        # Get grade map for pupil
        gradedata = getGradeData(schoolyear, pid, term)
        # Check for mismatches with pupil and term info
        gmap = None
        if gradedata:
            if gradedata['CLASS'] != ggroup.klass:
                REPORT.Warn(_WRONG_CLASS, pname = pdata.name())
                continue
            gstream = gradedata['STREAM']
            if gstream != pdata['STREAM']:
                REPORT.Warn(_WRONG_GROUP, pname = pdata.name())
                if ggroup.containsStream(gstream):
                    pdata['STREAM'] = gstream
                else:
                    continue
            grtype = gradedata['REPORT_TYPE']
            if grtype and grtype != rtype:
                REPORT.Warn(_WRONG_RTYPE, pname = pdata.name(),
                        rtype = gradedata['REPORT_TYPE'])
            # Add the grades, etc., to the pupil data
            gmap = gradedata['GRADES']

        if not gmap:
            REPORT.Warn(_NO_GRADES, pname = pdata.name())
            continue

#?
        gmanager = reportData.gradeManager(gmap)
        gdata = reportData.getTagmap(gmanager, pdata, report = False)
        REPORT.Test("\n  %s:\n %s" % (pdata.name(), repr(gdata)))

        REPORT.Test("\n  XINFO: %s" % repr(gmanager.XINFO))

#        pdata.grades = gdata
        pdata.grades = gmap
        plist.append(pdata)


#TODO
    REPORT.Test("\n\nTEST AREA!!!\n#################\n")
    slist = []
    for g, sids in reportData.sgroup2sids.items():
        if sids:
            slist.append((None, None))
            for sid in sids:
                sname = reportData.sid2tlist[sid].subject
                if len(sname) > 20:
                    sname = sname[:16] + '...'
                slist.append((sid, sname))

# composite subject with different colouring?

    # Get table template
    template = openTemplate('GRADES/GRADETABLE.html')
    ### Generate html for the table
    source = template.render(
#TODO
            SCHOOLYEAR = printSchoolYear(schoolyear),
            date = Dates.today(iso = False),
            subjects = slist,
            pupils = plist,
            klass = ggroup
        )
#TODO
    return source

    # Convert to pdf
    if not plist:
        REPORT.Fail(_NOPUPILS)
    html = HTML(string=source,
            base_url=os.path.dirname(reportData.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEKREPORTS, ks=klass_streams)
    return pdfBytes



##################### Test functions
_year = 2016
_term = '2'
def test_01():
    _ks = Klass('11')
    pdfBytes = makeTable(_year, _term, _ks)

#TODO: currently html as string?
    fpath = os.path.join(Paths.getYearPath(_year), 'tmp', 'GRADES.html')
    with open(fpath, 'w', encoding='utf-8') as fh:
        fh.write(pdfBytes)
#    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
#    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_ks, _term))
#    with open(fpath, 'wb') as fh:
#        fh.write(pdfBytes)

def test_07():
    return
    _term = '2'
    for _ks0 in '11', '12.RS-HS-_', '12.Gym':
        _ks = Klass(_ks0)
        pdfBytes = makeTable(_year, _term, _ks)
        folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
        fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_ks, _term))
        with open(fpath, 'wb') as fh:
            fh.write(pdfBytes)
