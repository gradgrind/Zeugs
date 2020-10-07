### python >= 3.7
# -*- coding: utf-8 -*-

"""
grades/makereports.py

Last updated:  2020-10-02

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


import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

## Messages
_NO_ISSUE_DATE = "Kein Ausstellungsdatum für Klasse {cs}"
_NO_GRADES_DATE = "Kein Notendatum (Notenkonferenz) für Klasse {cs}"
_INVALID_TERM_GROUP = "Keine Notenzeugnis-Vorlage für Klasse {cs}, Anlass {term}"
_NO_GRADE_TEMPLATE = "Keine Notenzeugnis-Vorlage für Klasse {cs}: {rtype}"
_PUPILS_NOT_IN_CLASS_STREAM = "BUG: Pupils not in class {group}\n  {names}"
_GRADE_WRONG_CLASS_STREAM = "{name} ist in Klasse {cs}, aber Noten in Klasse {csn}"
_GRADES_FINALISED = "Das Zeugnis für {name} wurde schon fertiggestellt"
_NO_GRADES_TERM = "Keine Noten für {name}"
#?
#_BAD_TERM_GROUP = ("Keine Zeugnistypen sind vorgesehen für Halbjahr {term}"
#        "in Klasse {group}")
_NO_GRADES_ENTRY = "BUG: No grades for {name} on {date}"
#_NO_TEMPLATE = "Keine Notenzeugnis-Vorlage für Klasse {group}:\n"
#        "Halbjahr: {term}, Zeugnistyp: {rtype}"
#_BAD_REPORT_TYPE = ("Keine Notenzeugnis-Vorlage für Klasse {group}:\n"
#        "Halbjahr: {term}, Zeugnistyp: {rtype}")

#?
_MADEKREPORTS = "Notenzeugnisse für Klasse {ks} wurden erstellt"
_NOPUPILS = "Notenzeugnisse: keine Schüler"
_MADEPREPORT = "Notenzeugnis für {pupil} wurde erstellt"
_NO_GRADES = "Keine Noten für {pname} => kein Zeugnis"
_WRONG_GROUP = "{pname} hat die Gruppe gewechselt => kein Zeugnis"
_WRONG_RTYPE = "Zeugnistyp für {pname} ist {rtype} => kein Zeugnis"
_WRONG_DATE = "Ausstellungsdatum ({date}) für {pname} weicht vom Standard ab"
_WRONG_GDATE = "Konferenzdatum ({date}) für {pname} weicht vom Standard ab"
_BAD_DATE_GROUP = "Gruppe {group} ist keine Zeugnisgruppe"
_TOO_MANY_SUBJECTS = ("Zu wenig Platz für Fachgruppe {group} in Vorlage:"
        "\n  {template}\n  {pname}: {sids}")

from types import SimpleNamespace

from core.base import Dates
from core.pupils import Pupils
from core.db import DB
from local.base_config import print_schoolyear
from local.grade_config import (GradeConfigError, cs_split,
        REPORT_TYPES, GRADE_REPORT_TERM,
        GRADE_REPORT_TEMPLATE, print_level, print_title, print_year)
from local.grade_functions import GradeError, Manager
from grades.gradetable import getGrades, gradeMap
from template_engine.template_sub import Template


def get_template(class_stream, report_type = None):
    """If <report_type> is supplied, return the corresponding template
    file (name).
    Otherwise return a list of (report type, template name) tuples for
    the given class/group.
    """
    rtlist = GRADE_REPORT_TEMPLATE.get(class_stream)
    if not rtlist:
        klass, stream = cs_split(class_stream)
        if stream:
            rtlist = GRADE_REPORT_TEMPLATE.get(klass)
        if not rtlist:
            rtlist = GRADE_REPORT_TEMPLATE['*']
    if report_type:
        for rtype, tfile in rtlist:
            if rtype == report_type:
                return tfile
        raise GradeConfigError(_NO_GRADE_TEMPLATE.format(cs = class_stream,
                rtype = report_type))
    return rtlist

###

def makeReports(schoolyear, occasion, class_stream, pids = None):
    """Generate a single file containing grade reports for a group of
    pupils. The group is supplied as <class_stream>, which can be a class
    name or a class name with stream tag (e.g. '11:Gym').
    A subset of the group can be chosen by passing a list of pupil-ids
    as <pids>.
    The grade information is extracted from the database for the given
    school-year and "occasion" (term or other category).
    If double-sided printing is to be done, some care will be necessary
    with the template design and processing to ensure that empty pages
    are inserted as necessary.
    """
    data = SimpleNamespace()
    data.class_stream = class_stream
    data.klass, data.stream = cs_split(class_stream)
    data.schoolyear = schoolyear
    data.occasion = occasion
    data.pupils = Pupils(schoolyear)
    data.dmap = {}

    try:
        data.report_type = GRADE_REPORT_TERM[occasion][class_stream][0]
    except KeyError as e:
        raise GradeConfigError(_INVALID_TERM_GROUP.format(
                term = occasion, cs = class_stream)) from e
    data.dmap = {'REPORT': REPORT_TYPES[data.report_type]}

    dbconn = DB(schoolyear)
    with dbconn:
        row = dbconn.select1('OCCASION_INFO',
                OCCASION = occasion, INFO = 'ISSUE_D-' + class_stream)
        if row:
            issue_date = row['VALUE']
            data.dmap['ISSUE_D'] = issue_date
        else:
            raise GradeConfigError(_NO_ISSUE_DATE.format(cs = class_stream))

        row = dbconn.select1('OCCASION_INFO',
                OCCASION = occasion, INFO = 'GRADES_D-' + class_stream)
        if row:
            data.dmap['GRADES_D'] = row['VALUE']
        else:
            raise GradeConfigError(_NO_GRADES_DATE.format(cs = class_stream))

#  Other items depending on locality, etc.?

    # Get template
    data.template = Template(get_template(class_stream, data.report_type))
    # Get pupils' data
    pdata_list = data.pupils.classPupils(data.klass, data.stream,
            issue_date)
    if pids:
        pid_set = set(pids)
        pltemp = pdata_list
        pdata_list = []
        for pdata in pltemp:
            try:
                pid_set.remove(pdata['PID'])
            except KeyError:
                # Don't include this pupil
                continue
            pdata_list.append(pdata)
        fail_list = [data.pupils.pid2name(pid) for pid in pid_set]
        if fail_list:
            raise Bug(_PUPILS_NOT_IN_CLASS_STREAM.format(
                    group = data.class_stream,
                    names = ', '.join(fail_list)))
    data.plist = []
    for pdata in pdata_list:
        # Get grades
        grades = getGrades(data.schoolyear, pdata['PID'], data.occasion)
        if not grades:
            raise GradeError(_NO_GRADES_TERM.format(
                    name = data.pupils.pdata2name(pdata)))
        # Check for already "finalised" grades. This assumes that the
        # ISSUE_D, GRADES_D (and COMMENTS) fields are all set at the same
        # time as REPORT_TYPE.
        if grades['REPORT_TYPE']:
            raise GradeError(_GRADES_FINALISED.format(
                    name = data.pupils.pdata2name(pdata)))
        # Check that class and stream of pupil match the <data> versions
        data.gstream = grades['STREAM']
        if grades['CLASS'] == data.klass:
            if (not data.stream) or data.gstream == data.stream:
                # Include pupil
                data.plist.append((pdata,
                        Manager(data.schoolyear, data.klass,
                                data.stream, gradeMap(grades))))
                continue
        csgrades = cs_join(grades['CLASS'], data.gstream)
        raise GradeError(_GRADE_WRONG_CLASS_STREAM.format(
                name = data.pupils.pdata2name(pdata),
                cs = data.class_stream, csn = csgrades))
    return _build(data)

###

def _build(data):
    allkeys = data.template.allkeys()
#    return allkeys

    texlist = []
    subdata = {
        'SCHOOLYEAR': print_schoolyear(data.schoolyear),
        'REPORT': print_title(data.report_type),
        'CLASSYEAR': print_year(data.klass),
        'CLASS': data.klass,

#TODO
    }
    for pdata, gman in data.plist:
        gman.addDerivedEntries()
#?
        gdata = dict(pdata)
# Should LEVEL be user-input? If so, where would it be stored?
        gdata['LEVEL'] = print_level(data.report_type,
                gman.XINFO['Q12'], data.klass, data.gstream)

###### For Sek I template
# 'gleichstellung':
#   'h' (Hauptschulabschluss)
#   '0' (none)
# 'abschluss':
#   'a' (Abschluss)
#   'v' (Versetzung in die Qualifikationsphase)
#   'x' (Abgang)
#   '0' (normales Zeugnis)
###
# Zeugnis – with or without "Versetzung" (12:Gym, 11:Gym) – needs GRADES_D
# Abschluss – (12:RS – Erw/RS/HS/..., 11:RS – RS/HS/..., 11&12:HS?);
#   what about "None"?
# Abgang – with or without "Gleichstellungsvermerk" (12:Gym – Erw/RS/HS,
#     sonst – HS/None)
# Orientierungsnoten / Zwischenzeugnis – nothing special


        gdata.update(subdata)
        gdata.update(data.dmap)
        Dates.convert_dates(gdata)

        return gdata
#TODO: divide up subjects and grades into groups
# Try (for Sek I) without group lists, using composite status to decide?




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

# Qualification (not all valid in every group): HS, RS, Erw(/13), Q, None.
# The meaning can vary according to year and stream.




class GradeReports:

#    def selectTemplates(self):
#        """Fetch a list of possible report types and the associated template
#        name based on the class/group and term.
#
#??
#        If term is <None>, the types available for "irregular" reports (not
#        at the end of a term) are returned.
#        <class_stream> may just be a class, but it may also have a stream tag.
#        There must be a matching entry in the configuration module.
#        Return a list of tuples:
#            [(report type, template name), ...].
#        The first entry is the default.
#        """
#        if term:
#            try:
#                return GRADE_REPORT_TERM[self.term][self.class_stream]
#            except KeyError:
#                pass
#            # If <class_stream> includes a stream, try just the class
#            if self.stream:
#                try:
#                    return GRADE_REPORT_TERM[self.term][self.klass]
#                except KeyError:
#                    pass
#            raise GradeConfigError(_BAD_TERM_GROUP.format(
#                    term = self.term, group = self.class_stream))
#        else:
#            try:
#                return GRADE_REPORT_ANYTIME[self.class_stream]
#            except KeyError:
#                pass
#            # If <class_stream> includes a stream, try just the class
#            if self.stream:
#                try:
#                    return GRADE_REPORT_ANYTIME[self.klass]
#                except KeyError:
#                    pass
#            return GRADE_REPORT_ANYTIME['*']


    def makeOneReport(self, schoolyear, pid, term_or_date):
        """Generate a file containing the grade report for the given pupil.
        <schoolyear> and <term_or_date> determine which grade entry in the
        database should be used.
        <term_or_date> can be either a term or the date-of-issue.
        """
        self.schoolyear = schoolyear
        self.pupils = Pupils(schoolyear)
        # First try to find grades assuming <term_or_date> is a term
        grades = getGrades(schoolyear, pid, term_or_date)
        if not grades:
            # Otherwise assume it is a date
            for grades in getGrades(schoolyear, pid):
                if grades['ISSUE_D'] == term_or_date:
                    break
            else:
                raise GradeError(_NO_GRADES_ENTRY.format(
                        name = self.pupils.pid2name(pid), date = term_or_date))
        pdata = self.pupils[pid]

        self.issue_date = grades['ISSUE_D']
        self.term = grades['TERM']
        self.grades_date = grades['GRADES_D']

        # Get template
        self.klass = grades['CLASS']
        self.stream = grades['STREAM']
        self.class_stream = self.klass
        if self.stream:
            self.class_stream += '.' + self.stream
        for rt, self.template_name in selectTemplates():
            if rt == self.report_type:
                break
        else:
            raise GradeConfigError(_NO_TEMPLATE.format(
                    group = self.class_stream, term = self.term,
                    rtype = self.report_type))
        gmap = gradeMap(grades)
        pdata.grades = Manager(self.schoolyear, self.klass,
                self.stream, gmap)
        self.pdata_list = [pdata]
        return self.build()

