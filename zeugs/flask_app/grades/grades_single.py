### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades_single.py

Last updated:  2020-04-19

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


from .grades_base import bp, _HEADING, _BPNAME


import datetime, os

from flask import (render_template, request, session,
        url_for, abort, redirect, flash)
from flask import current_app as app
from flask_wtf import FlaskForm

from wz_core.configuration import Dates
from wz_core.pupils import Pupils, Klass
from wz_grades.gradedata import (CurrentTerm, getTermTypes,
        GradeData, GradeReportData, getGradeEntries)
from wz_grades.makereports import makeOneSheet
from wz_compat.grade_classes import (needGradeDate, getGradeGroup,
        klass2streams)


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
    rows = getGradeEntries(schoolyear, pdata)
    for row in rows:
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
#TODO: Maybe only existing GRADES entries, current term and new X?
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


#???? Do I want this? Or integrate it in grades_pupil?
@bp.route('/grades_pupil_klass/<pid>/<rtag>', methods=['GET','POST'])
def grades_pupil_klass(pid, rtag):
    """Change stream of a grades-info entry.
    """
    schoolyear = session['year']
    pdata = Pupils(schoolyear).pupil(pid)
    if not pdata:
        abort(404)
    try:
        curterm = CurrentTerm(schoolyear, rtag)
        flash("Maßstab kann nicht für Noten im aktuellen Halbjahr geändert"
                " werden. Dafür muss man die Schülerdaten ändern.",
                "Warning")
        return redirect(request.referrer)
    except:
        pass
    streams = klass2streams(pdata['CLASS'])
    form = FlaskForm()
    if app.isPOST(form):
        # POST
        stream = request.form['STREAM']

    # GET


# Allow any stream and report type to be chosen, mismatches being
# picked up on submission? It might make the coding easier ...
# A stream change might change the grades, etc! A redisplay would
# be necessary ...
@bp.route('/grades_pupil/<pid>/<rtag>', methods=['GET','POST'])
@bp.route('/grades_pupil/<pid>/<rtag>/<stream>', methods=['GET','POST'])
def grades_pupil(pid, rtag, stream = None):
    """Edit data for the report to be created. Submit to save the
    changes. A second submit possibility generates the report.
    <rtag> is a TERM field entry from the GRADES table (term or tag).
    It may also be 'X', indicating that a new date is to be set up.
    """
    schoolyear = session['year']
    pdata = REPORT.wrap(Pupils(schoolyear).pupil, pid)
    if not pdata:
        abort(404)
    pdata.TERMTAG = rtag
    try:
        curterm = CurrentTerm(schoolyear, rtag)
        pdata.TERM0 = curterm.TERM
    except:
        pdata.TERM0 = None

    def prepare():
        ### Get existing grades and report type (or default)
        pdata.RTAG = rtag
        gradeData = GradeData(schoolyear, rtag, pdata, stream)
        pdata.RTYPE = gradeData.ginfo.get('REPORT_TYPE')
        pdata.DATE_D = gradeData.ginfo.get('DATE_D')
        pdata.GDATE_D = gradeData.ginfo.get('GDATE_D')
        pdata.REMARKS = gradeData.ginfo.get('REMARKS') or ''
        gmap = gradeData.getAllGrades()
        # Note that the GRADES_INFO entry has not yet been updated.
        pdata.gklass = Klass.fromKandS(gradeData.gclass, gradeData.gstream)
        # Get a list of possible report types for this class/group
        rtypes = getTermTypes(pdata.gklass, rtag)
        if not rtypes:
            REPORT.Fail(_NO_REPORT_TYPES, ks = pdata.gklass, term = rtag[0])
        if pdata.RTYPE not in rtypes:
            pdata.RTYPE = rtypes[0]
        pdata.RTYPES = rtypes

        # Get subject data
# Actually, not so much is needed at this stage: grades, rtype and date.
# Should it be required (unlikely?) it might also be possible to make
# all fields of a template editable, by selecting the template and having
# an editor page with fields for all variables.
        pdata.VALIDGRADES = gradeData.validGrades() + ('?',)

        # Dates ...
        if pdata.TERM0 == rtag:
            # Need the containing grade-group, not the pupil/grade group!
            ggroup = str(getGradeGroup(rtag, pdata.gklass))
            dates = curterm.dates().get(ggroup)
            if dates:
                pdata.DATE_D0 = dates.DATE_D
                pdata.GDATE_D0 = dates.GDATE_D
        # Grade conference date only for some classes / terms
        pdata.GDATE = needGradeDate(rtag, pdata.gklass)

#TODO: Subjects grouped (using gdata.sgroup2sids)?
        # Return the grades
        return gradeData.getAllGrades()

    def enterGrades():
        # Enter grade data into db
        gradeData = GradeData(schoolyear, rtag, pdata, stream)
        gradeData.updateGrades(gmap, user = session['user_id'],
                DATE_D = DATE_D, GDATE_D = GDATE_D,
                REPORT_TYPE = RTYPE, REMARKS = REMARKS)
        return True

    form = FlaskForm()
    if app.isPOST(form):
        # POST
        DATE_D = request.form['DATE_D']
        GDATE_D = request.form.get('GDATE_D')
        RTYPE = request.form['rtype']
        gmap = {}   # grade mapping {sid -> "grade"}
        for tag, g in request.form.items():
            if tag.startswith('G_'):
                sid = tag[2:]
                if g == '?':
                    g = None
                gmap[sid] = g
        REMARKS = request.form.get('REMARKS') or None
        # Update GRADES entry, or add new one
        if REPORT.wrap(enterGrades, suppressok = True):
            flash("Zeugnisdaten gespeichert", "Info")
            ok = True
            if request.form['action'] == 'build':
                pdfBytes = REPORT.wrap(makeOneSheet,
                        schoolyear, pdata, rtag)
                if pdfBytes:
                    session['filebytes'] = pdfBytes
                    session['download'] = 'Notenzeugnis_%s.pdf' % (
                            pdata['PSORT'].replace(' ', '_'))
                else:
                    ok = False
            if ok:
                return redirect(url_for('bp_grades.pupils',
                        klass = gdata.klassdata.klass))
        return redirect(request.path)

    # GET
    gradeManager = REPORT.wrap(prepare, suppressok = True)
    if not gradeManager:
        return redirect(url_for('bp_grades.pupils',
                klass = pdata['CLASS']))
    subjects = []
    names = gradeManager.sname
    for sid, g in gradeManager.items():
        # Only "taught" subjects
        subjects.append(('G_' + sid, names[sid], g or '?'))
    astreams = []
    if not stream:
        streams0 = REPORT.wrap(klass2streams, pdata.gklass.klass,
                suppressok = True)
        if streams0:
            astreams = [s for s in streams0 if s != pdata.gklass.stream]
    return render_template(os.path.join(_BPNAME, 'grades_pupil.html'),
            form = form,
            heading = _HEADING,
            subjects = subjects,
            pdata = pdata,
            termn = rtag if rtag in CONF.MISC.TERMS else None,
            astreams = astreams
    )
