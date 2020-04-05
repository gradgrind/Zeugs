### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/makereports.py

Last updated:  2020-04-05

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
_BAD_DATE_GROUP = "Gruppe {group} ist keine Zeugnisgruppe"
_TOO_MANY_SUBJECTS = ("Zu wenig Platz für Fachgruppe {group} in Vorlage:"
        "\n  {template}\n  {pname}: {sids}")


import os

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils, Klass
from wz_core.db import DB
from wz_compat.config import printSchoolYear, printStream
from wz_compat.grade_classes import getGradeGroup
from wz_grades.gradedata import (GradeReportData, CurrentTerm,
        getGradeData, updateGradeReport, getTermTypes)


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
    ks = str(klass_streams)
    try:
        dateInfo = curterm.dates()[ks]
    except:
        REPORT.Fail(_BAD_DATE_GROUP, group = ks)
    DATE_D = dateInfo.DATE_D
    if not DATE_D:
        REPORT.Fail(_NO_ISSUE_DATE, klass = ks)
    # GDATE_D is not necessarily needed by the report, so don't report
    # it missing – the conversion will catch the null value later.
    GDATE_D = dateInfo.GDATE_D
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
    reportData = GradeReportData(schoolyear, klass_streams)
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
        pdata.date_D = gradedata['DATE_D'] or DATE_D
        pdata.gdate_D = gradedata['GDATE_D'] or GDATE_D
        # Add the grades, etc., to the pupil data
        gmap = gradedata['GRADES']
        gmanager = reportData.gradeManager(gmap)
        reportData.getTagmap(gmanager, pdata, rtype)
        if gmanager.reportFail(termn, rtype, pdata):
            # true -> include report
            pdata.grades = gmanager
            pdata.remarks = gradedata['REMARKS']
            pmaplist.append(pdata)

    if not pmaplist:
        REPORT.Fail(_NOPUPILS)
    ### Generate html for the reports
    source = reportData.template.render(
            report_type = rtype,
            SCHOOLYEAR = printSchoolYear(schoolyear),
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = pmaplist,
            klass = klass_streams
        )

    # Report excess subject/grade pairs
    ok = True
    for pdata in pmaplist:
        for group in reportData.sgroup2sids:
            sidlist = []
            while True:
                s = pdata.grades.GET(group)
                if not s:
                    break
                sidlist.append(s[0])
            if sidlist:
                ok = False
                REPORT.Error(_TOO_MANY_SUBJECTS, group = group,
                        pname = pdata.name(), sids = repr(sidlist),
                        template = reportData.template.filename)
    if not ok:
        return None

    # Convert to pdf
    html = HTML(string=source,
            base_url=os.path.dirname(reportData.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEKREPORTS, ks=klass_streams)
    return pdfBytes



def makeOneSheet(schoolyear, pdata, term):
    """
    <schoolyear>: year in which school-year ends (int)
    <pdata>: a <PupilData> instance for the pupil whose report is to be built
    <term>: keys the grades in the database (term or tag)
    """
    pid = pdata['PID']
    # Read database entry for the grades
    gradedata = getGradeData(schoolyear, pid, term)
    gmap = gradedata['GRADES']  # grade mapping
    # <GradeReportData> manages the report template, etc.:
    # From here on use klass and stream from <gradedata>
    klass = Klass.fromKandS(gradedata['CLASS'], gradedata['STREAM'])
    try:
        curterm = CurrentTerm(schoolyear, term)
    except CurrentTerm.NoTerm:
        curterm = None
    pdata.date_D = gradedata['DATE_D']
    pdata.gdate_D = gradedata['GDATE_D']
    rtype = gradedata['REPORT_TYPE']
    if curterm:
        ggroup = str(getGradeGroup(term, klass))
        dates = curterm.dates().get(ggroup)
        if not pdata.date_D:
            if dates:
                pdata.date_D = dates.DATE_D
        if not pdata.gdate_D:
            if dates:
                pdata.gdate_D = dates.GDATE_D
        if not rtype:
            rtype = getTermTypes(klass, curterm.TERM)[0]
    reportData = GradeReportData(schoolyear, klass)
    # Build a grade mapping for the tags of the template.
    # Use the class and stream from the grade data
    pdata['CLASS'] = gradedata['CLASS']
    pdata['STREAM'] = gradedata['STREAM']
    gmanager = reportData.gradeManager(gmap)
    reportData.getTagmap(gmanager, pdata, rtype)
    if not gmanager.reportFail(term, rtype, pdata):
        return None
    pdata.grades = gmanager
    pdata.remarks = gradedata['REMARKS']

    ### Generate html for the reports
    source = reportData.template.render(
            report_type = rtype,
            SCHOOLYEAR = printSchoolYear(schoolyear),
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = [pdata],
            klass = klass
        )

    # Report excess subject/grade pairs
    ok = True
    for group in reportData.sgroup2sids:
        sidlist = []
        while True:
            s = pdata.grades.GET(group)
            if not s:
                break
            sidlist.append(s[0])
        if sidlist:
            ok = False
            REPORT.Error(_TOO_MANY_SUBJECTS, group = group,
                    pname = pdata.name(), sids = repr(sidlist),
                    template = reportData.template.filename)
    if not ok:
        return None

    # Convert to pdf
    html = HTML(string=source,
            base_url=os.path.dirname(reportData.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEPREPORT, pupil=pdata.name())
    return pdfBytes



##################### Test functions
_year = 2016

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
    for k in ('13', '12.Gym', '12.HS-RS', '11.Gym', '11.HS-RS', '10'):
        REPORT.Test("\n  Reports for class %s\n" % k)
        _ks = Klass(k)
        try:
            pdfBytes = makeReports(_ks)
        except REPORT.RuntimeFail:
            continue
        if pdfBytes:
            fpath = Paths.getYearPath(_year, 'FILE_GRADE_REPORT', make = -1
                    ).replace('*', str(_ks).replace('.', '-')) + '.pdf'
            with open(fpath, 'wb') as fh:
                fh.write(pdfBytes)

def test_03():
    _term = '1'
    _pids = ('200407', '200853', '200651')
    pupils = Pupils(_year)
    for _pid in _pids:
        pdata = pupils.pupil(_pid)
        pdfBytes = makeOneSheet(_year, pdata, _term)
        if pdfBytes:
            ptag = pdata['PSORT'].replace(' ', '_')
            fpath = Paths.getYearPath(_year, 'FILE_GRADE_REPORT', make = -1
                    ).replace('*', ptag + '.pdf')
            with open(fpath, 'wb') as fh:
                fh.write(pdfBytes)

def test_04():
    _term = '2'
    _pids = ('201052', '200408')
    pupils = Pupils(_year)
    for _pid in _pids:
        pdata = pupils.pupil(_pid)
        pdfBytes = makeOneSheet(_year, pdata, _term)
        if pdfBytes:
            ptag = pdata['PSORT'].replace(' ', '_')
            fpath = Paths.getYearPath(_year, 'FILE_GRADE_REPORT', make = -1
                    ).replace('*', ptag + '.pdf')
            with open(fpath, 'wb') as fh:
                fh.write(pdfBytes)
