### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades.py

Last updated:  2020-03-14

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

_DEFAULT_RTYPE = "Abgang"   # default report type for single reports

# Messages
_NO_CLASSES = "Keine Klassen für Halbjahr {term} [in wz_compat/grade_classes.py]"


import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, abort, redirect, flash)
#from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Optional #, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wz_core.configuration import Dates
from wz_core.pupils import Pupils, Klass
from wz_core.db import DB
from wz_table.dbtable import readPSMatrix
from wz_grades.gradedata import (grades2db, db2grades,
        getGradeData, GradeReportData, singleGrades2db)
from wz_grades.makereports import getTermDefaultType, makeReports, makeOneSheet
from wz_grades.gradetable import makeBasicGradeTable
from wz_compat.grade_classes import gradeGroups, getDateOfIssue, setDateOfIssue
from wz_compat.gradefunctions import getVDate


# Set up Blueprint
_BPNAME = 'bp_grades'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
def index():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


########### Views for group reports ###########

### Settings view, set closing date and current term for user input
@bp.route('/closingdate', methods=['GET','POST'])
def closingdate():
    class _Form(FlaskForm):
        TERM = SelectField("Halbjahr")
        GRADES_CLOSING_D = DateField("Einsendeschluss", validators=[Optional()])

    schoolyear = session['year']
    form = _Form()
    form.TERM.choices = [(t, t) for t in CONF.MISC.TERMS] + [('', '–')]
    db = DB(schoolyear)

    if form.validate_on_submit():
        ok = True
        # POST
        term = form.TERM.data
        if term:
            gdate = form.GRADES_CLOSING_D.data
            if gdate:
                d = gdate.isoformat()
                if Dates.checkschoolyear(schoolyear, d):
                    db.setInfo('GRADES_CURRENT', term + ':' + d)
                    flash("Notentermin %s. Halbjahr eingestellt: %s" %
                            (term, d), "Info")
                else:
                    flash("Noten: Einsendeschluss ungültig (Schuljahr)", "Error")
                    ok = False
            else:
                flash("Noten: Einsendeschluss fehlt", "Error")
                ok = False
        else:
            # Not accepting grade input
            db.setInfo('GRADES_CURRENT', None)
            flash("Noteneingabe gesperrt", "Info")
        if ok:
            return redirect(url_for('bp_grades.index'))
        else:
            flash("Fehler sind aufgetreten", "Error")

    # GET
    # Get current settings
    gradesInfo = db.getInfo('GRADES_CURRENT')
    if gradesInfo:
        t, d = gradesInfo.split(':')
        form.TERM.data = t
        form.GRADES_CLOSING_D.data = datetime.date.fromisoformat(d)
    else:
        form.TERM.data = ''
    return render_template(os.path.join(_BPNAME, 'closingdate.html'),
                            form=form,
                            heading=_HEADING)


### Settings view, set "Konferenzdatum" for end of 11th and 12th years
@bp.route('/vdate', methods=['GET','POST'])
def vdate():
    class _Form(FlaskForm):
        pass

    schoolyear = session['year']
    db = DB(schoolyear)
    # Get current settings
    pupils = Pupils(schoolyear)
    keys = []
    for k in pupils.classes(stream = 'Gym'):
        if k.startswith('11') or k.startswith('12'):
            key = 'X_' + k
            keys.append(key)
            date = db.getInfo('Versetzungsdatum_' + k)
            dfield = DateField("Klasse " + k, validators=[Optional()],
                    default = datetime.date.fromisoformat(date)
                            if date else None)
            setattr(_Form, key, dfield)
    form = _Form()

    if form.validate_on_submit():
        # POST
        ok = 0
        for key in keys:
            klass = key.split('_', 1)[1]
            date = form[key].data
            if date:
                _date = date.isoformat()
                if Dates.checkschoolyear(schoolyear, _date):
                    db.setInfo('Versetzungsdatum_' + klass, _date)
                    if ok >= 0:
                        ok += 1
                    flash("Konferenzdatum für Klasse %s: %s" %
                            (klass, _date), "Info")
                else:
                    ok = -1
                    flash("Noten: Konferenzdatum ungültig (Schuljahr)",
                            "Error")
        if ok >= 0:
            if ok > 0:
                flash("%d Einstellung(en) gespeichert" % ok, "Info")
            nextpage = session.pop('nextpage', None)
            if nextpage:
                return redirect(nextpage)
            return redirect(url_for('bp_grades.index'))
        else:
            flash("Fehler sind aufgetreten", "Error")

    # GET
    return render_template(os.path.join(_BPNAME, 'vdate.html'),
                            form = form,
                            heading = _HEADING,
                            keys = keys)


