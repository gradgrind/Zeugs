### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/makereports.py

Last updated:  2020-03-22

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
_MADEKREPORTS = "Notenzeugnisse für Klasse {ks} wurden erstellt"
_NOPUPILS = "Notenzeugnisse: keine Schüler"
_MADEPREPORT = "Notenzeugnis für {pupil} wurde erstellt"
_NO_ISSUE_DATE = "Kein Ausstellungsdatum für Klasse {klass}"
_NO_GRADES = "Keine Noten für {pname} => kein Zeugnis"
_WRONG_GROUP = "{pname} hat die Gruppe gewechselt => kein Zeugnis"
_WRONG_RTYPE = "Zeugnistyp für {pname} ist {rtype} => kein Zeugnis"
_WRONG_DATE = "Ausstellungsdatum ({date}) für {pname} weicht vom Standard ab"
_WRONG_GDATE = "Konferenzdatum ({date}) für {pname} weicht vom Standard ab"


import os

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils, Klass
from wz_core.db import DB
from wz_compat.config import printSchoolYear, printStream
from wz_compat.grade_classes import CurrentTerm, gradeIssueDate, gradeDate
from wz_grades.gradedata import (GradeReportData,
        getGradeData, updateGradeReport)


#def getTermDefaultType (klass, term):
#    t = '_' + term if term in CONF.MISC.TERMS else '_X'
#    rtypes = klass.match_map(CONF.GRADES.TEMPLATE_INFO[t])
#    return rtypes.split()[0]

def getTermTypes(klass, term):
    """Get a list of acceptable report types for the given group
    (<Klass> instance) and term. If <term> is not a term, a list for
    "special" reports is returned.
    If there is no match, return <None>.
    """
    t = ('_' + term) if term in CONF.MISC.TERMS else '_X'
    tlist = klass.match_map(CONF.GRADES.TEMPLATE_INFO[t])
    return tlist.split() if tlist else None