###


#TODO: grades
# The grades should be supplied as a list of pupil-grade tuples.
# The pupil-grade tuples should be <Dictuples>.
# Initially these should be purely "real" grades for actual graded courses.
# The various special fields are then obtained by processing the grades
# (possibly in conjunction with other data).


#TODO: do two substitutions? Firstly the individual data (reporting no
# errors), then join all the bits together and substitute the general
# data (with error reporting)
        data.update(general_data)


        # Substitute pupil data, ignore missing fields
        texlist.append(template.substitute(data, tag='body')[0])
        tex0 = '\n\n\\newpage\n\n'.join(texlist)
        # Insert in frame, substitute general data
#TODO: gather all the parameters in an info-block somehow?
        gdata = prepareData(schoolyear, class_stream, term,
                report_type, issuedate, fixdate)
        tex =insert_and_substitute(gdata, ':', body=tex0)
        return template.makepdf(tex)



def prepareData(schoolyear, class_stream):
    """This can contain region/locality-dependent code preparing the
    information needed by the template.
    """
    data = {}


    for k, v in data.items():
        if k.endswith('.DAT'):
            data[k] = date_conv(v)
    # Assume the class always starts with two digits.
#TODO: How to get <class_stream>?
    data['Jahrgang'] = class_stream[:2]
