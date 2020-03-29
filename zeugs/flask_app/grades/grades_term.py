### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades_term.py

Last updated:  2020-03-29

"Sub-module" of grades for group term reports

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

from .grades_base import bp, _HEADING, _BPNAME

import datetime, os

from flask import (render_template, request, session,
        url_for, abort, redirect, flash)
from flask import current_app as app

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wz_core.configuration import Dates
from wz_core.pupils import Klass
from wz_table.dbtable import readPSMatrix
from wz_grades.gradedata import grades2db, db2grades, CurrentTerm, getTermTypes
from wz_grades.makereports import makeReports
from wz_grades.gradetable import makeBasicGradeTable
from wz_compat.grade_classes import gradeGroups, needGradeDate


########### Views for term-based group reports ###########

@bp.route('/grade_tables', methods=['GET'])
@bp.route('/grade_tables/<termn>', methods=['GET'])
@bp.route('/grade_tables/<termn>/<ks>', methods=['GET'])
def grade_tables(termn = None, ks = None):
    """Generate grade tables.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)   # check year
        term0 = curterm.TERM
    except CurrentTerm.NoTerm:
        term0 = None
    if termn:
        if termn not in CONF.MISC.TERMS:
            abort(404)
    else:
        # Default to the current term
        return redirect(url_for('bp_grades.grade_tables',
                termn = term0 or '1'))

    klasses = REPORT.wrap(gradeGroups, termn, suppressok = True)
    if not klasses:
        flash(_NO_CLASSES.format(term = termn), "Error")
        return redirect(url_for('bp_grades.index'))

    dfile = None    # download file
    if ks:
        klass = Klass(ks)
        # GET: Generate the table
        if klass.inlist(klasses):
            xlsxbytes = REPORT.wrap(makeBasicGradeTable,
                    schoolyear, termn,
                    klass, suppressok = True)
            if xlsxbytes:
                dfile = 'Noten_%s.xlsx' % ks.replace('.', '-')
                session['filebytes'] = xlsxbytes
#WARNING: This is not part of the official flask API, it might change!
                if not session.get("_flashes"):
                    # There are no messages: send the file for downloading.
                    return redirect(url_for('download', dfile = dfile))
                # If there are messages, the template will show these
                # and then make the file available for downloading.
        else:
            abort(404)

    # Make a list of dates. Handle the "current" term slightly
    # differently from the others. For the "current" term the date of
    # the "Notenkonferenz" is necessary, though it may be not set. If
    # it is not set, the template can use an alternative link, to
    # redirect to the page for setting the date.
    # For "non-current" terms, no date should be shown.
    if termn == term0:
        dateInfo = REPORT.wrap(curterm.dates, suppressok = True)
        if not dateInfo:
            return redirect(url_for('bp_grades.index'))
        kdates = [(_ks, dateInfo[str(_ks)].GDATE_D)
                        for _ks in klasses]
    else:
        kdates = [(_ks, None) for _ks in klasses]
    session['nextpage'] = request.path
    return render_template(os.path.join(_BPNAME, 'grade_tables.html'),
                            heading = _HEADING,
                            term0 = term0,
                            termn = termn,
                            klasses = kdates,
                            dfile = dfile)


@bp.route('/term', methods=['GET', 'POST'])
def term():
    """View: Group report generation, select school-class.
    Only possible for current year and term.
    Also grade tables (for this term only) may be uploaded, causing
    their contents to be entered into the database.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)   # check year
        termn = curterm.TERM
    except CurrentTerm.NoTerm:
        flash("%d ist nicht das „aktuelle“ Schuljahr", "Error")
        return redirect(url_for('bp_grades.index'))

    try:
        dfile = session.pop('download')
    except:
        dfile = None

    klasses = REPORT.wrap(gradeGroups, termn, suppressok = True)
    if klasses:
        # Check report types
        klasses = [k for k in klasses if getTermTypes(k, termn)]
    if not klasses:
        flash("Keine Klassen!", "Error")
        return redirect(url_for('bp_grades.index'))

    class UploadForm(FlaskForm):
        upload = FileField('Notentabelle:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Notentabelle')
        ])

    def readdata(f):
        gtbl = readPSMatrix(f)
        grades2db(gtbl)

    form = UploadForm()
    if app.isPOST(form):
        # POST
        REPORT.wrap(readdata, form.upload.data)
        ks = None

    return render_template(os.path.join(_BPNAME, 'term.html'),
                            heading = _HEADING,
                            termn = termn,
                            klasses = klasses,
                            form = form,
                            dfile = dfile)


