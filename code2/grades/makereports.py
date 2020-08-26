### python >= 3.7
# -*- coding: utf-8 -*-

"""
grades/makereports.py

Last updated:  2020-08-24

Generate the grade reports for a given class/stream.
Fields in template files are replaced by the report information.

In the templates there are grouped and numbered slots for subject names
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

#TODO: Maybe also "Sozialverhalten" und "Arbeitsverhalten"
#TODO: Praktika? e.g.
#       Vermessungspraktikum:   10 Tage
#       Sozialpraktikum:        3 Wochen
#TODO: Maybe component courses (& eurythmy?) merely as "teilgenommen"?


## Messages


#?
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
from collections import namedtuple

#from wz_core.configuration import Paths, Dates
#from wz_core.pupils import Pupils, Klass
#from wz_compat.config import printSchoolYear, printStream
#from wz_compat.grade_classes import getGradeGroup
#from wz_grades.gradedata import (GradeReportData, CurrentTerm,
#        GradeData, getTermTypes)


def makeReports(class_stream, schoolyear, term,
        report_type, issuedate, fixdate, grades):
    """Given grade information for a list of pupils, build a single file
    containing the grade reports for all pupils in the list.
    The grades (etc.) for a pupil are provided in a <Dictuple>.

    The school class (potentially with stream) is provided separately, for
    the whole group. It is possible that this class/stream differs from
    that of an individual pupil (when this has changed since the grading),
    in which case a warning will be issued, but the grade report will
    still be generated.
    Also the template for the reports needs to be supplied. This should
    be an instance of the appropriate <Template> class.

    Multiple reports within one file probably require all the reports to
    have the same number of pages if double-sided printing is to be done.
    """
# How to manage multipart templates?!
# 1) Separate the frame and the body
# 2) Substitute the individual fields in the body for each pupil (ignore
#   missing general fields). It would be good if missing individual
#   fields were reported?
# 3) Construct the whole tex file (frame + n*body)
# 4) Substitute the general fields – now report anything missing
# 5) Build pdf

    # School name (+ image, etc.?)

    # School year, e.g. 2019 – 2020
    # Term ("1. Halbjahr" / "1. und 2. Halbjahr" in Qualiphase)
    # Class and stream. The pupil-entries could be checked for conformity
    # before passing them here.
    # "Jahrgang".
    # Date of issue.
    # Date of Notenkonferenz.

    ### ?Possibly pupil-dependent?
    # Report type (Zeugnis / Abgangszeugnis / Abschlusszeugnis / ...)
    # All reports must have same type?
    #   Failed Abschluss -> Warning/Error? ... or automatic Zeugnis/Abgang
    #   As an Abschluss is potentially a different template: Error and fail
    #   or Error and skip.
    # Level (Maßstab Realschule, etc.)
    #   Abschluss: Erw/RS can be in the same group (like Versetzung in Quali)
    #   Because of the grade level, HS must be a separate group, even if
    #   the group was RS until the grades were "adjusted".

    # For RS/HS in class 12.2, the two parameters Abschluss (Erw/RS/HS/None)
    # and Gleichstellungsvermerk (HS/None) are required.
    # Grades.
    # Personal data (date and place of birth, place of dwelling, first
    # names, last name, date of entry, date of exit).

    # As far as possible, no processing should be done here which depends
    # on the regulations. Try to keep that in a regional/local module.

    # Qualifikation (not all valid in every group): HS, RS, Erw(/13), Q, None.
    # The meaning can vary according to year and stream.
    try:
        klass, stream = class_stream.split('.')
    except:
        klass, stream = class_stream, None

#This as function?
    try:
        grtemplates = GRADE_REPORT_TEMPLATE[report_type]
        t = grtemplates.get(class_stream)
        if not t:
            t = grtemplates.get(klass)
            if not t:
                t = grtemplates['*']
        if t == '-':
            raise KeyError
    except:
#TODO
        raise

#TODO: <t> is only the file name, will need full path!
    template = Template(t)
    texlist = []
    for pgrades in grades:
        data = dict(pgrades)
        # Get pupil's personal data
#TODO
        data.update(Pupils(pgrades['PID']))
        # Substitute pupil data, ignore missing fields
        texlist.append(template.substitute(data, tag='body')[0])
        tex0 = '\n\n\\newpage\n\n'.join(texlist)
        # Insert in frame, substitute general data
#TODO: gather all the parameters in an info-block somehow?
        gdata = prepareData(schoolyear, class_stream, term,
                report_type, issuedate, fixdate)
        tex =insert_and_substitute(gdata, ':', body=tex0)
        return template.makepdf(tex)



SCHOOL_DATA = {
    'Schule': 'Freie Michaelschule',
#TODO: absolute path?
    'LOGO': 'School-Logo.sgv'
}

def prepareData(schoolyear, class_stream, ...):
    """This can contain region/locality-dependent code preparing the
    information needed by the template.
    """
    data = {}


    for k, v in data.items():
        if k.endswith('.DAT'):
            data[k] = dateConv(v)
    # Assume the class always starts with two digits.
#TODO: How to get <class_stream>?
    data['Jahrgang'] = class_stream[:2]
#TODO: <schoolyear>?
    data['Schuljahr'] = '%d – %d' % (schoolyear - 1, schoolyear)
    data.update(SCHOOL_DATA)


DATEFORMAT = '%d.%m.%Y' # for  <datetime.datetime.strftime>
class DateError(Exception):
    pass
def dateConv (date, trap=True):
    """Convert a date string from the program format (e.g. "2016-12-06") to
    the format used for output (e.g. "06.12.2016").
    """
    try:
        d = datetime.datetime.strptime (date, "%Y-%m-%d")
        return d.strftime (DATEFORMAT)
    except:
        if trap:
            raise DateError("Ungültiges Datum: '%s'" % date)
        else:
            return "00.00.0000"


QUALI_VALID = { # Levels of qualification for stream and class.
    'HS': {'*': ['HS', '-']},
    'RS': {'12': ['Erw', 'RS', 'HS', '-'],
           '*': ['HS', '-']},
    'Gym': {'12': ['Erw', 'RS', 'HS'],
            '11': ['Q', 'HS', '-'],
            '*': ['HS', '-']}
}

# Grade report types.
GRADE_REPORTS = { # Map to titles of reports
    'Zeugnis':      'Zeugnis',
    'Abschluss':    'Abschlusszeugnis',
    'Abgang':       'Abgangszeugnis',
    'Orientierung': 'Orientierungsnoten',
    'Zwischen':     'Zwischenzeugnis'
}

# The first entry in each list is the default.
GRADE_REPORT_TERM = { # Valid types for term and class.
    '1': {
        '11': ['Orientierung', 'Abgang'],
        '12': ['Zeugnis', 'Abgang']
    }
    '2': {
        '10': ['Orientierung', 'Abgang'],
        '11': ['Zeugnis', 'Abgang'],
        '12.Gym': ['Zeugnis', 'Abgang'],
        '12.RS': ['Abschluss', 'Abgang', 'Zeugnis'],
        '12.HS': ['Abschluss', 'Abgang', 'Zeugnis']
    }
}
# ... any class, any time
GRADE_REPORT_ANYTIME = ['Abgang', 'Zwischen']

GRADE_REPORT_TEMPLATE = {
    'Orientierung': {'*': 'Orientierungsnoten'},
    'Zeugnis': {
        '12.Gym': 'Notenzeugnis-SII',
        '*': 'Notenzeugnis-SI'
    }
    'Zwischen': {
        '12': '-',
        '11': '-',
        '*' 'Zwischenzeugnis'
    }
    'Abschluss': {
        '12.RS': 'Notenzeugnis-SI',
        '12.HS': 'Notenzeugnis-SI'
    }
    'Abgang': {
    # An exit from class 12.Gym before the report for the first half year
    # can be a problem if there are no grades yet. Perhaps those from
    # class 11 could be converted?
        '12.Gym': 'Notenzeugnis-SII',
        '*': 'Notenzeugnis-SI'
    }
}


FIELDS_SI = {
    'Zeugnis', 'Klasse', 'Schule', 'Massstab', 'Jahrgang', 'Schuljahr',
    'P.G.DAT', 'P.G.ORT', 'X.DAT', 'I.DAT', 'E.DAT', 'K.DAT',
    'abschluss', 'gleichstellung',
    'P.VORNAMEN', 'P.NACHNAME',
    'Note.xx' & 'Fach.xx' for xx in 01 to 16,
    'NoteKP.xx' & 'FachKP.xx' for xx in 01 to 08,
}


def old_makeReports(klass_streams, pids=None):
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
    for pdata in plist:
        # Get grade map for pupil
        gradedata = GradeData(schoolyear, curterm.TERM, pdata)
        # Check for mismatches with pupil and term info
        if not gradedata.KEYTAG:
            REPORT.Error(_NO_GRADES, pname = pdata.name())
            continue
        if (gradedata.gclass != klass_streams.klass
                or gradedata.gstream != pdata['STREAM']):
            REPORT.Warn(_WRONG_GROUP, pname = pdata.name())
            continue
        grtype = gradedata.ginfo['REPORT_TYPE']
        if grtype and grtype != rtype:
            REPORT.Warn(_WRONG_RTYPE, pname = pdata.name(),
                    rtype = gradedata.ginfo['REPORT_TYPE'])
            continue
        pdata.date_D = gradedata.ginfo['DATE_D'] or DATE_D
        pdata.gdate_D = gradedata.ginfo['GDATE_D'] or GDATE_D
        # Add the grades, etc., to the pupil data
        gmanager = gradedata.getAllGrades()
        reportData.getTagmap(gmanager, pdata, rtype)
        if gmanager.reportFail(termn, rtype, pdata):
            # true -> include report
            pdata.grades = gmanager
            pdata.remarks = gradedata.ginfo['REMARKS']
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
    # Read database entry for the grades
    gradedata = GradeData(schoolyear, term, pdata)
    gmap = gradedata.getAllGrades()  # grade manager
    # <GradeReportData> manages the report template, etc.:
    # From here on use klass and stream from <gradedata>
    klass = Klass.fromKandS(gradedata.gclass, gradedata.gstream)
    try:
        curterm = CurrentTerm(schoolyear, term)
    except CurrentTerm.NoTerm:
        curterm = None
    pdata.date_D = gradedata.ginfo['DATE_D']
    pdata.gdate_D = gradedata.ginfo['GDATE_D']
    rtype = gradedata.ginfo['REPORT_TYPE']
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
    pdata['CLASS'] = gradedata.gclass
    pdata['STREAM'] = gradedata.gstream
    reportData.getTagmap(gmap, pdata, rtype)
    if not gmap.reportFail(term, rtype, pdata):
        return None
    pdata.grades = gmap
    pdata.remarks = gradedata.ginfo['REMARKS']

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
    from wz_core.template import openTemplate, getTemplateTags, pupilFields
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
