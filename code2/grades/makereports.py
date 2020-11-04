### python >= 3.7
# -*- coding: utf-8 -*-

"""
grades/makereports.py

Last updated:  2020-11-04

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
_MULTI_GRADE_GROUPS = "Fach {sbj} passt zu mehr als eine Fach-Gruppe"
_WARN_NO_GRADE = "Schüler {pid}: keine Note im Fach {sbj}"
_UNEXPECTED_GRADE_GROUP = "Ungültiger Fachgruppe ({tag}) in Vorlage:\n" \
        "  {tpath}"
_NO_SUBJECT_GROUP = "Keine passende Fach-Gruppe für Fach {sbj}"


from core.base import Dates
from core.db import year_path
from core.pupils import Pupils
from core.courses import Subjects
from local.base_config import SCHOOL_NAME, class_year, print_schoolyear
from local.grade_config import MISSING_GRADE, UNGRADED, GradeConfigError, \
        STREAMS, NO_SUBJECT
from local.grade_template import REPORT_TYPES
from grades.gradetable import Grades, GradeTableError


#TODO: Does this handle Abitur reports?

def makeReport1(schoolyear, term_date, pid):
    """Generate the grade report for the given pupil.
    The grade information is extracted from the database for the given
    school-year and "term". In the case of a "non-scheduled" report,
    the date (YYYY-MM-DD) is passed instead of the term.
    A pdf-file is produced, return the file-path.
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
    return buildReports(schoolyear, gdata['TERM'], rtype, group, [gdata])

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
    Return a list of file-paths for the report-type pdf-files.
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
    return [buildReports(schoolyear, term, rtype, group, gdatalist)
            for rtype, gdatalist in greport_type.items()]

###

def buildReports(schoolyear, term, rtype, group, gdata_list):
    """
    """
    ### Pupil data
    pupils = Pupils(schoolyear)
    # The individual pupil data can be fetched using pupils[pid].
    # Fetching the whole class may not be good enough, as it is vaguely
    # possible that a pupil has changed class.

    ### Subject data (for whole class)
    _courses = Subjects(schoolyear)
    klass, streams = Grades.group2klass_streams(group)
    sdata_list = _courses.grade_subjects(klass)

    ### Grade report template
    try:
        GradeTemplate = REPORT_TYPES[rtype]
    except KeyError as e:
        raise Bug("Invalid report type for group %s: %s" %
                (group, rtype)) from e
    gTemplate = GradeTemplate(group, term)

    ## Build the data mappings and generate the reports
    gmaplist = []
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
            gmap[field] = gdata[field] or ''
        gmap['CYEAR'] = class_year(gmap['CLASS'])
        gmap['issued_d'] = gdata['ISSUE_D']     # for file-names
        gmap['ISSUE_D'] = Dates.print_date(gdata['ISSUE_D'])
        gmap['GRADES_D'] = Dates.print_date(gdata['GRADES_D'])

        ## Process the grades themselves ...
        # Sort into grade groups
        grade_map = sort_grade_keys(sdata_list, gdata, gTemplate)
        gmap.update(grade_map)

        ## Add general data
        gmap['SCHOOL'] = SCHOOL_NAME
        gmap['SCHOOLBIG'] = SCHOOL_NAME.upper()
        gmap['schoolyear'] = str(schoolyear)
        gmap['SCHOOLYEAR'] = print_schoolyear(schoolyear)
        gmap['Zeugnis'] = gTemplate.NAME
        gmap['ZEUGNIS'] = gTemplate.NAME.upper()
        # Add local stuff
        gTemplate.quali(gmap)

        gmaplist.append(gmap)

    return gTemplate.make_pdf(gmaplist,
            year_path(schoolyear, Grades.grade_path(term)))

###

def group_grades(all_keys):
    """Determine the subject and grade slots in the template.
    <all_keys> is the complete set of template slots/keys.
    Keys of the form 'G.k.n' are sought: k is the group-tag, n is a number.
    Return a mapping {group-tag -> [index, ...]}.
    The index lists are sorted reverse-alphabetically (for popping).
    Note that the indexes are <str> values, not <int>.
    Also keys of the form 'G.sid' are collected as a set. Such keys are
    returned as the value of the entry with <group-tag = None>.
    """
