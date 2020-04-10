### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/abitur.py

Last updated:  2020-04-10

Flask Blueprint for abitur reports

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

_HEADING = "Abitur"     # page heading

ABIYEAR = "13"          # Abitur only possible in this year

# Messages
_NOT_ABI_YEAR = "{pname} (Klasse {klass}) ist nicht in einer Abiturklasse."


#TODO: check imports ...
import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, abort, redirect, flash, make_response)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_grades.gradedata import gradeInfo, getGrade
from wz_grades.gradetable import makeBasicGradeTable
from wz_grades.makeabi import saveGrades, makeAbi
from wz_compat.grade_classes import (choices2db, choiceTable,
        abi_sid_name, abi_klausuren,
        abi_klausur_classes, abi_choice_classes)


# Set up Blueprint
_BPNAME = 'bp_abitur'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


#TODO?
#@bp.route('/', methods=['GET'])
#def index():
#    return render_template(os.path.join(_BPNAME, 'abi-index.html'),
#                            heading=_HEADING)

@bp.route('/tests/<testn>/<klass>', methods=['GET'])
@bp.route('/tests/<testn>', methods=['GET','POST'])
@bp.route('/tests', methods=['GET'])
def tests(testn = None, klass = None):
    """Manage the results of the scheduled tests (Klausuren) in the
    final class.
    Result tables can be downloaded and uploaded here.
    <testn> is the test number (1-3) preceded by 'T'.
    <klass> is an Abitur class.
    """
    test_vals = abi_klausuren()
    if not testn:
        return render_template(os.path.join(_BPNAME, 'tests_n.html'),
                            heading = _HEADING,
                            tests = test_vals)

    schoolyear = session['year']
    # Get a list of relevant classes
    klasslist = abi_klausur_classes(schoolyear)
    try:
        dfile = session.pop('test_klass')   # download file
    except:
        dfile = None
    if testn not in test_vals:
        abort(404)
#TODO
    if klass:
        if klass not in klasslist:
            abort(404)
        # GET only. Generate the table
        dfile = None    # download file
        ks = Klass(klass)
        # GET: Generate the table
        xlsxBytes = REPORT.wrap(makeBasicGradeTable,
                schoolyear, testn, ks, suppressok = True)
        if xlsxBytes:
            dfile = 'Klausur_%s-%s.xlsx' % (testn[1], klass)
            session['filebytes'] = xlsxBytes
#WARNING: This is not part of the official flask API, it might change!
            if not session.get("_flashes"):
                # There are no messages: send the file for downloading.
                return redirect(url_for('download', dfile = dfile))
            # If there are messages, save the file-name in the
            # session data and then redirect to the page with no
            # <klass> parameter.
            # The template will show the messages
            # and make the file available for downloading.
            session['test_klass'] = dfile
        return redirect(url_for('bp_abitur.tests', testn = testn))

    class UploadForm(FlaskForm):
        upload = FileField('Klausur-Ergebnisse:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Klausur-Ergebnisse')
        ])

    form = UploadForm()
    if app.isPOST(form):
#TODO: like grade table, but check test number
        REPORT.wrap(tests2db, schoolyear, testn, form.upload.data)
        return redirect(url_for('bp_abitur.tests'))

    return render_template(os.path.join(_BPNAME, 'tests.html'),
                            heading = _HEADING,
                            test = testn,
                            klasses = klasslist,
                            dfile = dfile,
                            form = form)


@bp.route('/choices', methods=['GET','POST'])
@bp.route('/choices/<klass>', methods=['GET'])
def choices(klass = None):
    """Manage subject-choice tables for classes/groups with Abitur-
    relevant subjects.
    These tables can be downloaded and uploaded here.
    """
    schoolyear = session['year']
    # Get a list of relevant classes
    klasslist = abi_choice_classes(schoolyear)
    try:
        dfile = session.pop('choices')  # download file
    except:
        dfile = None

    if klass:
        # GET only. Generate the table
        if klass in klasslist:
            xlsxBytes = REPORT.wrap(choiceTable, schoolyear, klass,
                    suppressok = True)
            if xlsxBytes:
                dfile = 'Kurswahl_%s.xlsx' % klass
                session['filebytes'] = xlsxBytes
#WARNING: This is not part of the official flask API, it might change!
                if not session.get("_flashes"):
                    # There are no messages: send the file for downloading.
                    return redirect(url_for('download', dfile = dfile))
                # If there are messages, save the file-name in the
                # session data and then redirect to the class-less page.
                # The template will show the messages
                # and make the file available for downloading.
                session['choices'] = dfile
            return redirect(url_for('bp_abitur.choices'))
        else:
            abort(404)

    class UploadForm(FlaskForm):
        upload = FileField('Kurswahl-Tabelle:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Kurswahl-Tabelle')
        ])

    form = UploadForm()
    if app.isPOST(form):
        REPORT.wrap(choices2db, schoolyear, form.upload.data)
        return redirect(url_for('bp_abitur.choices'))

    return render_template(os.path.join(_BPNAME, 'choices.html'),
                            heading = _HEADING,
                            klasses = klasslist,
                            dfile = dfile,
                            form = form)


