### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/courses.py - last updated 2020-11-02

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
_MULTI_COMPOSITE = "Fach mit Kürzel „{sid}“ ist Unterfach für mehrere" \
        " Sammelfächer"
_NO_COMPONENTS = "Sammelfach {sid} hat keine Unterfächer"
_NOT_A_COMPOSITE = "Unterfach {sid}: „{sidc}“ ist kein Sammelfach"
_COMPOSITE_IS_COMPONENT = "Fach-Kürzel „{sid}“ ist sowohl als „Sammelfach“" \
        " als auch als „Unterfach“ definiert"


import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

from collections import namedtuple
SubjectData = namedtuple("SubjectData", ('sid', 'tids', 'composite',
        'report_groups', 'name'))

from core.db import DB
from core.base import str2list
from local.grade_config import (NULL_COMPOSITE, NOT_GRADED)
from tables.spreadsheet import Spreadsheet


class CourseError(Exception):
    pass


class Subjects:
    """Manage the SUBJECT and CLASS_SUBJECT tables.
    """
    def __init__(self, schoolyear):
        self.schoolyear = schoolyear
        self.dbconn = DB(schoolyear)
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
        """Return a list of <SubjectData> named-tuples for the given class.
        Only subjects relevant for grade reports are included, i.e. those
        with non-empty report_groups (see below). That does not mean
        they will all be included in the report – that depends on the
        slots in the template.
        Each element has the following fields:
            sid: the subject tag;
            tids: a list of teacher ids, empty if the subject is a composite;
            composite: if the subject is a component, this will be the
                sid of its composite; if the subject is a composite, this
                will be the list of components, each is a tuple
                (sid, weight); otherwise the field is empty;
            report_groups: a list of tags representing a particular block
                of grades in the report template;
            name: the full name of the subject.
        "Composite" grades are marked in the database by having no tids.
        Grade "components" are marked by having '*' as the first character
        of their GRADE field. The first element of this field (after
        stripping the '*') is the composite subject tag.
        *** Weighting of components ***
         Add to composite in FLAGS field: *Ku:2  for weight 2.
        Weights should be <int>, to preserve exact rouding.
        """
        composites = {}
        subjects = []
        for sdata in self.for_class(klass):
            sid = sdata['SID']
            _rgroups = sdata['SGROUPS']
            if (not _rgroups) or _rgroups == NOT_GRADED:
                # Subject not relevant for grades
                continue
            rgroups = _rgroups.split()
            flags = sdata['FLAGS']
            comp = None     # no associated composite
            if flags:
                for f in flags.split():
                    if f[0] == '*':
                        # This subject is a grade "component"
                        if comp:
                            # >1 "composite"
                            raise CourseError(_MULTI_COMPOSITE.format(
                                    sid = sid))
                        # Get the associated composite and the weighting:
                        comp = f[1:]    # remove the '*'
                        try:
                            comp, _weight = comp.split(':')
                        except ValueError:
                            weight = 1
                        else:
                            weight = int(_weight)
                        if comp == NULL_COMPOSITE:
                            continue
                        try:
                            composites[comp].append((sid, weight))
                        except KeyError:
                            composites[comp] = [(sid, weight)]
            tids = sdata['TIDS']
            if tids:
                tids = tids.split()
            else:
                # composite subject
                tids = None
                if comp:
                    raise CourseError(_COMPOSITE_IS_COMPONENT.format(
                            sid = sid))
                # The 'composite' field must be modified later
            subjects.append(SubjectData(sid, tids, comp, rgroups,
                    sdata['SUBJECT']))
        ### Add the 'composite' field to composite subjects,
        ### check that the referenced composites are valid,
        ### check that all composites have components.
        result = []
        for sbjdata in subjects:
            if sbjdata.tids:
                # Not a composite
                result.append(sbjdata)
            else:
                # A composite
                try:
                    comp = composites.pop(sbjdata.sid)
                except KeyError:
                    raise CourseError(_NO_COMPONENTS.format(sid = sbjdata.sid))
                result.append(sbjdata._replace(composite = comp))
        for sid, sid_w_list in composites.items():
            # Invalid composite,
            # more than one is not very likely, just report the first one
            raise CourseError(_NOT_A_COMPOSITE.format(
                    sidc = sid, sid = sid_w_list[0][0]))
        return result



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
    print("\n**** Subject data for class 11: grading ****")
    for sdata in subjects.grade_subjects('11'):
        print("  ++", sdata)