def makeReports(klass_streams, pids=None):
    """Build a single file containing reports for the given pupils.
    It is only applicable to the current term, because in the past the
    individual pupils may have been in different groups, or even classes.
    This also only works for groups with the same report type and template.
    Should any included pupils have mismatches in critical fields, e.g.
    the report type, they will be automatically excluded from the reports.
    <klass_streams> is a <Klass> instance: it can be a just a school-class,
        but it can also have a stream, or list of streams.
    <pids>: a list of pids (must all be in the given klass/streams), only
        generate reports for pupils in this list.
        If not supplied, generate reports for the whole klass/group.
    """
    curterm = CurrentTerm()
    termn = curterm.TERM
    schoolyear = curterm.schoolyear
    DATE_D = gradeIssueDate(schoolyear, termn, klass_streams)
    if not DATE_D:
        REPORT.Fail(_NO_ISSUE_DATE, klass = klass_streams)
    # GDATE_D is not necessarily needed by the report, so don't report
    # it missing – the conversion will catch the null value later.
    GDATE_D = gradeDate(schoolyear, termn, klass_streams)
    # Get the report type from the term and klass/stream
    rtype = getTermTypes(klass_streams, curterm.TERM)[0]
    # If a pupil list is supplied, select the required pupil data,
    # otherwise use the full list.
    pupils = Pupils(schoolyear)
    pall = pupils.classPupils(klass_streams) # list of data for all pupils
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
                    ks=klass_streams)
    else:
        plist = pall
    ### Get a tag mapping for the grade data of each pupil
    # <GradeReportData> manages the report template, etc.:
    reportData = GradeReportData(schoolyear, klass_streams, rtype)
    pmaplist = []
    db = DB(schoolyear)
    for pdata in plist:
        pid = pdata['PID']
        # Get grade map for pupil
        gradedata = getGradeData(schoolyear, pid, curterm.TERM)
        # Check for mismatches with pupil and term info
        if not gradedata:
            REPORT.Error(_NO_GRADES, pname = pdata.name())
            continue
        if (gradedata['CLASS'] != klass_streams.klass
                or gradedata['STREAM'] != pdata['STREAM']):
            REPORT.Warn(_WRONG_GROUP, pname = pdata.name())
            continue
        grtype = gradedata['REPORT_TYPE']
        if grtype and grtype != rtype:
            REPORT.Warn(_WRONG_RTYPE, pname = pdata.name(),
                    rtype = gradedata['REPORT_TYPE'])
            continue
        db.updateOrAdd('GRADES',
                {   'REPORT_TYPE': rtype,
                    'DATE_D': DATE_D,
                    'GDATE_D': GDATE_D
                },
                TERM = curterm.TERM,
                PID = pid,
                update_only = True
        )
        # Add the grades, etc., to the pupil data
        gmap = gradedata['GRADES']
        pdata.grades = reportData.getTagmap(reportData.gradeManager(gmap),
                pdata)
        pdata.REMARKS = gradedata['REMARKS']
        pmaplist.append(pdata)

    ### Generate html for the reports
    source = reportData.template.render(
            report_type = rtype,
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = DATE_D,
            GDATE_D = GDATE_D,
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = pmaplist,
            klass = klass_streams
        )
    # Convert to pdf
    if not plist:
        REPORT.Fail(_NOPUPILS)
    html = HTML(string=source,
            base_url=os.path.dirname(reportData.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEKREPORTS, ks=klass_streams)
    return pdfBytes



def makeOneSheet(schoolyear, pdata, term, rtype):
    """
    <schoolyear>: year in which school-year ends (int)
    <pdata>: a <PupilData> instance for the pupil whose report is to be built
    <term>: keys the grades in the database (term or date)
    <rtype>: report category, determines template
    """
    pid = pdata['PID']
    # Read database entry for the grades
    gradedata = getGradeData(schoolyear, pid, term)
    gmap = gradedata['GRADES']  # grade mapping
    # <GradeReportData> manages the report template, etc.:
    # From here on use klass and stream from <gradedata>
    klass = Klass.fromKandS(gradedata['CLASS'], gradedata['STREAM'])
    if term in CONF.MISC.TERMS:
#TODO
        date = getDateOfIssue(schoolyear, term, klass)
    else:
#TODO
        date = term
    reportData = GradeReportData(schoolyear, klass, rtype)
    # Build a grade mapping for the tags of the template.
    # Use the class and stream from the grade data
    pdata['CLASS'] = gradedata['CLASS']
    pdata['STREAM'] = gradedata['STREAM']
    pdata.grades = reportData.getTagmap(reportData.gradeManager(gmap), pdata)
    pdata.REMARKS = gradedata['REMARKS']

    ### Generate html for the reports
    source = reportData.template.render(
            report_type = rtype,
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = [pdata],
            klass = klass
        )
    # Convert to pdf
    html = HTML(string=source,
            base_url=os.path.dirname(reportData.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEPREPORT, pupil=pdata.name())
    return pdfBytes



##################### Test functions
_year = 2016
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
    _klass_stream = Klass('13')
    pdfBytes = makeReports (_year, _term, _klass_stream)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _term))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_03():
    _klass_stream = Klass('12.RS')
    pdfBytes = makeReports (_year, _term, _klass_stream)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _term))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_04():
    _klass_stream = Klass('12.Gym')
    pdfBytes = makeReports (_year, _term, _klass_stream)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _term))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_05():
    _klass_stream = Klass('11')
    pdfBytes = makeReports (_year, _term, _klass_stream)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _term))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)


def test_06():
#TODO: Perhaps if _GS is set, the type should be overriden?
    _klass = Klass('12')
    _pid = '200407'
    pupils = Pupils(_year)
    pall = pupils.classPupils(_klass) # list of data for all pupils
    pdata = pall.pidmap[_pid]
    pdfBytes = makeOneSheet(_year, pdata, _term, 'Abgang')
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    ptag = pdata['PSORT'].replace(' ', '_')
    fpath = os.path.join (folder, 'test_%s_Abgang.pdf' % ptag)
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test(" --> %s" % fpath)

def test_07():
    # Reports for second term
    _term = '2'
    for _ks in '11', '12.RS-HS-_', '12.Gym':
        _klass_stream = Klass(_ks)
        pdfBytes = makeReports (_year, _term, _klass_stream)
        folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
        fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _term))
        with open(fpath, 'wb') as fh:
            fh.write(pdfBytes)
