### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grade_edit.py

Last updated:  2020-02-29

Flask Blueprint for editing grades (single teacher / subject)

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

#TODO!

_HEADING = "Noten"   # page heading


# Messages
_KLASS_AND_STREAM = ("Klasse {klass} kommt in GRADES/REPORT_CLASSES sowohl"
        " als ganze Klasse als auch mit Gruppen vor")
_NO_CLASSES = "Keine Klassen für Halbjahr {term} [in wz_compat/grade_classes.py]"


import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, abort, redirect, flash, make_response)
#from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Optional #, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed

#from wz_core.configuration import Dates
from wz_core.courses import CourseTables
from wz_core.subjectchoices import pupilFilter
#from wz_core.pupils import Pupils, Klass
from wz_grades.gradedata import db2grades

from wz_core.db import DB
from wz_table.dbtable import readPSMatrix
#from wz_grades.gradedata import (grades2db, db2grades,
#        getGradeData, GradeReportData, singleGrades2db)
from wz_grades.makereports import makeReports, makeOneSheet
from wz_grades.gradetable import makeBasicGradeTable
from wz_compat.grade_classes import gradeGroups
from wz_compat.gradefunctions import gradeCalc


# Set up Blueprint
_BPNAME = 'bp_grade_edit'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
def index():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


@bp.route('/editgrades/<termn>/<ks>/<sid>', methods=['GET', 'POST'])
def editgrades(termn, ks, sid):
    """View: edit the grades for a class/group in a particular subject.
    Respect editing permissions for the user.
    """
    schoolyear = session['year']
    tid = session['user_id']
    klass_stream = Klass(ks)
    courses = CourseTables(schoolyear)
    sid2tlist = courses.classSubjects(klass_stream, 'GRADE', keep=True)
    tlist0 = sid2tlist.get(sid)
    if not tlist0:
        abort(404)
    perms = session['permission']
    if 's' in perms:
        admin = True
    elif 'u' in perms and tid in tlist0:
        admin = False
    else:
        flash("{tid} unterrichtet nicht {sid} in {ks}".format(tid = tid,
                sid = sid, ks = ks), "Error")
#TODO
        # go to subject choice page?

# or just abort?
    # Get pupil/grade list: [(pid, pname, {subject -> grade}), ...]
    pglist = db2grades(schoolyear, termn, klass_stream)

    showlist = []
    for pid, pname, gmap in pglist:
        # Get tlist from {sid -> <TeacherList> instance OR <None>}
        tlist = pupilFilter(schoolyear, sid2tlist, pid).get(sid)
        if tlist:
            grade = gmap.get(sid)
#TODO: getLastTid
            owner = getLastTid(schoolyear, termn, klass_stream, sid)
            editable = admin or (tid in tlist and (not owner or tid == owner))


