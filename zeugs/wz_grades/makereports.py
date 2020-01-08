# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/makereports.py

Last updated:  2020-01-08

Generate the grade reports for a given class/stream.
Fields in template files are replaced by the report information.

In the templates there are grouped and numbered slots for subject names
and the corresponding grades.

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

#TODO: Maybe also "Sozialverhalten" und "Arbeitsverhalten"
#TODO: Praktika? e.g.
#       Vermessungspraktikum:   10 Tage
#       Sozialpraktikum:        3 Wochen
#TODO: Maybe component courses (& eurythmy?) merely as "teilgenommen"?


## Messages
_PUPILS_NOT_IN_CLASS_STREAM = "Schüler {pids} nicht in Klasse/Gruppe {ks}"
#_NOTEMPLATE = "Vorlagedatei (Notenzeugnis) fehlt für Klasse {ks}:\n  {path}"
_MADEKREPORTS = "Notenzeugnisse für Klasse {ks} wurden erstellt"
_NOPUPILS = "Notenzeugnisse: keine Schüler"
_MADEPREPORT = "Notenzeugnis für {pupil} wurde erstellt"


import os
#from types import SimpleNamespace

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils, KlassData, match_klass_stream
from wz_compat.config import printSchoolYear, printStream
from wz_grades.gradedata import (GradeReportData,
        db2grades, getGradeData, updateGradeReport)


def makeReports(schoolyear, term, klass_stream, date, pids=None):
    """Build a single file containing reports for the given pupils.
    This only works for groups with the same report type and template.
    <term> is the term.
    <date> is the date of issue ('YYYY-MM-DD').
    <pids>: a list of pids (must all be in the given klass), only
        generate reports for pupils in this list.
        If not supplied, generate reports for the whole klass/group.
    """
    # <db2grades> returns a list: [(pid, pname, grade map), ...]
    # <grades>: {pid -> (pname, grade map)}
    grades = {pid: (pname, gmap)
            for pid, pname, gmap in db2grades(schoolyear, term, klass_stream)
    }
    pupils = Pupils(schoolyear)
    pall = pupils.classPupils(klass_stream) # list of data for all pupils
    # If a pupil list is supplied, select the required pupil data.
    # Otherwise use the full list.
    if pids:
        pset = set (pids)
        plist = []
        for pdata in pall:
            try:
                pset.remove(pdata['PID'])
            except KeyError:
                continue
            plist.append(pdata)
        if pset:
            REPORT.Bug(_PUPILS_NOT_IN_CLASS_STREAM, pids=', '.join(pset),
                    ks=klass_stream)
    else:
        plist = pall

    ### Get a tag mapping for the grade data of each pupil
    # Get the name of the relevant configuration file in folder GRADES:
    grademap = match_klass_stream(klass_stream, CONF.MISC.GRADE_SCALE)
    # <GradeReportData> manages the report template, etc.:
    # Get the report type from the term and klass/stream
    rtype = match_klass_stream(klass_stream, CONF.REPORT_TEMPLATES['_' + term])
    reportData = GradeReportData(schoolyear, rtype, klass_stream)
    # General info on the klass/stream:
    klassData = KlassData(klass_stream)
    pmaplist = []
    for pdata in plist:
        pid = pdata['PID']
        pname, gmap = grades[pid]   # get pupil name and grade map
        # Build a grade mapping for the tags of the template:
        pdata.grades = reportData.getTagmap(gmap, pname, grademap)
        pmaplist.append(pdata)
        # Update grade database
        updateGradeReport(schoolyear, pid, term,
                date=date,
                rtype=rtype
        )

    ### Generate html for the reports
# Testing:
#    n = 0  # with change below, just generate nth of list
#    print("§§§", pmaplist[n])
    source = reportData.template.render(
            report_type = rtype,
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = pmaplist,
#            pupils = [pmaplist[n]],
            klass = klassData
        )
    # Convert to pdf
    if not plist:
        REPORT.Fail(_NOPUPILS)
    html = HTML(string=source,
            base_url=os.path.dirname(reportData.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEKREPORTS, ks=klass_stream)
    return pdfBytes



def makeOneSheet(schoolyear, date, pdata, term, rtype):
    """
    <schoolyear>: year in which school-year ends (int)
    <data>: date of issue ('YYYY-MM-DD')
    <pdata>: a <PupilData> instance for the pupil whose report is to be built
    <term>: keys the grades in the database
    <rtype>: report category, determines template
    """
    pid = pdata['PID']
    # Read database entry for the grades
    gradedata = getGradeData(schoolyear, pid, term)
    gmap = gradedata['GRADES']  # grade mapping
    pname = pdata.name()
    # <GradeReportData> manages the report template, etc.:
    # From here on use klass_stream from <gradedata>
    klass_stream = gradedata['CLASS_STREAM']
    reportData = GradeReportData(schoolyear, rtype, klass_stream)
    # General info on the klass/stream:
    klassData = KlassData(klass_stream)
    # Get the name of the relevant configuration file in folder GRADES:
    grademap = match_klass_stream(klass_stream, CONF.MISC.GRADE_SCALE)
    # Build a grade mapping for the tags of the template:
    pdata.grades = reportData.getTagmap(gmap, pname, grademap)
    # Update grade database
    updateGradeReport(schoolyear, pid, term,
            date=date,
            rtype=rtype
    )

    ### Generate html for the reports
    source = reportData.template.render(
            report_type = rtype,
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = [pdata],
            klass = klassData
        )
    # Convert to pdf
    html = HTML(string=source,
            base_url=os.path.dirname(reportData.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEPREPORT, pupil=pname)
    return pdfBytes



##################### Test functions
_year = 2016
_date = '2016-01-29'
_term = '1'
def test_01():
    from wz_compat.template import openTemplate, getTemplateTags, pupilFields
    from glob import glob
    fbase = Paths.getUserPath('DIR_TEMPLATES')
    fx = 'Notenzeugnis/*.html'
    fmask = os.path.join(fbase, *fx.split('/'))
    for f in glob(fmask):
        fname = os.path.basename(f)
        fpath = fx.rsplit('/', 1)[0] + '/' + os.path.basename(f)
        REPORT.Test("TEMPLATE: %s" % fpath)
        t = openTemplate(fpath)
        tags = getTemplateTags(t)
        REPORT.Test("Pupil fields: %s" % repr(pupilFields(tags)))

def test_02():
    _klass_stream = '13'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_03():
    _klass_stream = '12.RS'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_04():
    _klass_stream = '12.Gym'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_05():
    _klass_stream = '11'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)


def test_06():
#TODO: Perhaps if _GS is set, the type should be overriden?
    _klass = '12'
    _pid = '200407'
    pupils = Pupils(_year)
    pall = pupils.classPupils(_klass) # list of data for all pupils
    pdata = pall.pidmap[_pid]
    pdfBytes = makeOneSheet(_year, '2016-02-03', pdata, _term, 'Abgang')
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    ptag = pdata['PSORT'].replace(' ', '_')
    fpath = os.path.join (folder, 'test_%s_Abgang.pdf' % ptag)
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test(" --> %s" % fpath)

def test_07():
    return

    _klass_stream = '12.RS'
    pupils = Pupils(_year)
    plist = pupils.classPupils(_klass_stream)
    from types import SimpleNamespace
    p = plist[0]
    pmap = {f: p[f] for f in p.fields()}
    pdfBytes = makeOneSheet(_year, _date, _klass_stream, 'Abschluss',
            SimpleNamespace(**pmap))
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test2.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test(" --> %s" % fpath)