@bp.route('/reports/<ks>', methods=['GET','POST'])
def reports(ks):
    """Handle report generation for a group of pupils.
    This is available only for the "current" term.
    A list of pupils with checkboxes is displayed, so that some can be
    deselected.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)
    except CurrentTerm.NoTerm:
        flash(("Gruppenzeugnisse können nur im „aktuellen“ Jahr erstellt"
                " werden"), "Error")
        return redirect(url_for('bp_grades_index'))
    termn = curterm.TERM

    # Get default report type for term
    klass = Klass(ks)
    try:
        rtype = getTermTypes(klass, termn)[0]
    except:
        flash("Klasse %s: keine Gruppenzeugnisse möglich" % ks, "Error")
        return redirect(url_for('bp_grades.term'))

    # Get current date info
    dateInfo = REPORT.wrap(curterm.dates, suppressok = True)
    if not dateInfo:
        return redirect(url_for('bp_grades.index'))
    dates = dateInfo[ks]
    withgdate = needGradeDate(termn, klass)
    if withgdate:
        if not dates.GDATE_D:
            session['nextpage'] = request.path
            flash("Das Konferenzdatum für %s fehlt" % ks, "Error")
            # Redirect to set the conference date
            return redirect(url_for('bp_grades.grade_dates'))

    if not dates.DATE_D:
        session['nextpage'] = request.path
        flash("Das Ausstelungsdatum für %s fehlt" % ks, "Error")
        # Redirect to set the conference date
        return redirect(url_for('bp_grades.issue_dates'))

    form = FlaskForm()
    form.withgdate = withgdate
    if app.isPOST(form):
        # POST
        pids=request.form.getlist('Pupil')
        if pids:
            # Generate the reports
            pdfBytes = REPORT.wrap(makeReports, klass, pids)
            if pdfBytes:
                session['filebytes'] = pdfBytes
                session['download'] = ('Notenzeugnis_%s.pdf'
                        % str(klass).replace('.', '-'))
                session.pop('nextpage', None)
                return redirect(url_for('bp_grades.term',
                        termn = termn))
        else:
            flash("** Keine Schüler ... **", "Warning")

    # GET
    pdlist = REPORT.wrap(db2grades, schoolyear, termn, klass, rtype,
            suppressok = True)
    MIN_D, MAX_D = Dates.checkschoolyear(schoolyear)
    return render_template(os.path.join(_BPNAME, 'reports.html'),
                            heading = _HEADING,
                            form = form,
                            termn = termn,
                            dates = dates,
                            MIN_D = MIN_D,
                            MAX_D = MAX_D,
                            rtype = rtype,
                            ks = ks,
                            pupils = pdlist)
#TODO:
# There might be a checkbox/switch for print/pdf, but print might not
# be available on all hosts.
#
# It might be helpful to have a little javascript to implement a pupil-
# selection toggle (all/none) – or else (without javascript) a redisplay
# with all boxes unchecked?


########### Views for term-based settings ###########

@bp.route('/switchterm', methods=['GET', 'POST'])
def switchterm():
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)
    except CurrentTerm.NoTerm:
        # The current term, if any, is not in this year
        flash("%d ist nicht das „aktuelle“ Schuljahr" % schoolyear, "Warning")
        return redirect(url_for('bp_grades.index'))
    return "TODO: Switch term from %s" % curterm.TERM
#TODO:
#    REPORT.wrap(closeTerm, curterm.TERM)
#    DB().setInfo('TERM', '2')
# This needs to be coupled to current-year changes ...


@bp.route('/issue_dates', methods=['GET', 'POST'])
def issue_dates():
    """Set the date of issue for the groups in the current term.
    Also allow locking of the date control for each group.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)
    except CurrentTerm.NoTerm:
        # The current term, if any, is not in this year
        flash("%d ist nicht das „aktuelle“ Schuljahr" % schoolyear, "Warning")
        return redirect(url_for('bp_grades.index'))

    termn = curterm.TERM
    # Get current date info for all groups
    dateInfo = REPORT.wrap(curterm.dates, suppressok = True)
    if not dateInfo:
        return redirect(url_for('bp_grades.index'))

    form = FlaskForm()
    if app.isPOST(form):
        ok = True
        action = request.form['action']
        if action == 'all':
            date0 = request.form['ALL_D']
            if not date0:
                flash("Kein Ausstellungsdatum", "Error")
                ok = False
        else:
            date0 = None

        if ok:
            locks = []
            count = 0
            for ks, termDates in dateInfo.items():
                if termDates.LOCK == 0:
                    continue
                if date0:
                    date = date0
                else:
                    date = request.form[ks]
                d = None
                if date and date != termDates.DATE_D:
                    if REPORT.wrap(curterm.dates, Klass(ks),
                            date = date,
                            suppressok = True):
                        flash("Klasse %s: %s" % (ks, date), "Info")
                        count += 1
                    d = date

                if request.form.get('L_' + ks):
                    if date:
                        locks.append(ks)
                    else:
                        flash(("Klasse %s kann nicht ohne Datum"
                                " gesperrt werden" % ks, "Error"))

            if count:
                flash("%d Änderungen" % count, "Info")
            if locks:
                session['confirm_lock'] = locks
                return redirect(url_for('bp_grades.confirm_lock'))
            nextpage = session.pop('nextpage', None)
            return redirect(nextpage or request.path)

    # GET
    MIN_D, MAX_D = Dates.checkschoolyear(schoolyear)
    return render_template(os.path.join(_BPNAME, 'issue_dates.html'),
                            heading = _HEADING,
                            termn = termn,
                            MIN_D = MIN_D,
                            MAX_D = MAX_D,
                            klasses = dateInfo,
                            form = form)


