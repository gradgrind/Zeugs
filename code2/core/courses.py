### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/courses.py - last updated 2020-10-18

Database access for reading course data.

==============================
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
"""

### Messages
#_INVALID_STREAMS_FIELD = ("In Tabelle CLASS_SUBJECT: ungültiges GRP_Feld für"
_UNKNOWN_SID = "Fach-Kürzel „{sid}“ ist nicht bekannt"
_MULTIPLE_COMPOSITE = ("Fach mit Kürzel „{sid}“ ist Unterfach für mehrere"
        " Sammelfächer")
_COMPOSITE_IS_COMPONENT = ("Fach-Kürzel „{sid}“ ist sowohl als „Sammelfach“"
        " als auch als „Unterfach“ definiert")
_UNUSED_COMPOSITE = "Unterfach {sid}: Sammelfach „{sidc}“ wird nicht benutzt"
#_UNKNOWN_COMPOSITE = "Unterfach {sid}: Sammelfach „{sidc}“ ist nicht definiert"
_NOT_A_COMPOSITE = "Unterfach {sid}: „{sidc}“ ist kein Sammelfach"
_NO_COMPONENTS = "Sammelfach {sid} hat keine Unterfächer"


import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

from collections import namedtuple
SubjectData = namedtuple("SubjectData", ('pgroup', 'composite', 'tids',
        'report_groups', 'name'))

from core.db import DB
from core.base import str2list
from local.grade_config import (NULL_COMPOSITE, NOT_GRADED, ALL_STREAMS,
        all_streams)
from tables.spreadsheet import Spreadsheet


class CourseError(Exception):
    pass

#TODO: Can't index on sid anymore because there is no general sid -> name
# mapping!
class Subjects:
    """Manage the SUBJECT and CLASS_SUBJECT tables.
    """
    def __init__(self, schoolyear):
        self.schoolyear = schoolyear
        self.dbconn = DB(schoolyear)
#
    def __getitem__(self, sid):
        """Return the name of the subject with the given tag.
        """
        with self.dbconn:
            row = self.dbconn.select1('SUBJECT', SID = sid)
        if not row:
            raise KeyError(_UNKNOWN_SID.format(sid = sid))
        return row['SUBJECT']
#
    def for_class(self, klass):
        """Return a list of subject-data rows for the given class.
        """
        with self.dbconn:
            # Use <order> parameter to get table order
            return list(self.dbconn.select('CLASS_SUBJECT',
                    CLASS = klass, order = 'rowid'))
#
    def grade_subjects(self, klass):
        """Return a mapping {sid -> subject data} for the given class.
        Only subjects relevant for grade reports are included, i.e. those
        with non-empty report_groups (see below). That does not mean
        they will all be included in the report – that depends on the
        slots in the template. However, note that "component" subjects
        may be specified withoout a report_group.
        The subject data is in the form of a <SubjectData> named tuple with
        the following fields:
            pgroup: the tag of the pupil-group for which this subject is
                relevant, '*' if whole class;
            composite: if the subject is a component, this will be the
                sid of its composite (the pupil-group must match);
            tids: a list of teacher ids, empty if the subject is a composite;
            report_groups: a list of tags representing a particular block
                of grades in the report template;
            name: the full name of the subject.
        """
        composites = {}
        subjects = {}
        for sdata in self.for_class(klass):
            sid = sdata['SID']
            _rgroups = sdata['GRADE']
            if (not _rgroups) or _rgroups == NOT_GRADED:
                # Subject not relevant for grades
                continue
            rgroups = []    # Collect report_groups
            comp = None     # Associated composite
            for rg in str2list(_rgroups):
                if rg[0] == '*':
                    # It is a component
                    if comp:
                        raise CourseError(_MULTIPLE_COMPOSITE.format(
                                sid = sid))
                    comp = rg[1:]
                    continue
                # report_group
                rgroups.append(rg)

            tids = sdata['TIDS']
            if not tids:
                # composite subject
                if comp:
                    raise CourseError(_COMPOSITE_IS_COMPONENT.format(
                            sid = sid))
                composites[sid] = []
            ### Here is the subject data item:
            pgroup = sdata['GRP']
#TODO: Check validity of <pgroup>? - at least not empty ...
            if not pgroup:
                print("NO PUPIL GROUP: %s" % sid)
                continue

            subjects[sid] = SubjectData(pgroup, comp, str2list(tids),
                    rgroups, sdata['SUBJECT'])
        ### Check that the referenced composites are valid
        # For checking that all composites have components:
        cset = set(composites)
        for sid, sbjdata in subjects.items():
            if sbjdata.composite:
                sidc = sbjdata.composite
                if sidc == NULL_COMPOSITE:
                    continue
                if sidc not in composites:
                    # The target is not a composite
                    raise CourseError(_NOT_A_COMPOSITE.format(
                            sidc = sidc, sid = sid))
                # Check pupil group
                cdata = subjects[sbjdata.composite]
                if cdata.pgroup != '*' and cdata.pgroup != sbjdata.pgroup:
                    # group mismatch
                    raise CourseError(_GROUP_MISMATCH.format(
                            sidc = sidc, sid = sid))
                try:
                    cset.remove(sidc)
                except:
                    pass
        # Check that all composites have components
        if cset:
            raise CourseError(_NO_COMPONENTS.format(sids = repr(cset)))
        return subjects



if __name__ == '__main__':
    _year = 2016
    from core.base import init
    init('TESTDATA')

    dbconn = DB(_year)
    filepath = os.path.join(DATA, 'testing', 'Class-Subjects.ods')
    fname = os.path.basename(filepath)
    with dbconn:
        dbconn.from_table('CLASS_SUBJECT', filepath)

    subjects = Subjects(_year)
    print("\n**** raw subject data for class 11 ****")
    for row in subjects.for_class('11'):
        print("  ", dict(row))
    print("\n**** Subject data for class 11.RS: grading ****")
    for sid, sdata in subjects.grade_subjects('11').items():
        print("  %s:" % sid, sdata)
