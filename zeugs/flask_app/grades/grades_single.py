### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades_single.py

Last updated:  2020-03-28

"Sub-module" of grades for single reports

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

from .grades_base import bp, _HEADING, _BPNAME, getCurrentTerm


#TODO: filter
import datetime, os

from flask import (render_template, request, session,
        url_for, abort, redirect, flash)

from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, BooleanField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Optional
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wz_core.configuration import Dates
from wz_core.pupils import Pupils, Klass
from wz_core.db import DB
from wz_table.dbtable import readPSMatrix
from wz_grades.gradedata import (grades2db, db2grades, CurrentTerm,
        getTermTypes, getGradeData, GradeReportData, singleGrades2db)
from wz_grades.makereports import makeReports, makeOneSheet
from wz_grades.gradetable import makeBasicGradeTable
from wz_compat.grade_classes import gradeGroups, needGradeDate


########### Views for single reports ###########

### Select school-class
@bp.route('/klasses', methods=['GET'])
def klasses():
    """Select school-class (single report generation).
    """
    schoolyear = session['year']
    # Collect list of school-classes.
    # Accept all classes here, then – when it turns out that the class
    # has no possible templates – show a message indicating this state
    # of affairs.
    pupils = Pupils(schoolyear)
    # List the classes with the oldest pupils first, as these are more
    # likely to need grades.
    klasslist = sorted(pupils.classes(), reverse=True)
    return render_template(os.path.join(_BPNAME, 'klasses.html'),
            heading = _HEADING,
            klasses = klasslist
    )


