### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/abitur.py

Last updated:  2020-03-14

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
_TOO_MANY_SUBJECTS = "zu viele Fächer (es müssen genau 8 sein): siehe Kurswahl-Tabelle"
_NOT_G = "{i}. Fach: {sid}. Dieses muss gA + schriftlich (Endung '.g') sein."
_NOT_E = "{i}. Fach: {sid}. Dieses muss eA (Endung '.e') sein."
_NOT_M = "{i}. Fach: {sid}. Dieses muss mündlich (Endung '.m') sein."
_NOT_ABI_YEAR = "{pname} (Klasse {klass}) ist nicht in einer Abiturklasse."
_SUBJECT_CHOICE = "Unerwarte Abifächer: {sids}"


#TODO: check imports ...
import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, abort, redirect, flash, make_response)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired#, Optional , Length
from flask_wtf.file import FileField, FileRequired, FileAllowed

#from wz_core.configuration import Dates
from wz_core.pupils import Pupils, Klass
from wz_core.courses import CourseTables
from wz_grades.gradedata import getGradeData#, grades2db, db2grades,
#        getGradeData, GradeReportData, singleGrades2db)
from wz_grades.makeabi import saveGrades, makeAbi
from wz_compat.grade_classes import choices2db, choiceTable, abi_sids

# Set up Blueprint
_BPNAME = 'bp_abitur'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


#TODO
@bp.route('/', methods=['GET'])
def index():
    return render_template(os.path.join(_BPNAME, 'abi-index.html'),
                            heading=_HEADING)


@bp.route('/choices', methods=['GET','POST'])
def choices():

    class UploadForm(FlaskForm):
        upload = FileField('Kurswahl-Tabelle:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Kurswahl-Tabelle')
        ])

    schoolyear = session['year']
    form = UploadForm()
    if form.validate_on_submit():
        REPORT.wrap(choices2db, schoolyear, form.upload.data)

    pupils = Pupils(schoolyear)
    # List the classes.
    klasslist = [klass for klass in pupils.classes('Gym')
            if klass.startswith('12') or klass.startswith('13')]
    try:
        download = session.pop('download')
    except:
        download = None
    return render_template(os.path.join(_BPNAME, 'choices.html'),
                            heading=_HEADING,
                            klasses=klasslist,
                            dfile=download,
                            form=form)


@bp.route('klass_choices/<klass>', methods=['GET'])
def klass_choices(klass):
    """Generate editable subject-choice table to download.
    """
    schoolyear = session['year']
    pdfBytes = REPORT.wrap(choiceTable, schoolyear, klass)
    session['filebytes'] = pdfBytes
    session['download'] = 'Kurswahl_%s.xlsx' % klass
    return redirect(url_for('bp_abitur.choices'))





### Select school-class
@bp.route('/klasses', methods=['GET'])
def klasses():
    """View: select school-class. Only year 13 is relevant for Abitur
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
    """View: select pupil from given school-class.
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

        courses = CourseTables(schoolyear)
        sid2tlist = courses.classSubjects(klass, 'GRADE')
        choices = abi_sids(schoolyear, pid)
        i = 0
        for sid in sid2tlist:
            try:
                choices.remove(sid)
            except ValueError:
                continue
            i += 1
            if i < 4:
                # Check written subject, eA
                if not sid.endswith (".e"):
                    REPORT.Fail(_NOT_E, i = i, sid = sid)
            elif i == 4:
                # Check written subject, gA
                if not sid.endswith (".g"):
                    REPORT.Fail(_NOT_G, i = i, sid = sid)
            elif i <= 8:
                # Check oral subject
                if not sid.endswith (".m"):
                    REPORT.Fail(_NOT_M, i = i, sid = sid)
            else:
                REPORT.Fail(_TOO_MANY_SUBJECTS)
            subjects.append((sid, sid2tlist[sid].subject))
        if choices:
            REPORT.Fail(_SUBJECT_CHOICE, sids = ', '.join(choices))

        # Get any existing grades for this pupil: {sid -> grade}
        # If there is no grade data, use <{}> to satisfy the subsequent code.
        grades = getGradeData(schoolyear, pid, rtype = 'Abitur')
        try:
            sid2grade = grades['GRADES']
            date = grades['TERM']
        except:
            sid2grade = {}
            date = '?'

        # Add grade-select fields
        gchoices = [(g, g) for g in gradechoices]
        gchoicesM = [(g, g) for g in gradechoicesM]
        i = 0
        for sid, sname in subjects:
            i += 1
            grade = sid2grade.get(sid)
            if grade not in gradechoices:
                grade = ''
            sfield = SelectField(sname, choices=gchoices, default=grade)
            setattr(_Form, sid, sfield)
            if i <= 4:
                # Add (optional) oral exam
                sn = sid + 'N'
                grade = sid2grade.get(sn)
                if grade not in gradechoicesM:
                    grade = '*'
                sfield = SelectField("mdl.", choices = gchoicesM,
                        default = grade)
                setattr(_Form, sn, sfield)

        return pdata, klass, date

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
    subjects = []
    try:
        pdata, klass, date = REPORT.wrap(prepare, suppressok=True)
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

