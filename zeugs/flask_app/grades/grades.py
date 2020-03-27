### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades.py

Last updated:  2020-03-27

Flask Blueprint for grade reports

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

_HEADING = "Notenzeugnis"   # page heading


import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, abort, redirect, flash)
#from flask import current_app as app

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


# Set up Blueprint
_BPNAME = 'bp_grades'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


def getCurrentTerm():
    """Return the current term ('1' or '2') if it lies in the session
    year, otherwise <None>.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)
        return curterm.TERM
    except CurrentTerm.NoTerm:
        # The current term is not in this year
        return None


@bp.route('/', methods=['GET'])
def index():
    """View: start-page, select function.
    """
    term0 = getCurrentTerm()
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading = _HEADING,
                            term0 = term0)


########### Views for group reports ###########

@bp.route('/grade_tables', methods=['GET'])
@bp.route('/grade_tables/<termn>', methods=['GET'])
@bp.route('/grade_tables/<termn>/<ks>', methods=['GET'])
def grade_tables(termn = None, ks = None):
    """View: generate grade tables.
    """
    curterm = CurrentTerm()
    if termn:
        if termn not in CONF.MISC.TERMS:
            abort(404)
    else:
        # Default to the current term
        return redirect(url_for('bp_grades.grade_tables',
                termn = curterm.TERM))

    klasses = REPORT.wrap(gradeGroups, termn, suppressok = True)
    if not klasses:
        flash(_NO_CLASSES.format(term = termn), "Error")
        return redirect(url_for('bp_grades.index'))

    schoolyear = session['year']
    dfile = None    # download file
    if ks:
        # GET: Generate the table
        if ks in klasses:
            xlsxbytes = REPORT.wrap(makeBasicGradeTable,
                    schoolyear, termn,
                    ks, suppressok = True)
            if xlsxbytes:
                dfile = 'Noten_%s.xlsx' % str(ks).replace('.', '-')
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
    if termn == curterm.TERM:
        dateInfo = REPORT.wrap(curterm.dates, suppressok = True)
        if not dateInfo:
            return redirect(url_for('bp_grades.index'))
        kdates = [(_ks, dateInfo[str(_ks)].GDATE_D)
                        for _ks in klasses]
    else:
        kdates = [(_ks, None) for _ks in klasses]
    return render_template(os.path.join(_BPNAME, 'grade_tables.html'),
                            heading = _HEADING,
                            term0 = curterm.TERM,
                            termn = termn,
                            klasses = kdates,
                            dfile = dfile)


#TODO: current term/year setting -> "Settings"

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

    class _Form(FlaskForm):
        pass

    form = _Form()
    if request.method == 'POST':
        if form.validate():
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
                count = 0
                for ks, termDates in dateInfo.items():
                    changes = 0
                    if termDates.LOCK == 0:
                        continue
                    if date0:
                        date = date0
                    else:
                        date = request.form[ks]
                    d = None
                    if date and date != termDates.DATE_D:
                        d = date

                    lock = False
                    if request.form.get('L_' + ks):
                        if date:
                            lock = True
                        else:
                            flash(("Klasse %s kann nicht ohne Datum"
                                    " gesperrt werden" % ks, "Error"))

                    if d or lock:
                        if REPORT.wrap(curterm.dates, Klass(ks),
                                date = d,
                                lock = 0 if lock else None,
                                suppressok = True):
                            flash("Klasse %s: %s%s"
                                    % (ks, date,
                                        " – gesperrt" if lock
                                        else ""), "Info")
                            count += 1
                        else:
                            break

                if count:
                    flash("%d Änderungen" % count, "Info")
                    return redirect(request.path)
#???
        else:
            for e in form.errors:
                flash(e, "Error")
                flash("Ungültige Daten", "Fail")

    # GET
    MIN_D, MAX_D = Dates.checkschoolyear(schoolyear)
#TODO
#    form.default = dates
#    form.locked = klocked
    return render_template(os.path.join(_BPNAME, 'issue_dates.html'),
                            heading = _HEADING,
                            termn = termn,
                            MIN_D = MIN_D,
                            MAX_D = MAX_D,
                            klasses = dateInfo,
                            form = form)


#TODO: without wtf fields?
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

    class _Form(FlaskForm):
        ALL_D = DateField(validators = [Optional()])

    # Get current date info for all groups
    dateInfo = REPORT.wrap(curterm.dates, suppressok = True)
    if not dateInfo:
        return redirect(url_for('bp_grades.index'))
    i = 0
    for ks, termDates in dateInfo.items():
        dok = termDates.GDATE_D
        dokd = datetime.date.fromisoformat(dok) if dok else None
        lock = termDates.LOCK
        setattr(_Form, 'DOK_%02d' % i, DateField(
                validators = [Optional()],
                default = dokd,
                render_kw={'readonly': lock == 0}))
        setattr(_Form, 'OPEN_%02d' % i, BooleanField(
                default = bool(dok) and lock == 2,
                render_kw={'disabled': lock == 0}))
        i += 1

    form = _Form()
    if form.validate_on_submit():
        # POST
        ok = True
        if request.form['action'] == 'all':
            try:
                date0 = form.ALL_D.data.isoformat()
            except:
                flash("Kein Konferenzdatum", "Error")
                ok = False
            else:
                if not Dates.checkschoolyear(schoolyear, date0):
                    flash(("Konferenzdatum („alle Gruppen“) außerhalb"
                            " des Schuljahres"), "Error")
                    ok = False
        else:
            date0 = None

        if ok:
            count = 0
            i = 0
            for ks, termDates in dateInfo.items():
                if termDates.LOCK == 0:
                    i += 1
                    continue
                if date0:
                    date = date0
                else:
                    date = getattr(form, 'DOK_%02d' % i).data
                    if date:
                        date = date.isoformat()
                        if not Dates.checkschoolyear(schoolyear, date):
                            flash(("Konferenzdatum (Klasse %s) außerhalb"
                                    " des Schuljahres") % ks, "Error")
                            break

                lock = 1
                if getattr(form, 'OPEN_%02d' % i).data:
                    if date:
                        lock = 2
                    else:
                        flash(("Klasse %s: Für die Noteneingabe muss das"
                                " Konferenzdatum gesetzt werden") % ks,
                                "Warning")
                        break
                if date:
                    # Set date and/or lock if changed
                    if (termDates.LOCK != lock
                            or termDates.GDATE_D != date):
                        if REPORT.wrap(curterm.dates, Klass(ks),
                                gdate = date,
                                lock = lock,
                                suppressok = True):
                            flash("Klasse %s: %s Noteneingabe %s"
                                    % (ks, date,
                                        "freigegeben" if lock == 2
                                        else "gesperrt"), "Info")
                            count += 1
                        else:
                            break
                i += 1

            if count:
                flash("%d Änderungen" % count, "Info")
                return redirect(request.path)

    # GET
    return render_template(os.path.join(_BPNAME, 'grade_dates.html'),
                            heading = _HEADING,
                            termn = termn,
                            klasses = dateInfo,
                            form = form)


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
    if form.validate_on_submit():
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
    """View: Handle report generation for a group of pupils.
    This is available only for the "current" term.
    A list of pupils with checkboxes is displayed, so that some can be
    deselected.
    """
    termn = getCurrentTerm()
    if not termn:
        flash(("Gruppenzeugnisse können nur im „aktuellen“ Jahr erstellt"
                " werden"), "Error")
        return redirect(url_for('bp_grades_index'))

    klass = Klass(ks)
    rtypes = klass.match_map(CONF.GRADES.TEMPLATE_INFO['_' + termn])
    try:
        rtype = rtypes.split()[0]
    except:
        flash("Klasse %s: keine Gruppenzeugnisse möglich" % ks, "Error")
        return redirect(url_for('bp_grades.term'))

    schoolyear = session['year']
#TODO: curterm.dates()
    idate = gradeDate(schoolyear, termn, klass)

    class _Form(FlaskForm):
        DATE_D = DateField(validators = [InputRequired()],
                default = (datetime.date.fromisoformat(idate)
                            if idate else None))

    if needGradeDate(termn, klass):
#TODO: curterm.dates()
        gdate = gradeDate(schoolyear, termn, klass, key = 'GDATE')
        if not gdate:
            session['nextpage'] = request.path
            flash("Das Konferenzdatum für %s fehlt" % klass, "Error")
            # Redirect to set the conference date
            return redirect(url_for('bp_grades.grade_dates'))
        # This date field is read-only, as the setting is done elsewhere
        _Form.VDATE_D = DateField(validators = [InputRequired()],
                    default = (datetime.date.fromisoformat(gdate)))

    form = _Form()
    if form.validate_on_submit():
        # POST
        pids=request.form.getlist('Pupil')
        if pids:
            # Save date
            date = form.DATE_D.data.isoformat()
            if Dates.checkschoolyear(schoolyear, date):
                # Store the date in the database
#TODO: curterm.dates()
                gradeDate(schoolyear, termn, klass, date = date)
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
                flash(("Ausstellungsdatum (Klasse %s) außerhalb"
                        " des Schuljahres") % klass, "Error")
        else:
            flash("** Keine Schüler ... **", "Warning")

    # GET
    pdlist = REPORT.wrap(db2grades, schoolyear, termn, klass, rtype,
            suppressok = True)
    return render_template(os.path.join(_BPNAME, 'reports.html'),
                            heading = _HEADING,
                            form = form,
                            termn = termn,
                            rtype = rtype,
                            ks = klass,
                            pupils = pdlist)
#TODO:
# There might be a checkbox/switch for print/pdf, but print might not
# be available on all hosts.
#
# It might be helpful to have a little javascript to implement a pupil-
# selection toggle (all/none) – or else (without javascript) a redisplay
# with all boxes unchecked?

########### END: views for group reports ###########


########### Views for single reports ###########

### Select school-class
@bp.route('/klasses', methods=['GET'])
def klasses():
    """View: select school-class (single report generation).
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


