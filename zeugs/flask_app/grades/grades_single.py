### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades_single.py

Last updated:  2020-03-29

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

# Messages
_NO_REPORT_TYPES = "Kein Zeugnistyp für {ks} (Halbjahr/Kennzeichen {term})"
_TOO_MANY_REPORTS = "{pname} hat zu viele Zeugnisse ..."
_BAD_RTAG = "Ungültiges Halbjahr/Kennzeichen: {rtag}"


from .grades_base import bp, _HEADING, _BPNAME


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
from wz_compat.grade_classes import gradeGroups, needGradeDate, getGradeGroup


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
    be selected. This view does not cover final Abitur reports.
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
                # If <rtype> is not a valid type, show the default
                _terms[t] = rtype if rtype in rtypes else rtypes[0]
            else:
#TODO: No report types for this group/term
# delete entry?
                raise TODO

        elif t[0] == 'X':
            # An additional report
            try:
                x = int(t[1:])
            except:
#TODO: illegal tag, delete entry?
                raise TODO
            rtypes = getTermTypes(gklass, 'X') # valid report types
            if rtypes:
                # If <rtype> is not a valid type, use the default
                dates.append((t,
                        rtype if rtype in rtypes else rtypes[0],
                        row['DATE_D']))
            else:
#TODO: No report types for this group/term
# delete entry?
                raise TODO

    dates.sort(reverse=True)
    pklass = pdata.getKlass(withStream = True)
    rtypes = getTermTypes(pklass, 'X') # valid "special" report types
    if rtypes:
        # Add entry for new "special" report
        dates.append(('X', rtypes[0], None))

    # Ensure that there are fields for each valid term
    terms = []
    for t in CONF.MISC.TERMS:
        rtype = _terms.get(t)
        if rtype:
            terms.append((t, rtype))
        else:
            # If no report type, get default, if any
            rtypes = getTermTypes(pklass, t)
            if rtypes:
                terms.append((t, rtypes[0]))

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
    It may also be 'X', indicating that a new date is to be set up.
    """
    schoolyear = session['year']
    pdata = Pupils(schoolyear).pupil(pid)
    if not pdata:
        abort(404)
    try:
        curterm = CurrentTerm(schoolyear, rtag)
        pdata.TERM0 = curterm.TERM
    except:
        pdata.TERM0 = None
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
        elif rtag == 'X' or rtag in CONF.MISC.TERMS:
            k, s = pdata['CLASS'], pdata['STREAM']
            pdata.RTYPE = None
            gmap = None
            pdata.DATE_D = None
            pdata.GDATE_D = None
        else:
            REPORT._Fail(_BAD_RTAG, rtag = rtag)

        klass = Klass.fromKandS(k, s)
        pdata.GKLASS = klass
        # Get a list of possible report types for this class/group
        rtypes = getTermTypes(klass, rtag)
        if not rtypes:
            REPORT.Fail(_NO_REPORT_TYPES, ks = klass, term = rtag[0])
        if pdata.RTYPE not in rtypes:
            pdata.RTYPE = rtypes[0]
        pdata.RTYPES = rtypes

        # Get subject data
# Actually, not so much is needed at this stage: grades, rtype and date.
# Should it be required (unlikely?) it might also be possible to make
# all fields of a template editable, by selecting the template and having
# an editor page with fields for all variables.
        gdata = GradeReportData(schoolyear, klass)
        gradechoices = gdata.validGrades() + ('?',)
        pdata.VALIDGRADES = gradechoices
        # Get the grade manager
        gradeManager = gdata.gradeManager(gmap)

        # Dates ...
        if pdata.TERM0 == rtag:
            # Need the containing group, not the pupil/grade group!
            dates = curterm.dates()[str(getGradeGroup(rtag, klass))]
            pdata.DATE_D0 = dates.DATE_D
            pdata.GDATE_D0 = dates.GDATE_D
        # Grade conference date only for some classes / terms
        if needGradeDate(rtag, klass):
            pdata.GDATE = True

        # Add the grade fields to the form
        for sid, tlist in gdata.sid2tlist.items():
            # Only "taught" subjects
            if sid in gradeManager.composites:
                continue
            subjects.append((sid, gradeManager[sid] or '?'))

        try:
            pdata.REMARKS = grades['REMARKS']
        except:
            pdata.REMARKS = ''
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

    # Test for new report
    gdata = REPORT.wrap(prepare, suppressok = True)
    form = FlaskForm()
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
    return render_template(os.path.join(_BPNAME, 'grades_pupil.html'),
            form = form,
            heading = _HEADING,
            subjects = subjects,
            pdata = pdata,
            termn = rtag if rtag in CONF.MISC.TERMS else None,
            klass = gdata.klassdata
    )