@bp.route('/confirm_lock', methods=['GET', 'POST'])
def confirm_lock():
    """Confirm locking the date control for each group.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)
    except CurrentTerm.NoTerm:
        # The current term, if any, is not in this year
        flash("%d ist nicht das „aktuelle“ Schuljahr" % schoolyear, "Warning")
        return redirect(url_for('bp_grades.index'))
    form = FlaskForm()
    if app.isPOST(form):
        if request.form['action'] == 'lock':
            locks = request.form.getlist('locks')
            count = 0
            for ks in locks:
                if REPORT.wrap(curterm.dates, Klass(ks),
                            lock = 0,
                            suppressok = True):
                    flash("Klasse %s gesperrt" % ks, "Info")
                    count += 1
            if count:
                flash("%d Änderungen" % count, "Info")
        nextpage = session.pop('nextpage', None)
        return redirect(nextpage or url_for('bp_grades.issue_dates'))

    locks = session.pop('confirm_lock', None)
    if not locks:
        abort(404)
    return render_template(os.path.join(_BPNAME, 'confirm_lock.html'),
                        heading = _HEADING,
                        termn = curterm.TERM,
                        klasses = locks,
                        form = form)


@bp.route('/grade_dates', methods=['GET', 'POST'])
def grade_dates():
    """Set the "Konferenzdatum" for the groups in the current term.
    Also control whether grades may be entered for each group.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)
    except CurrentTerm.NoTerm:
        # The current term, if any, is not in this year
        flash("%d ist nicht das „aktuelle“ Schuljahr" % schoolyear, "Warning")
        return redirect(url_for('bp_grades.index'))

    termn = curterm.TERM
    # Get current date info for all groups
    dateInfo = REPORT.wrap(curterm.dates, suppressok = True)
    if not dateInfo:
        return redirect(url_for('bp_grades.index'))

    form = FlaskForm()
    if app.isPOST(form):
        ok = True
        action = request.form['action']
        if action == 'all':
            date0 = request.form['ALL_D']
            if not date0:
                flash("Kein Konferenzdatum", "Error")
                ok = False
        else:
            date0 = None

        if ok:
            count = 0
            for ks, termDates in dateInfo.items():
                if termDates.LOCK == 0:
                    continue
                if date0:
                    date = date0
                else:
                    date = request.form[ks]
                d = None
                if date and date != termDates.GDATE_D:
                    d = date

                lock = 1
                if request.form.get('L_' + ks):
                    if date:
                        lock = 2
                    else:
                        flash(("Klasse %s: Für die Noteneingabe muss das"
                                " Konferenzdatum gesetzt werden") % ks,
                                "Warning")
                        break

                if d or lock != termDates.LOCK:
                    # Set date and/or lock if changed
                    if REPORT.wrap(curterm.dates, Klass(ks),
                            gdate = d,
                            lock = lock,
                            suppressok = True):
                        flash("Klasse %s: %s Noteneingabe %s"
                                % (ks, date,
                                    "freigegeben" if lock == 2
                                    else "gesperrt"), "Info")
                        count += 1
                    else:
                        break

            if count:
                flash("%d Änderungen" % count, "Info")
                nextpage = session.pop('nextpage', None)
                return redirect(nextpage or request.path)

    # GET
    MIN_D, MAX_D = Dates.checkschoolyear(schoolyear)
    return render_template(os.path.join(_BPNAME, 'grade_dates.html'),
                            heading = _HEADING,
                            termn = termn,
                            MIN_D = MIN_D,
                            MAX_D = MAX_D,
                            klasses = dateInfo,
                            form = form)