### Select pupil
@bp.route('/pupils/<klass>', methods=['GET'])
def pupils(klass):
    """View: select pupil from given school-class (single report generation).
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
    """View: select report type and [edit-existing vs. new] for single report.

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
    """View: Edit data for the report to be created. Submit to save the
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

########### END: views for single reports ###########


#TODO: remove
"""
Snippet, which may be useful in some context?

        f = form.upload.data
        filename = secure_filename(f.filename)
#TODO: the folder (grades) must exist!
        fpath = os.path.join(app.instance_path, 'grades', filename)
        f.save(fpath)

#TODO: testing – read using openpyxl, save as tsv.
        from wz_table.spreadsheet import XLS_spreadsheet, ODS_spreadsheet
        if f.filename.endswith('.xlsx'):
            sheets = XLS_spreadsheet(f).sheets
        elif f.filename.endswith('.ods'):
            sheets = ODS_spreadsheet(f).sheets
        else:
            return "Invalid file: %s" % f.filename
        with open(fpath.rsplit('.', 1)[0] + '.tsv', 'w',
                encoding='utf-8', newline='') as fh:
            for sheet, lines in sheets.items():
                fh.write(':::::: %s\n' % sheet)
                for line in lines:
                    fh.write('\t'.join([item or '' for item in line]) + '\n')

        flash('Loaded %s' % f.filename, 'Info')
        flash('Some more info', 'Warning')
        flash('Bad news', 'Error')
#        return redirect(url_for('bp_grades.term', termn=termn))
"""