#TODO: <schoolyear>?
    data['Schuljahr'] = '%d – %d' % (schoolyear - 1, schoolyear)
    data.update(SCHOOL_DATA)




QUALI_VALID = { # Levels of qualification for stream and class.
    'HS': {'*': ['HS', '-']},
    'RS': {'12': ['Erw', 'RS', 'HS', '-'],
           '*': ['HS', '-']},
    'Gym': {'12': ['Erw', 'RS', 'HS'],
            '11': ['Q', 'HS', '-'],
            '*': ['HS', '-']}
}



#
#def getTemplateName(class_stream, term = None, report_type = None):
#    mapping = GRADE_REPORT_TERM[term] if term else GRADE_REPORT_ANYTIME
#    gtemplates = mapping.get(class_stream)
#    if not gtemplates:
#        gtemplates = mapping.get(class_stream.split('.')[0])
#        if not gtemplates:
#            return None
#    if report_type:
#        for rtype, gtemplate in gtemplates:
#            if report_type == rtype:
#                return gtemplate
#        return None
#    else:
#        #
#        return gtemplates[0]




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
        REPORT.Fail(_NO_ISSUE_DATE, cs = ks)
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


if __name__ == '__main__':
    _year = 2016
    _issue = '2016-06-16'
    from core.base import init
    init('TESTDATA')

    _class_stream = '11'
    _term = '2'
    _grades_date = '2016-06-06'

    dbconn = DB(_year)
    with dbconn:
        key = 'ISSUE_D-' + _class_stream
        dbconn.updateOrAdd('OCCASION_INFO', {
                    'OCCASION': _term,
                    'INFO': key,
                    'VALUE': _issue
                }, OCCASION = _term, INFO = key)
        key = 'GRADES_D-' + _class_stream
        dbconn.updateOrAdd('OCCASION_INFO', {
                    'OCCASION': _term,
                    'INFO': key,
                    'VALUE': _grades_date
                }, OCCASION = _term, INFO = key)

    gr = makeReports(_year, _term, _class_stream)
#    print("\nKeys:", sorted(gr))
    print("\nPupil data:", gr)


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