### View for a term, select date of issue
@bp.route('/issue', methods=['GET', 'POST'])
@bp.route('/issue/<termn>', methods=['GET', 'POST'])
@bp.route('/issue/<termn>/<ks>', methods=['GET', 'POST'])
def issue(termn = None, ks = None):
    class _Form(FlaskForm):
        DOI_D = DateField("Ausstellungsdatum", validators = [InputRequired()])

    schoolyear = session['year']
    if not termn:
        current = DB(schoolyear).getInfo('GRADES_CURRENT')
        if current:
            termn, _ = current.split(':')
        else:
            termn = '1'
    klasses = REPORT.wrap(gradeGroups, termn, suppressok=True)
    if not klasses:
        return abort(404)
    if ks and str(Klass(ks)) not in klasses:
        return abort(404)
    form = _Form()
    if form.validate_on_submit():
        # POST
        date = form.DOI_D.data.isoformat()
        if ks:
            kslist = [ks]
        else:
            kslist = klasses
        for _ks in kslist:
            setDateOfIssue(schoolyear, termn, Klass(_ks), date)
            flash("Ausstellungsdatum für Klasse %s: %s" % (_ks, date), "Info")
        nextpage = session.pop('nextpage', None)
        if nextpage:
            return redirect(nextpage)
        return redirect(url_for('bp_grades.issue', termn = termn))

    # GET
    # Set initial date (if there is an old value)
    if ks:
        # Single group page
        date = getDateOfIssue(schoolyear, termn, Klass(ks))
    else:
        # All groups page
        # Check that all dates are equal
        date = None
        for _ks in klasses:
            d = getDateOfIssue(schoolyear, termn, Klass(_ks))
            if d != date:
                if date:
                    date = None
                    break
                date = d
        else:
            date = d
    try:
        form.DOI_D.data = datetime.date.fromisoformat(date)
    except:
        pass
    return render_template(os.path.join(_BPNAME, 'issue.html'),
                            heading = _HEADING,
                            klasses = klasses,
                            klass = ks,
                            termn = termn,
                            form = form)


### View for a term, select school-class
@bp.route('/term/<termn>', methods=['GET'])
def term(termn):
    """View: select school-class (group report generation).
    """
    try:
        dfile = session.pop('download')
    except:
        dfile = None
    schoolyear = session['year']
    try:
        kmap = CONF.GRADES.REPORT_TEMPLATES['_' + termn]
    except:
        abort(404)
    klasses = REPORT.wrap(gradeGroups, termn, suppressok=True)
    if not klasses:
        flash(_NO_CLASSES.format(term = termn), "Error")
        return redirect(url_for('bp_grades.index'))
    return render_template(os.path.join(_BPNAME, 'term.html'),
                            heading=_HEADING,
                            termn=termn,
                            klasses=klasses,
                            dfile=dfile)


