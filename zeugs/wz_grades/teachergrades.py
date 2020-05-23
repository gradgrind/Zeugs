### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/teachergrades.py

Last updated:  2020-05-23

Manage teacher-class access to grade information.

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

# Messages
_NOT_CURRENT_TERM = "Noten können nur für das „aktive“ Halbjahr eingegeben werden"


import os

from wz_core.configuration import Paths, Dates
from wz_core.courses import CourseTables
from wz_core.pupils import Pupils, Klass
from wz_core.teachers import TeacherData
from wz_grades.gradedata import CurrentTerm, GradeData
from wz_compat.grade_classes import gradeGroups


class TeacherGradeGroups(dict):
    def __init__(self, schoolyear, term = None):
        """Build a mapping: {tid -> {group-name -> {sid, ...}}}.
        Only subjects are included for which grades are expected.
        """
        super().__init__()
        try:
            termdata = CurrentTerm(schoolyear, term)
        except CurrentTerm.NoTerm:
            REPORT.Fail(_NOT_CURRENT_TERM)
        self.term = termdata.TERM
        self.schoolyear = schoolyear
        # Only look at predefined grade groups
        self.kslist = gradeGroups(self.term)
        courses = CourseTables(schoolyear)
        for ks in self.kslist:
            ksname = str(ks)
            sid2tids = courses.classSubjects(ks, 'GRADE')
            for sid, tids in sid2tids.items():
                for tid in tids:
                    try:
                        tmap = self[tid]
                    except:
                        self[tid] = {ksname: {sid}}
                        continue
                    try:
                        tmap[ksname].add(sid)
                    except:
                        tmap[ksname] = {sid}


    def groupSubjectGrades(self, group, sid):
        """Get grades for all pupils in a group and subject.
        """
        pupils = Pupils(self.schoolyear)
        grades = []
        for pdata in pupils.classPupils(group):
            gdata = GradeData(self.schoolyear, self.term, pdata)
            grade = gdata.getGrade(sid)
            grades.append([pdata['PID'], pdata.name(), grade, gdata.user])
        return grades


# So far I have assumed that multiple teachers are handled "manually".
# For a subject in a class there can be more than one teacher. No
# association of teachers with sub-groups (streams) is possible at present.
# IF some further association of pupils to a particular teacher were to
# be implemented, it would need to be handled here, too ...

#DEPRECATED
def tGradeGroups(schoolyear, term = None):
    """Build a mapping: {tid -> {group-name -> {sid, ...}}}.
    Only subjects are included for which grades are expected.
    """
    try:
        termdata = CurrentTerm(schoolyear, term)
    except CurrentTerm.NoTerm:
        REPORT.Fail(_NOT_CURRENT_TERM)
    # Only look at predefined grade groups
    kslist = gradeGroups(termdata.TERM)
    courses = CourseTables(schoolyear)
    tidmap = {}
    for ks in kslist:
        ksname = str(ks)
        sid2tids = courses.classSubjects(ks, 'GRADE')
        for sid, tids in sid2tids.items():
            for tid in tids:
                try:
                    tmap = tidmap[tid]
                except:
                    tidmap[tid] = {ksname: {sid}}
                    continue
                try:
                    tmap[ksname].add(sid)
                except:
                    tmap[ksname] = {sid}
    return tidmap


#DEPRECATED
def groupSubjectGrades(schoolyear, term, group, sid):
    """Get grades for all pupils in a group and subject.
    """
    pupils = Pupils(schoolyear)
    grades = []
    for pdata in pupils.classPupils(group):
        gdata = GradeData(schoolyear, term, pdata)
        grade = gdata.getGrade(sid)
        grades.append([pdata['PID'], pdata.name(), grade])
    return grades




##################### Test functions
_year = 2016
_term = "2"
def test_01 ():
    REPORT.Info("Group and subject lists for each teacher:\n")
    tidmap = TeacherGradeGroups(_year, _term)
    teachers = TeacherData(_year)
    for tid, tmap in tidmap.items():
        REPORT.Test("\n *** %s ***" % teachers.getTeacherName(tid))
        REPORT.Test(" --> %s" % repr(tmap))

def test_02 ():
    ks = Klass('12.Gym')
    sid = 'Ma'
    REPORT.Info("Group %s, Grades in %s:" % (ks, sid))
    tidmap = TeacherGradeGroups(_year, _term)
    grades = tidmap.groupSubjectGrades(ks, sid)
    REPORT.Test(" --> %s" % repr(grades))