@bp.route('/klasses', methods=['GET'])
def klasses():
    """Select school-class. Only year 13 is relevant for Abitur
    reports.
    """
    schoolyear = session['year']
    # Collect list of school-classes.
    # Accept all classes here, then – when it turns out that the class
    # has no possible templates – show a message indicating this state
    # of affairs.
    pupils = Pupils(schoolyear)
    # List the classes with the oldest pupils first, as these are more
    # likely to need grades.
    klasslist = [k for k in pupils.classes() if k >= '13']
    if len(klasslist) == 1:
        # If there is only one class, skip to the pupil list ...
        k = klasslist[0]
        if request.referrer.endswith('/' + k):
            # ... unless we have come from there, in which case go to the
            # grade report dispatcher
            return redirect(url_for('bp_grades.index'))
        else:
            return redirect(url_for('bp_abitur.pupils', klass=k))
    return render_template(os.path.join(_BPNAME, 'klasses.html'),
            heading = _HEADING,
            klasses = klasslist
    )


### Select pupil
@bp.route('/pupils/<klass>', methods=['GET'])
def pupils(klass):
    """Select pupil from given school-class.
    """
    try:
        dfile = session.pop('download')
    except:
        dfile = None
    schoolyear = session['year']
    # Collect list of pupils for this school-class.
    pupils = Pupils(schoolyear)
    # List the classes with the highest first, as these are more
    # likely to need grades.
    _klass = Klass(klass)
    plist = pupils.classPupils(_klass)
    return render_template(os.path.join(_BPNAME, 'pupils.html'),
            heading = _HEADING,
            klass = _klass.klass,
            pupils = plist,
            dfile = dfile
    )


@bp.route('/grades/<pid>', methods=['GET', 'POST'])
def grades(pid):
    """View: enter grades for a pupil.
    """
    class _Form(FlaskForm):
        DATE_D = DateField('Ausstellungsdatum', validators=[InputRequired()])

    def prepare():
        pupils = Pupils(schoolyear)
        pdata = pupils.pupil(pid)
        k = pdata['CLASS']
        if k < ABIYEAR:
            REPORT.Fail(_NOT_ABI_YEAR, klass=k, pname=pdata.name())
        klass = Klass(k)
        subjects = abi_sid_name(schoolyear, pdata)

        # Get any existing grades for this pupil: {sid -> grade}
        # If there is no grade data, use <{}> to satisfy the subsequent code.
        ginfo = gradeInfo(schoolyear, 'A', pid)
        sid2grade = []
        sid2xgrade = []
        date = ginfo['DATE_D'] if ginfo else '?'
        i = 0
        for sid, sname in subjects:
            sid2grade.append(getGrade(schoolyear, ginfo, sid)
                    if ginfo else None)
            if i < 4:
                sid2xgrade.append(getGrade(schoolyear, ginfo, sid + 'N')
                        if ginfo else None)
            i += 1

#TODO: without WTFORMS?

        # Add grade-select fields
        gchoices = [(g, g) for g in gradechoices]
        gchoicesM = [(g, g) for g in gradechoicesM]
        i = 0
        for sid, sname in subjects:
            grade = sid2grade[i]
            if grade not in gradechoices:
                grade = ''
            sfield = SelectField(sname, choices=gchoices, default=grade)
            setattr(_Form, sid, sfield)
            if i < 4:
                # Add (optional) oral exam
                grade = sid2xgrade[i]
                if grade not in gradechoicesM:
                    grade = '*'
                sfield = SelectField("mdl.", choices = gchoicesM,
                        default = grade)
                setattr(_Form, sid + 'N', sfield)
            i += 1
        return subjects, pdata, klass, date

    # Build grade lists. <gradechoicesM> is for the additional oral
    # exams for the first four subjects – these are optional so they
    # can take the value '*' (no exam).
    gradechoices, gradechoicesM = [], []
    for i in range(15, -1, -1):
        g = "%02d" % i
        gradechoices.append(g)
        gradechoicesM.append(g)
    gradechoices.append('')
    gradechoicesM.append('*')

    schoolyear = session['year']
    try:
        subjects, pdata, klass, date = REPORT.wrap(prepare, suppressok=True)
    except TypeError:
        # Return to caller
        return redirect(request.referrer)

    form = _Form()
    if form.validate_on_submit():
        ### POST
        # Get the date of issue
        _d = form.DATE_D.data.isoformat()
        # Get the grades
        grades = {} # for saving grades
        for sid, sname in subjects:
            grades[sid] = form[sid].data
            if not sid.endswith('m'):
                sn = sid + 'N'
                grades[sn] = form[sn].data
        # Save the grades and date to the database
        if REPORT.wrap(saveGrades, schoolyear, pdata, grades, _d,
                suppressok=True):
            # Test whether a report is to be constructed
            if request.form['action'] == 'build':
                pdfBytes = REPORT.wrap(makeAbi, schoolyear, pdata)
                if pdfBytes:
                    session['filebytes'] = pdfBytes
                    session['download'] = 'Abiturzeugnis_%s.pdf' % (
                            pdata['PSORT'].replace(' ', '_'))
                    return redirect(url_for('bp_abitur.pupils',
                            klass = klass.klass))
            else:
                return redirect(url_for('bp_abitur.pupils',
                        klass = klass.klass))

    ### GET
    # Set date (if saved)
    try:
        form.DATE_D.data = datetime.date.fromisoformat(date)
    except ValueError:
        form.DATE_D.data = datetime.date.today()

    return render_template(os.path.join(_BPNAME, 'abitur.html'),
                    heading = _HEADING,
                    form = form,
                    klass = klass.klass,
                    pname = pdata.name(),
                    sids = subjects
                )

