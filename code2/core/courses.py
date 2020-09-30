### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/courses.py - last updated 2020-09-27

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
_UNKNOWN_SID = "Fach-Kürzel „{sid}“ ist nicht bekannt"
_INVALID_STREAMS_FIELD = ("In Tabelle CLASS_SUBJECT: ungültiges GRP_Feld für"
        " Fach-Kürzel „{sid}“ ({grp})")
_COMPOSITE_IS_COMPONENT = ("Fach-Kürzel „{sid}“ ist sowohl als „Sammelfach“"
        " als auch als „Unterfach“ definiert")
_UNUSED_COMPOSITE = "Unterfach {sid}: Sammelfach „{sidc}“ wird nicht benutzt"
_UNKNOWN_COMPOSITE = "Unterfach {sid}: Sammelfach „{sidc}“ ist nicht definiert"
_NOT_A_COMPOSITE = "Unterfach {sid}: „{sidc}“ ist kein Sammelfach"
_NO_COMPONENTS = "Sammelfach {sid} hat keine Unterfächer"


import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

from collections import namedtuple
SubjectData = namedtuple("SubjectData", ('streams', 'composite', 'tids',
        'name'))

from core.db import DB
from core.base import str2list
from local.grade_config import (NULL_COMPOSITE, NOT_GRADED, ALL_STREAMS,
        all_streams)
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
            return list(self.dbconn.select('CLASS_SUBJECT', CLASS = klass))
#
    def grade_subjects(self, klass, stream = None):
        """Return a mapping {sid -> subject data} for the given class.
        Only subjects relevant for grade reports are included. The subject
        data is in the form of a <SubjectData> named tuple with fields:
            streams: a list of streams for which this subject is relevant;
            composite: a list of sids for which the subject is a component
                (may be more than one entry, in case the streams are
                handled differently);
            tids: a list of teacher ids, empty if the subject is a composite;
            name: the full name of the subject.
        If <stream> is supplied, only subjects relevant for this stream
        will be included.
        """
        composites = {}
        subjects = {}
        for sdata in self.for_class(klass):
            sid = sdata['SID']
            comp = sdata['GRADE']
            if comp == NOT_GRADED:
                continue
            groups = str2list(sdata['STREAMS'])
            if not groups:
                # Subject not relevant for grades
                continue
            try:
                groups.remove(ALL_STREAMS)
            except ValueError:
                # Check streams
                streams = []
                for g in all_streams(klass):
                    try:
                        groups.remove(g)
                    except ValueError:
                        continue
                    streams.append(g)
                # If <streams> is still empty, <groups> will not be,
                # which will lead to an exception below.
            else:
                streams = all_streams(klass)
            if groups:
                raise CourseError(_INVALID_STREAMS_FIELD.format(
                        sid = sid, grp = sdata['STREAMS']))
            tids = sdata['TIDS']
            if not tids:
                # composite subject
                if comp:
                    raise CourseError(_COMPOSITE_IS_COMPONENT.format(
                            sid = sid))
                composites[sid] = []
            ### Here is the subject data item:
            subjects[sid] = SubjectData(streams, str2list(comp),
                    str2list(tids), self[sid])

        # Check that the referenced composites are valid and useable,
        # filter for <stream>
        result = {}
        for sid, sbjdata in subjects.items():
            if sbjdata.composite:
                streams = set(sbjdata.streams)
                for sidc in sbjdata.composite:
                    if not streams:
                        raise CourseError(_UNUSED_COMPOSITE.format(
                                sidc = sidc, sid = sid))
                    if sidc == NULL_COMPOSITE:
                        # Must be the last one ...
                        streams.clear()
                        continue
                    try:
                        sbjcomp = subjects[sidc]
                    except KeyError:
                        raise CourseError(_UNKNOWN_COMPOSITE.format(
                                sidc = sidc, sid = sid))
                    if sidc not in composites:
                        # The target is not a composite
                        raise CourseError(_NOT_A_COMPOSITE.format(
                                sidc = sidc, sid = sid))
                    ok = False
                    for s in list(streams):
                        if s in sbjcomp.streams:
                            streams.remove(s)
                            ok = True
                    if not ok:
                        raise CourseError(_UNUSED_COMPOSITE.format(
                                sidc = sidc, sid = sid))
                    composites[sidc].append(sid)

            if (not stream) or (stream in sbjdata.streams):
                # Subject valid for given stream
                result[sid] = sbjdata

        # Check that all composites have components
        for sid, slist in composites.items():
            if not slist:
                raise CourseError(_NO_COMPONENTS.format(sid = sid))

        return result



if __name__ == '__main__':
    _year = 2016
    from core.base import init
    init('TESTDATA')

    dbconn = DB(_year)
    filepath = os.path.join(DATA, 'testing', 'Subjects.ods')
    fname = os.path.basename(filepath)
    with dbconn:
        dbconn.from_table('SUBJECT', filepath)
    filepath = os.path.join(DATA, 'testing', 'Class-Subjects.ods')
    fname = os.path.basename(filepath)
    with dbconn:
        dbconn.from_table('CLASS_SUBJECT', filepath)

    subjects = Subjects(_year)
    print("En ->", subjects['En'])
    print("\n**** raw subject data for class 11 ****")
    for row in subjects.for_class('11'):
        print("  ", dict(row))
    print("\n**** Subject data for class 11.RS: grading ****")
    for sid, sdata in subjects.grade_subjects('11', 'RS').items():
        print("  %s:" % sid, sdata)