### View for a term: grade tables, select school-class
@bp.route('/termtable/<termn>/<ks>', methods = ['GET', 'POST'])
@bp.route('/termtable/<termn>', methods = ['GET', 'POST'])
def termtable(termn, ks = None):
    """View: select school-class (group grade-table generation).
    The "POST" method allows uploading a completed grade-table.
    """
    class UploadForm(FlaskForm):
        upload = FileField('Notentabelle:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Notentabelle')
        ])

    def readdata(f):
        gtbl = readPSMatrix(f)
        grades2db(session['year'], gtbl, term=termn)

    schoolyear = session['year']
    try:
        kmap = CONF.GRADES.REPORT_TEMPLATES['_' + termn]
    except:
        abort(404)
    klasses = REPORT.wrap(gradeGroups, termn, suppressok=True)
    if not klasses:
        flash(_NO_CLASSES.format(term = termn), "Error")
        return redirect(url_for('bp_grades.index'))

    form = UploadForm()
    dfile = None
    if form.validate_on_submit():
        # POST
        REPORT.wrap(readdata, form.upload.data)

    else:
        # GET
        if ks:
            # Generate the table
            if ks in klasses:
                xlsxbytes = REPORT.wrap(makeBasicGradeTable,
                        schoolyear, termn,
                        Klass(ks), "Noten: %s. Halbjahr" % termn,
                        suppressok = True)
                if xlsxbytes:
                    dfile = 'Noten_%s.xlsx' % ks
                    session['filebytes'] = xlsxbytes
#WARNING: This is not part of the official flask API, it might change!
                    if not session.get("_flashes"):
                        # There are no messages: send the file for downloading.
                        return redirect(url_for('download', dfile = dfile))
                    # If there are messages, the template will show these
                    # and then make the file available for downloading.
            else:
                abort(404)

    return render_template(os.path.join(_BPNAME, 'termtable.html'),
                            heading = _HEADING,
                            form = form,
                            termn = termn,
                            klasses = klasses,
                            dfile = dfile)


### Select which pupils should be included.
### Generate reports.
@bp.route('/klass/<termn>/<klass_stream>', methods=['GET','POST'])
def klassview(termn, klass_stream):
    """View: Handle report generation for a group of pupils.
    This is specific to the selected term.
    A list of pupils with checkboxes is displayed, so that some can be
    deselected.
    """
    class _Form(FlaskForm):
        # Use a DateField more for the appearance than for the
        # functionality – it should be displayed read-only.
        DATE_D = DateField()

    schoolyear = session['year']
    klass = Klass(klass_stream)
    session['nextpage'] = request.path
    date = getDateOfIssue(schoolyear, termn, klass)
    if not date:
        return redirect(url_for('bp_grades.issue', termn = termn,
                ks = klass_stream))

    if (termn == '2' and klass.stream == 'Gym' and
            (klass.klass.startswith('11') or klass.klass.startswith('12'))):
        # Grade conference date only for 11(x).Gym and end-of-year
        vdate = getVDate(schoolyear, klass.klass)
        if not vdate:
            return redirect(url_for('bp_grades.vdate'))
        _Form.VDATE_D = DateField(validators = [Optional()],
                    default = (datetime.date.fromisoformat(vdate)
                            if vdate else None))

    form = _Form()
    if form.validate_on_submit():
        # POST
        pids=request.form.getlist('Pupil')
        if pids:
            pdfBytes = REPORT.wrap(makeReports,
                    schoolyear, termn, klass, pids)
            session['filebytes'] = pdfBytes
            session['download'] = 'Notenzeugnis_%s.pdf' % klass
            session.pop('nextpage', None)
            return redirect(url_for('bp_grades.term', termn=termn))
        else:
            flash("** Keine Schüler ... **", "Warning")

    # GET
    form.DATE_D.data = datetime.date.fromisoformat(date)
    rtype = klass.match_map(CONF.GRADES.REPORT_TEMPLATES['_' + termn])
    pdlist = REPORT.wrap(db2grades, schoolyear, termn, klass,
            rtype = rtype, suppressok=True)
    return render_template(os.path.join(_BPNAME, 'klass.html'),
                            form=form,
                            heading=_HEADING,
                            termn=termn,
                            klass_stream=klass,
                            pupils=pdlist)
