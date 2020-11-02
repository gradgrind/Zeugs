### python >= 3.7
# -*- coding: utf-8 -*-

"""
grades/makereports.py

Last updated:  2020-11-02

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
_NO_REPORT_TYPE = "Kein Zeugnistyp für Schüler {pids}"



_NO_ISSUE_DATE = "Kein Ausstellungsdatum für Klasse {cs}"
_NO_GRADES_DATE = "Kein Notendatum (Notenkonferenz) für Klasse {cs}"
_INVALID_TERM_GROUP = "Keine Notenzeugnis-Vorlage für Klasse {cs}, Anlass {term}"
_NO_GRADE_TEMPLATE = "Keine Notenzeugnis-Vorlage für Klasse {cs}: {rtype}"
_PUPILS_NOT_IN_CLASS_STREAM = "BUG: Pupils not in class {group}\n  {names}"
_GRADE_WRONG_CLASS_STREAM = "{name} ist in Klasse {cs}, aber Noten in Klasse {csn}"
_GRADES_FINALISED = "Das Zeugnis für {name} wurde schon fertiggestellt"
_NO_GRADES_TERM = "Keine Noten für {name}"
_GROUP_TOO_SMALL = "Zu viele Fächer in Zeugnisgruppe {tag}"
_MULTIPLE_GROUPS = "Fach {sid} in mehreren Fachgruppen"

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

#from types import SimpleNamespace

from core.base import Dates
from core.pupils import Pupils
from local.base_config import SCHOOL_NAME, class_year, print_schoolyear
from local.grade_template import REPORT_TYPES
from grades.gradetable import Grades, GradeTableError

#from core.db import DB
#from local.base_config import print_schoolyear
#from local.grade_config import (GradeConfigError, cs_split,
#        REPORT_TYPES, GRADE_REPORT_TERM,
#        GRADE_REPORT_TEMPLATE, print_level, print_title, print_year,
#        NO_SUBJECT
#)
#from local.grade_functions import GradeError, Manager

# !!! Should I rather omit the group filtering of the subjects?
# It is rather complicated and still somewhat limited. The simplification
# which could be achieved by removing it could make the whole thing a
# bit more accessible. The basic question is, how much should be
# automated and how much should the operator be expected to do? All sorts
# of things could be automated, checked, calculated, an so on, but at
# what cost in terms of implementation complexity? I suspect it is not
# really worth it.
# This thing with subject list filtering could be better off in the
# hands of the operator ...

# There is also the question of choosing the grade scale and the template.
# This can be left up to the local grade configuration.
# So: retain the groups for grade reports, dump the subject selection based
# on grades. If the subjects diverge a lot between two groups in the same
# class, one could (perhaps?) split the class for the reports ... (not
# likely in a Waldorf school). Or ... have a separate mechanism for
# determining relevant subjects.

#LOOK at single reports – the template subclasses take a GROUP as
# parameter, which a single pupil can't (or at least shouldn't need to)
# provide.

#TODO: Does this handle Abitur reports?
def makeReport1(schoolyear, term_date, pid):
    """Generate the grade report for the given pupil.
    The grade information is extracted from the database for the given
    school-year and "term". In the case of a "non-scheduled" report,
    the date (YYYY-MM-DD) is passed instead of the term.
    A pdf-file is produced.
    """
    ### Fetch grade data
    gdata = Grades.forPupil(schoolyear, term_date, pid)

    ### Get the report type
    rtype = gdata['REPORT_TYPE']
    if not rtype:
        raise GradeTableError(_NO_REPORT_TYPE.format(pids = pid))

    ### Get the grade group and build the report
    # The templates are selected according to pupil-group, so this must
    # be determined, based on the pupil's stream.
    group = Grades.klass_stream2group(gdata['CLASS'], gdata['STREAM'])
    buildReports(schoolyear, rtype, group, [gdata])

###

def makeReports(schoolyear, term, group, pids = None):
    """Generate the grade reports for the given group of pupils.
    The group can be a class name or a class name with a group tag
    (e.g. '12.G') – the valid groups are specified (possibly dependant
    on the term – in the 'grade_config' module.
    A subset of the group can be chosen by passing a list of pupil-ids
    as <pids>.
    The grade information is extracted from the database for the given
    school-year and "term".
    The resulting pdfs will be combined into a single pdf-file for each
    report type. If the reports are double-sided, empty pages can be
    added as necessary.
    """
    ### Fetch grade data and split according to report type
    greport_type = {}
    no_report_type = []
    for gdata in Grades.forGroupTerm(schoolyear, term, group):
        # <forGroupTerm> accepts only valid grade-groups.
        # Check pupil filter, <pids>:
        if pids and (gdata['PID'] not in pids):
            continue
        rtype = gdata['REPORT_TYPE']
        if rtype:
            try:
                greport_type[rtype].append(gdata)
            except KeyError:
                greport_type[rtype] = [gdata]
        else:
            no_report_type.append(gdata['PID'])
    if no_report_type:
        raise GradeTableError(_NO_REPORT_TYPE.format(
                pids = ', '.join(no_report_type)))

    ### Build reports for each report-type separately
    for rtype, gdatalist in greport_type.items():
        buildReports(schoolyear, rtype, group, gdata_list)

###

def buildReports(schoolyear, rtype, group, gdata_list):
    """
    """
    ### Pupil data
    pupils = Pupils(schoolyear)
    # The individual pupil data can be fetched using pupils[pid].
    # Fetching the whole class may not be good enough, as it is vaguely
    # possible that a pupil has changed class.

    ### Subject data (for whole class)
    courses = Subjects(schoolyear)
#TODO: Does this really need to be a mapping? would a list be ok/better?
    sdata_map = courses.grade_subjects(klass)

    ### Grade report template
    try:
        GradeTemplate = REPORT_TYPES[rtype]
    except KeyError as e:
        raise Bug("Invalid report type for group %s: %s" %
                (group, rtype)) from e
    gTemplate = GradeTemplate(group, term)

    ## Build the data mappings and generate the reports
    for gdata in gdata_list:
        gmap = {}
        pid = gdata['PID']
        # Get pupil data, an <sqlite3.Row> instance
        pdata = pupils[pid]
# could just do gmap[k] = pdata[k] or '' and later substitute all dates?
        for k in pdata.keys():
            v = pdata[k]
            if v:
                if k.endswith('_D'):
                    v = Dates.print_date(v)
            else:
                v = ''
            gmap[k] = v
        # Grade parameters, from <Grade> instance
        for field in ('CLASS', 'STREAM', 'TERM', 'REPORT_TYPE',
                'QUALI', 'COMMENT'):
            # The CLASS and STREAM fields overwrite those from the
            # pupil – they could differ ...
            gmap[field] = gdata[field]
        gmap['CYEAR'] = class_year(gmap['CLASS'])
        gmap['issued_d'] = gdata['ISSUE_D']     # for file-names
        gmap['ISSUE_D'] = Dates.print_date(gdata['ISSUE_D'])
        gmap['GRADES_D'] = Dates.print_date(gdata['GRADES_D'])


        ### Process the grades themselves ...

        # ... add composites
#?
        grades = gdata.get_full_grades(sdata_map)
        # ... sort into grade groups
        #


        ### Add general data
        gmap['SCHOOL'] = SCHOOL_NAME
        gmap['SCHOOLBIG'] = SCHOOL_NAME.upper()
        gmap['schoolyear'] = str(schoolyear)
        gmap['SCHOOLYEAR'] = print_schoolyear(schoolyear)
        gmap['Zeugnis'] = gTemplate.NAME
        gmap['ZEUGNIS'] = gTemplate.NAME.upper()
        # Add local stuff
        gTemplate.quali(gmap)

        stream = gdata['STREAM']
        gmap['LEVEL'] = STREAMS[stream] # SekI, not 'Abschluss'


# call gTemplate.make_pdf(self, data_list, working_dir = ???)


# Testing ...
        return gmap







    return






######################?????








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
# in local package ...
        gmap = group_grades(allkeys, gman) #?


def group_grades(allkeys):
    """Determine the subjects and grade slots in the template.
    """
#    G_REGEXP = re.compile(r'G\.([A-Za-z]+)\.([0-9]+)$')
    tags = {}
    subjects = set()
    for key in allkeys:
        if key.startswith('G.'):
            ksplit = key.split('.')
            if len(ksplit) == 3:
                # G.<group tag>.<index>
                tag, index = ksplit[1], int(ksplit[2])
                try:
                    tags[tag].add(index)
                except KeyError:
                    tags[tag] = {index}
            elif len(ksplit) == 2:
                # G.<subject tag>
                gsubjects.add(ksplit[1])
    tags[None] = subjects
    return tags

# Sek I: Non-component grades go to V, components to K. Unused slots
# are filled with '––––––––––'.
def sort_grades(tags, gman):
    gmap = {}
    i_k = 0
    i_v = 0
    for sid, g in gman.items():
#TODO
        if is_component(sid):
            i_k += 1
            if i_k in tags['K']:
#TODO
                gmap['S.K.%02d' % i_k] = subject_name(sid)
                gmap['G.K.%02d' % i_k] = g
            else:
                raise GradeConfigError(_GROUP_TOO_SMALL.format(tag = 'K'))
        else:
            i_v += 1
            if i_v in tags['V']:
#TODO
                gmap['S.V.%02d' % i_v] = subject_name(sid)
                gmap['G.V.%02d' % i_v] = g
            else:
                raise GradeConfigError(_GROUP_TOO_SMALL.format(tag = 'V'))

# If the group tags are in the subject table:
    allsids = set(gman)
    for sid, g in gman.items():
        for gtag in g.grade_tags:
            if gtag[0] == '*':
                # component of  gtag[1:]
                continue
            try:
                gtagmap[gtag].append(sid)
            except KeyError:
                gtagmap[gtag] = [sid]

    sidlist = list(gman)
    # Make lists of indexes, sorted in reverse order (so that they can be
    # "popped" as ascending indexes.
# Rather keep the indexes as strings?
    keys = {}
    #noslot = set()  # set of unused sids
    for tag, indexes in tags.items():
        # keys[tag] = sorted(indexes, reverse = True)

        sidlist = gtagmap.get(tag) or []


        while True:
            try:
                i = indexes.pop()
            except IndexError:
                #noslot.update(sidlist)
                break
            try:
                s = sidlist.pop()
            except IndexError:
                # No subject for slot, set to empty
# Uses string indexes
                gmap['S.%s.%s' % (tag, i)] = NO_SUBJECT
                gmap['G.%s.%s' % (tag, i)] = NO_SUBJECT
            else:
                try:
                    allsids.remove(s)
                except KeyError as e:
                    # This means the subject has been used as member
                    # of another group – this is an error.
                    raise GradeConfigError(_MULTIPLE_GROUPS.format(
                            sid = s)) from e

#TODO
                gmap['S.%s.%s' % (tag, i)] = gman.name(s)
                gmap['G.%s.%s' % (tag, i)] = gman[s]

# Another try ...? I'm not really sure where I'd got to, what I was thinking!
        _sidlist = sidlist.copy()
        for i in sorted(indexes, reverse = True):
            for s in _sidlist:
                pass
#???


#...


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




#TODO: grades
# The grades should be supplied as a list of pupil-grade tuples.
# The pupil-grade tuples should be <Dictuples>.
# Initially these should be purely "real" grades for actual graded courses.
# The various special fields are then obtained by processing the grades
# (possibly in conjunction with other data).




QUALI_VALID = { # Levels of qualification for stream and class.
    'HS': {'*': ['HS', '-']},
    'RS': {'12': ['Erw', 'RS', 'HS', '-'],
           '*': ['HS', '-']},
    'Gym': {'12': ['Erw', 'RS', 'HS'],
            '11': ['Q', 'HS', '-'],
            '*': ['HS', '-']}
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

    _group = '12.R'
    _term = '2'
    _grades_date = '2016-06-06'

    r = makeReports(_year, _term, _group)
    print(" -->", r)
    quit(0)




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