#    G_REGEXP = re.compile(r'G\.([A-Za-z]+)\.([0-9]+)$')
    tags = {}
    subjects = set()
    for key in all_keys:
        if key.startswith('G.'):
            ksplit = key.split('.')
            if len(ksplit) == 3:
                # G.<group tag>.<index>
                tag, index = ksplit[1], ksplit[2]
                try:
                    tags[tag].add(index)
                except KeyError:
                    tags[tag] = {index}
            elif len(ksplit) == 2:
                # G.<subject tag>
                gsubjects.add(ksplit[1])
    result = {None: subjects}
    for tag, ilist in tags.items():
        result[tag] = sorted(ilist, reverse = True)
    return result

###

def sort_grade_keys(sdata_list, gdata, template):
    """Allocate the subjects and grades to the appropriate slots in the
    template.
    Return a {slot: grade-entry} mapping.
    <sdata_list> is the list of <SubjectData> items,
    <gdata> is the <Grades> instance,
    <template> is a <Template> subclass.
    """
    _grp2indexes = group_grades(template.all_keys())
    tag2indexes = {}
    for tag in template.GROUPS:
        try:
            indexes = _grp2indexes.pop(tag)
        except KeyError:
            # Subjects in this group wil not appear in the report
            tag2indexes[tag] = None
        else:
            tag2indexes[tag] = indexes
    sbj_grades = None       # grade-only entries
    for tag in _grp2indexes:
        if tag:
            raise TemplateError(_UNEXPECTED_GRADE_GROUP.format(tag = tag,
                    tpath = template.template_path))
        else:
            sbj_grades = _grp2indexes[tag]  # set of sids for grade-only

    gmap = {}   # for the result
    # Get all the grades, including composites.
    grades = gdata.get_full_grades(sdata_list)
    for sdata in sdata_list:
        # Get the grade
        g = gdata.print_grade(grades[sdata.sid])
        # Get the subject name
        sbj = sdata.name
        if g == MISSING_GRADE:
            REPORT(_WARN_NO_GRADE.format(pid = gdata['PID'], sbj = sbj))
        if sbj_grades:
            try:
                sbj_grades.remove(sdata.sid)
            except KeyError:
                pass
            else:
                # grade-only entry
                gmap['G.%s' % sdata.sid] = g or UNGRADED
                continue
        if not g:
            # Subject "not chosen", no report entry
            continue
        done = False
        for rg in sdata.report_groups:
            # Get an index
            try:
                ilist = tag2indexes[rg]
            except KeyError:
                continue
            if done:
                raise GradeConfigError(_MULTI_GRADE_GROUPS.format(sbj = sbj))
            if ilist == None:
                # Suppress subject/grade
                done = True
                continue
            try:
                i = ilist.pop()
            except IndexError as e:
                # No indexes left
                raise TemplateError(_NO_SLOT.format(
                        tag = rg, sid = sdata.sid)) from e
            gmap['G.%s.%s' % (rg, i)] = g
            # For the name, strip possible extra bits, after '|':
            gmap['S.%s.%s' % (rg, i)] = sbj.split('|', 1)[0].rstrip()
            done = True
        if not done:
            raise GradeConfigError(_NO_SUBJECT_GROUP.format(sbj = sbj))

    ### Fill unused slots
    if sbj_grades:
        for sid in sbj_grades:
            gmap['G.%s' % sid] = UNGRADED
    for tag, ilist in tag2indexes.items():
        if ilist:
            for i in ilist:
                gmap['G.%s.%s' % (tag, i)] = NO_SUBJECT
                gmap['S.%s.%s' % (tag, i)] = NO_SUBJECT
    return gmap




if __name__ == '__main__':
    _year = 2016
    _issue = '2016-06-16'
    from core.base import init
    init('TESTDATA')

    _group = '12.R'
    _term = '2'
    _grades_date = '2016-06-06'

    for f in makeReports(_year, _term, _group):
        print("\n$$$:", f)

#TODO: make a single report
