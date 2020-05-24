### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades_user.py

Last updated:  2020-05-24

Flask Blueprint for handling user acces to grades, especially for
entering/editing grades.

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

#TODO!

from .grades_base import bp, _HEADING, _BPNAME


# Messages
_KLASS_AND_STREAM = ("Klasse {klass} kommt in GRADES/REPORT_CLASSES sowohl"
        " als ganze Klasse als auch mit Gruppen vor")
_NO_CLASSES = "Keine Klassen für Halbjahr {term} [in wz_compat/grade_classes.py]"


import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, abort, redirect, flash, make_response)
from flask import current_app as app

from flask_wtf import FlaskForm
#from wtforms import SelectField, TextAreaField
#from wtforms.fields.html5 import DateField
#from wtforms.validators import InputRequired, Optional #, Length
#from flask_wtf.file import FileField, FileRequired, FileAllowed

#from wz_core.configuration import Dates
#from wz_core.courses import CourseTables
#from wz_core.pupils import Pupils, Klass
#from wz_grades.gradedata import db2grades

#from wz_core.db import DBT
#from wz_table.dbtable import readPSMatrix
#from wz_grades.gradedata import (grades2db, db2grades,
#        getGradeData, GradeReportData, singleGrades2db)
#from wz_compat.grade_classes import gradeGroups
#from wz_compat.gradefunctions import gradeCalc
#from wz_core.teachers import User
from wz_grades.teachergrades import TeacherGradeGroups


@bp.route('/group_user', methods=['GET'])
def group_user():
    """Present the user with a choice of pupil-group/subject pairs.
    Only those for which the user is (at least jointly) responsible
    will be shown. However, note that teachers are allocated to classes
    and not streams, so some groups may be shown for which the teacher
    is not responsible.
    """
    session.pop('admin_grades', None)   # Flag "own grades"
    schoolyear = session['year']
    tidmap = REPORT.wrap(TeacherGradeGroups, schoolyear, suppressok = True)
    if tidmap:
        ugroups = None
        user = session.get('user_id')
        if user:
            uperms = session.get('permission')
            if uperms:
                if 'u' in uperms:
                    try:
                        ugroups = tidmap[user]
                    except:
                        pass
        if ugroups:
            return render_template(os.path.join(_BPNAME, 'index_user.html'),
                                heading = _HEADING,
                                term = tidmap.term,
                                groups = ugroups)

        flash("Keine Zeugnisgruppen für %s" % (user or "'?'"), "Warning")
    return redirect(url_for('bp_grades.index'))


@bp.route('/group_admin', methods=['GET'])
def group_admin():
    uperms = session.get('permission')
    if not (uperms and 's' in uperms):
        abort(404)
    schoolyear = session['year']
    tidmap = REPORT.wrap(TeacherGradeGroups, schoolyear, suppressok = True)
    if tidmap:
        return render_template(os.path.join(_BPNAME, 'group_admin.html'),
                        heading = _HEADING,
                        term = tidmap.term,
                        groups = tidmap.kslist)
    return redirect(url_for('bp_grades.index'))


@bp.route('/group_select/<group>', methods=['GET'])
def group_select(group):
    uperms = session.get('permission')
    if not (uperms and 's' in uperms):
        abort(404)
    schoolyear = session['year']
    tidmap = REPORT.wrap(TeacherGradeGroups, schoolyear, suppressok = True)
    if tidmap:
        sid2tids = tidmap.getGradeCourses(group)
        session['admin_grades'] = group  # Flag "anyone's grades"
        return render_template(os.path.join(_BPNAME, 'subject_admin.html'),
                        heading = _HEADING,
                        term = tidmap.term,
                        subjects = sid2tids)
    return redirect(url_for('bp_grades.index'))


@bp.route('/subject_user/<group>/<sid>', methods=['GET', 'POST'])
def subject_user(group, sid):
    def getGrades():
        tidmap = TeacherGradeGroups(schoolyear)
        tidmap.grades = tidmap.groupSubjectGrades(group, sid)
        return tidmap

    schoolyear = session['year']
    tidmap = REPORT.wrap(getGrades, suppressok = True)
    if not tidmap:
        return redirect(request.referrer)
    try:
        user = session['user_id']
        uperms = session['permission']
    except:
        abort(404)
    if 's' in uperms:
        sname = tidmap.courses.subjectName(sid)
    else:
        if 'u' not in uperms:
            abort(404)
        try:
            tmap = tidmap[user]
            sname = tmap[group][sid]
        except:
            abort(404)

    form = FlaskForm()
    if app.isPOST(form):
        # POST
        count, ecount = 0, 0
        for gdata, grade in tidmap.grades:
            pdata = gdata.pdata
            pid = pdata['PID']
            g = request.form['P_' + pid]
            if g == '?':
                if grade:
                    flash("Eine Note kann nicht auf '?' gestzt werden: %s"
                            % pdata.name(), "Error")
                    ecount += 1
            elif g != grade:
                if REPORT.wrap(gdata.updateGrades, {sid: g}, user = user,
                        suppressok = True) == []:
                    flash("NEW GRADE for %s: %s" % (pdata.name(), g), "Info")
                    count += 1
                else:
                    ecount += 1
        if count:
            flash("%d Note(n) geändert" % count, "Info")
        if ecount:
            flash("Mit Fehlern abgeschlossen", "Error")
        if count or ecount:
            return redirect(request.path)
        flash("Keine Noten geändert im Fach %s" % sname, "Info")
        return redirect(url_for('bp_grades.group_select', group = group)
                if session.get('admin_grades')
                else url_for('bp_grades.group_user'))

    # GET
    return render_template(os.path.join(_BPNAME, 'subject_grades.html'),
                        heading = _HEADING,
                        form = form,
                        group = group,
                        term = tidmap.term,
                        sname = sname,
                        grades = tidmap.grades)