@bp.route('/pupils/<klass>', methods=['GET'])
def pupils(klass):
    """Select pupil from given school-class (single report generation).
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
    plists = {}
    for pdata in pupils.classPupils(_klass):
        s = pdata['STREAM'] or '?'
        try:
            plists[s].append(pdata)
        except:
            plists[s] = [pdata]
    return render_template(os.path.join(_BPNAME, 'pupils.html'),
            heading = _HEADING,
            klass = _klass.klass,
            pupils = [(s, plists[s]) for s in sorted(plists)],
            dfile = dfile
    )


@bp.route('/pupil/<pid>', methods=['GET'])
def pupil(pid):
    """Select report type and [edit-existing vs. new] for single report.

    The terms and any existing additional report dates for this pupil
    will be presented for selection. Also a completely new report may
    be selected.
    """
    schoolyear = session['year']
    # Get pupil data
    pdata = Pupils(schoolyear).pupil(pid)
    # Get existing grade entries for the pupil
    dates, _terms = [], {}
    for row in DB(schoolyear).select('GRADES', PID=pid):
        t = row['TERM']
        rtype = row['REPORT_TYPE']
        gklass = Klass.fromKandS(row['CLASS'], row['STREAM'])
        if t in CONF.MISC.TERMS:
            # A term
            rtypes = getTermTypes(gklass, t)
            if rtypes:
                # If not a valid type, show the default
                _terms[t] = rtype if rtype in rtypes else rtypes[0]
        elif t[0] == 'X':
            # An additional report
            rtypes = getTermTypes(gklass, 'X')
            date = row['DATE_D']
            if rtype not in rtypes:
                rtype = rtypes[0]    # the default
            dates.append((t, rtype, date))
    dates.sort(reverse=True)
    # Ensure that there are fields for the terms
    terms = {}
    pklass = pdata.getKlass(withStream=True)
    for t in CONF.MISC.TERMS:
        rtype = _terms.get(t)
        if rtype:
            terms[t] = rtype
        else:
            # If no report type, get default, if any
            rtypes = getTermTypes(pklass, t)
            if rtypes:
                terms[t] = rtypes[0]

    return render_template(os.path.join(_BPNAME, 'pupil.html'),
                            heading = _HEADING,
                            pdata = pdata,
                            terms = terms,
                            dates = dates,
                            todate = Dates.dateConv)


@bp.route('/grades_pupil/<pid>/<rtag>', methods=['GET','POST'])
def grades_pupil(pid, rtag):
    """Edit data for the report to be created. Submit to save the
    changes. A second submit possibility generates the report.
    <rtag> is a TERM field entry from the GRADES table (term or tag).
    It may also be '_', indicating that a new date is to be set up.
    """
    class _Form(FlaskForm):
        # The date of issue can not be changed here for term reports,
        # so for these supply a link to the term date editor and render
        # the field as read-only.
        DATE_D = DateField(validators = [Optional()])

    schoolyear = session['year']
    pdata = Pupils(schoolyear).pupil(pid)
    if not pdata:
        abort(404)
    try:
        CurrentTerm(schoolyear, rtag)
        pdata.CURRENT = True
    except:
        pdata.CURRENT = False
    subjects = []

    def prepare():
        # Get existing grades and report type (or default)
        grades = getGradeData(schoolyear, pid, rtag)
        if grades:
            k, s = grades['CLASS'], grades['STREAM']
            pdata.RTYPE = grades['REPORT_TYPE']
            gmap = grades['GRADES']
            pdata.DATE_D = grades['DATE_D']
            pdata.GDATE_D = grades['GDATE_D']
        else:
            k, s = pdata['CLASS'], pdata['STREAM']
            pdata.RTYPE = None
            gmap = None
            pdata.DATE_D = None
            pdata.GDATE_D = None
        klass = Klass.fromKandS(k, s)
        # Get a list of possible report types for this class/group
        rtypes = getTermTypes(klass, rtag)
        rtype = pdata.RTYPE if pdata.RTYPE in rtypes else rtypes[0]
        _Form.RTYPE = SelectField("Zeugnistyp",
                    choices = [(rt, rt) for rt in rtypes],
                    default = rtype)

        # Get subject data
# Actually, not so much is needed at this stage: grades, rtype and date.
# Should it be required (unlikely?) it might also be possible to make
# all fields of a template editable, by selecting the template and having
# an editor page with fields for all variables.
        gdata = GradeReportData(schoolyear, klass)
        gradechoices = [(g, g) for g in gdata.validGrades()]
        gradechoices.append(('?', '?'))
        # Get the grade manager
        gradeManager = gdata.gradeManager(gmap)

        # Grade conference date only for 11/12(x).Gym and end-of-year
        if needGradeDate(rtag, klass):
#TODO: curterm.dates()
            pdata.GDATE0 = gradeDate(schoolyear, rtag, klass, key = 'GDATE')
            gdate = pdata.GDATE_D
            _Form.VDATE_D = DateField(validators = [Optional()],
                    default = (datetime.date.fromisoformat(gdate)
                            if gdate else None))

#TODO?
        # Add the grade fields to the form
        for sid, tlist in gdata.sid2tlist.items():
            # Only "taught" subjects
            if sid in gradeManager.composites:
                continue
            grade = gradeManager[sid] or '?'
            sfield = SelectField(gdata.sid2tlist[sid].subject,
                    choices = gradechoices, default = grade)
            key = 'X_' + sid
            setattr(_Form, key, sfield)
            subjects.append(key)

        try:
            remarks = grades['REMARKS']
        except:
            remarks = ''
        tfield = TextAreaField(default = remarks)
        setattr(_Form, 'REMARKS', tfield)
        return gdata

    def enterGrades():
#TODO
        REPORT.Test("TODO: enterGrades")
        return False

        # Enter grade data into db
        _grades = gdata.gradeManager(gmap)
        singleGrades2db(schoolyear, pid, gdata.klassdata, term = rtag,
                date = DATE_D, rtype = rtype, grades = _grades,
                remarks = REMARKS)
        return True

    gdata = REPORT.wrap(prepare, suppressok = True)
    form = _Form()
    if form.validate_on_submit():
        # POST
        DATE_D = form.DATE_D.data.isoformat()
        rtype = form.RTYPE.data
        gmap = {}   # grade mapping {sid -> "grade"}
        for key in subjects:
            g = form[key].data
            if g == '?':
                g = None
            gmap[key.split('_', 1)[1]] = g
        try:
            REMARKS = form['REMARKS'].data
        except:
            REMARKS = None
#TODO: Only update changed fields and only change dates from <None>
# when the
        if REPORT.wrap(enterGrades, suppressok = True):
            ok = True
            if request.form['action'] == 'build':
                pdfBytes = REPORT.wrap(makeOneSheet,
                        schoolyear, pdata,
                        rtag if rtag.isdigit() else DATE_D, rtype)
                if pdfBytes:
                    session['filebytes'] = pdfBytes
                    session['download'] = 'Notenzeugnis_%s.pdf' % (
                            pdata['PSORT'].replace(' ', '_'))
                else:
                    ok = False
            if ok:
                return redirect(url_for('bp_grades.pupils',
                        klass = gdata.klassdata.klass))

    # GET
# Move to prepare (like GDATE)?
    if pdata.DATE_D:
        form.DATE_D.data = datetime.date.fromisoformat(pdata.DATE_D)
    # There is also the date set for the group
#TODO: Must be available on PUSH!
#TODO: curterm.dates()
#    pdata.DATE0 = gradeDate(schoolyear, rtag, klass)

    return render_template(os.path.join(_BPNAME, 'grades_pupil.html'),
            form = form,
            heading = _HEADING,
            subjects = subjects,
            pdata = pdata,
            termn = rtag if rtag in CONF.MISC.TERMS else None,
            klass = gdata.klassdata
    )