#TODO:
# There might be a checkbox/switch for print/pdf, but print might not
# be available on all hosts.
#
# It might be helpful to a a little javascript to implement a pupil-
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
    # Get "terms" and existing dates
    dates, _terms = [], {}
    for row in DB(schoolyear).select('GRADES', PID=pid):
        t = row['TERM']
        if t[0] != '_':
            if t in CONF.MISC.TERMS:
                _terms[t] = row['REPORT_TYPE']
            else:
                dates.append((t, row['REPORT_TYPE'] or _DEFAULT_RTYPE))
    dates.sort(reverse=True)
    terms = {}
    for t in CONF.MISC.TERMS:
        rtype = _terms.get(t)
        if rtype:
            terms[t] = rtype
        else:
            # If no report type, get default
            klass = pdata.getKlass(withStream=True)
            terms[t] = getTermDefaultType (klass, t)

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
    <rtag> is a TERM field entry from the GRADES table (term or date).
    It may also be '_', indicating that a new date is to be set up.
    """
    class _Form(FlaskForm):
        # The date of issue can not be changed here for term reports,
        # so for these supply a link to the term date editor and render
        # the field as read-only.
        DATE_D = DateField(validators = [InputRequired()])

    schoolyear = session['year']
    pdata = Pupils(schoolyear).pupil(pid)
    subjects = []

    def prepare():
        # Get existing grades and report type (or default)
        grades = getGradeData(schoolyear, pid, rtag)
        if grades:
            k, s = grades['CLASS'], grades['STREAM']
            rtype = grades['REPORT_TYPE']
        else:
            k, s = pdata['CLASS'], pdata['STREAM']
            rtype = None
        klass = Klass.fromKandS(k, s)
        if not rtype:
            if rtag in CONF.MISC.TERMS:
                rtype = getTermDefaultType(klass, rtag)
            else:
                rtype = _DEFAULT_RTYPE
        # Build a list of possible report types for this class/group
        rtypes = []
        for _rtype, kmap in CONF.GRADES.REPORT_TEMPLATES.items():
            if _rtype[0] != '_':
                if klass.match_map(kmap):
                    rtypes.append((_rtype, _rtype))
        _Form.RTYPE = SelectField("Zeugnistyp",
                    choices = rtypes,
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
        try:
            gmap = grades['GRADES']
        except:
            gmap = None
        gradeManager = gdata.gradeManager(gmap)

        # Grade conference date only for 11(x).Gym and end-of-year
        if (rtag == '2'
                and klass.stream == 'Gym'
                and (klass.klass.startswith('11')
                    or klass.klass.startswith('12'))):
            vdate = getVDate(schoolyear, klass.klass)
            _Form.VDATE_D = DateField(validators = [Optional()],
                    default = (datetime.date.fromisoformat(vdate)
                            if vdate else None))

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
        # Enter grade data into db
        _grades = gdata.gradeManager(gmap)
        singleGrades2db(schoolyear, pid, gdata.klassdata, term = rtag,
                date = DATE_D, rtype = rtype, grades = _grades,
                remarks = REMARKS)
        return True

    gdata = REPORT.wrap(prepare, suppressok=True)
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
        if REPORT.wrap(enterGrades, suppressok=True):
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
    if rtag in CONF.MISC.TERMS:
        # There must be a date of issue
        term = rtag
        date = gdata.getTermDate(term)
        if not date:
            session['nextpage'] = url_for('bp_grades.grades_pupil',
                    pid = pid, rtag = rtag)
            flash("Ausstellungsdatum für Klasse %s fehlt"
                    % gdata.klassdata, "Error")
            return redirect(url_for('bp_grades.issue', termn = term))
        form.DATE_D.data = datetime.date.fromisoformat(date)
    else:
        term = None
    return render_template(os.path.join(_BPNAME, 'grades_pupil.html'),
            form = form,
            heading = _HEADING,
            subjects = subjects,
            pname = pdata.name(),
            termn = term,
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
