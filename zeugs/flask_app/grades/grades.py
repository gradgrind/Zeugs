### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades.py

Last updated:  2020-03-08

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

_NEWDATE = "*** neu ***"    # label for new date, as opposed to editing an old one
_DEFAULT_RTYPE = "Abgang"   # default report type for single reports

# Messages
_KLASS_AND_STREAM = ("Klasse {klass} kommt in GRADES/REPORT_CLASSES sowohl"
        " als ganze Klasse als auch mit Gruppen vor")
_NO_CLASSES = "Keine Klassen für Halbjahr {term} [in wz_compat/grade_classes.py]"


import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, abort, redirect, flash, make_response)
from flask import current_app as app

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
from wz_grades.makereports import makeReports, makeOneSheet
from wz_grades.gradetable import makeBasicGradeTable
from wz_compat.grade_classes import gradeGroups, getDateOfIssue, setDateOfIssue
#from wz_compat.gradefunctions import Manager#, gradeCalc
from wz_compat.template import getGradeTemplate, TemplateError


# Set up Blueprint
_BPNAME = 'bp_grades'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
def index():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


########### Views for group reports ###########

### View for a term, set closing date for user input
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
        date = getDateOfIssue(schoolyear, termn, Klass(ks))
    else:
        # Check all dates equal
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


### View for a term, select school-class
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

#TODO: It might be desirable to do collation in the web app! The entry
# of special fields would also need to be handled. At present this is
# possible for single reports only. Perhaps there should be the choice
# of generating a report or just storing the changes.



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
    form = _Form()
    if form.validate_on_submit():
        # POST
        pids=request.form.getlist('Pupil')
        if pids:
            pdfBytes = REPORT.wrap(makeReports,
                    schoolyear, termn, klass, date, pids)
            session['filebytes'] = pdfBytes
            session['download'] = 'Notenzeugnis_%s.pdf' % klass
            session.pop('nextpage', None)
            return redirect(url_for('bp_grades.term', termn=termn))
        else:
            flash("** Keine Schüler ... **", "Warning")

    # GET
    form.DATE_D.data = datetime.date.fromisoformat(date)
    pdlist = REPORT.wrap(db2grades, schoolyear, termn, klass,
            checkonly=True, suppressok=True)
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
    plist = pupils.classPupils(_klass)
    return render_template(os.path.join(_BPNAME, 'pupils.html'),
            heading = _HEADING,
            klass = _klass.klass,
            pupils = plist,
            dfile = dfile
    )


### For the given pupil select report type, edit / make new, etc.
@bp.route('/pupil/<pid>', methods=['GET','POST'])
def pupil(pid):
    """View: select report type and [edit-existing vs. new] for single report.

    All existing report dates for this pupil will be presented for
    selection.
    If there are no existing dates for this pupil, the only option is to
    construct a new one.
    Also a report type can be selected. The list might include invalid
    types as it is difficult at this stage (considering potential changes
    of stream or even school-class) to determine exactly which ones are
    valid.
    """
    class _Form(FlaskForm):
        KLASS = SelectField("Klasse")
        STREAM = SelectField("Maßstab")
        EDITNEW = SelectField("Ausgabedatum")
        RTYPE = SelectField("Zeugnistyp")

    schoolyear = session['year']
    # Get pupil data
    pupils = Pupils(schoolyear)
    pdata = pupils.pupil(pid)
    pname = pdata.name()
    klass = pdata.getKlass(withStream=True)
    # Get existing dates.
    db = DB(schoolyear)
    rows = db.select('GRADES', PID=pid)
    dates = [_NEWDATE]
    for row in db.select('GRADES', PID=pid):
        t = row['TERM']
        if t[0] != '_':
            dates.append(t)
    # If the stream, or even school-class have changed since an
    # existing report, the templates and available report types may be
    # different. To keep it simple, a list of all report types from the
    # configuration file GRADES.REPORT_TEMPLATES is presented for selection.
    # An invalid choice can be flagged at the next step.
    # If there is a mismatch between school-class/stream of the pupil as
    # selected on this page and that of the existing GRADES entry, a
    # warning can be shown at the next step.
    rtypes = [rtype for rtype in CONF.GRADES.REPORT_TEMPLATES if rtype[0] != '_']

    kname = klass.klass
    stream = klass.stream
    form = _Form(KLASS = kname, STREAM = stream,
            RTYPE = _DEFAULT_RTYPE)
    form.KLASS.choices = [(k, k) for k in reversed(pupils.classes())]
    form.STREAM.choices = [(s, s) for s in CONF.GROUPS.STREAMS]
    form.EDITNEW.choices = [(d, d) for d in dates]
    form.RTYPE.choices = [(t, t) for t in rtypes]

    if form.validate_on_submit():
        # POST
        rtag = form.EDITNEW.data
        rtype = form.RTYPE.data
        try:
            tfile = getGradeTemplate(rtype, klass)
        except TemplateError:
            flash("Zeugnistyp '%s' nicht möglich für Gruppe %s" % (
                    rtype, klass), "Error"
            )
        else:
            return redirect(url_for('bp_grades.make1',
                    pid = pid,
                    rtag = rtag,
                    rtype = rtype
            ))

    # GET
    return render_template(os.path.join(_BPNAME, 'pupil.html'),
                            form = form,
                            heading = _HEADING,
                            klass = kname,
                            pname = pname)


### Edit grades, date-of-issue, etc., then generate report.
@bp.route('/make1/<pid>/<rtype>/<rtag>', methods=['GET','POST'])
def make1(pid, rtype, rtag):
    """View: Edit data for the report to be created, submit to build it.
    <rtype> is the report type.
    <rtag> is a TERM field entry from the GRADES table (term or date).
    """
    class _Form(FlaskForm):
        DATE_D = DateField(validators=[InputRequired()])

    def prepare():
        # Get existing grades
        grades = getGradeData(schoolyear, pid, rtag)
        if grades:
            k, s = grades['CLASS'], grades['STREAM']
        else:
            k, s = pdata['CLASS'], pdata['STREAM']
        klass = Klass.fromKandS(k, s)
        # Get template fields which need to be set here, also subject data
        gdata = GradeReportData(schoolyear, rtype, klass)
        gradechoices = [(g, g) for g in gdata.validGrades()]
        gradechoices.append(('?', '?'))
        # Get the grade manager
        gradeManager = gdata.gradeManager(grades['GRADES'])
        # Add the fields to the form
        for sgroup in gdata.sgroup2sids:    # grouped subject-ids
            slist = []
            for sid in gdata.sgroup2sids[sgroup]:
                # Only "taught" subjects
                if sid in gradeManager.composites:
                    continue
                grade = gradeManager[sid] or '?'
                sfield = SelectField(gdata.sid2tlist[sid].subject,
                        choices=gradechoices, default=grade)
                key = sgroup + '_' + sid
                setattr(_Form, key, sfield)
                slist.append(key)
            if slist:
                groups[sgroup] = slist
        if 'pupil.REMARKS' in gdata.alltags:
            try:
                remarks = grades['REMARKS']
            except:
                remarks = ''
            tfield = TextAreaField(default = remarks)
            setattr(_Form, 'REMARKS', tfield)
        return gdata

    def enterGrades():
        # Add calculated grade entries
        gradeCalc(gmap, gcalc)
        # Enter grade data into db
        singleGrades2db(schoolyear, pid, klass, term = rtag,
                date = DATE_D, rtype = rtype, grades = gmap,
                remarks = REMARKS)
        return True

    schoolyear = session['year']
    pdata = Pupils(schoolyear).pupil(pid)
    groups = {}
    gdata = REPORT.wrap(prepare, suppressok=True)

#TODO
#    if not groups:
#        # Return to caller
#        return redirect(request.referrer)

    # Get pupil data
#    pupils = Pupils(schoolyear)
#    pdata = pupils.pupil(pid)
    pname = pdata.name()

    form = _Form()
    if form.validate_on_submit():
        # POST
        DATE_D = form.DATE_D.data.isoformat()
        gmap = {}   # grade mapping {sid -> "grade"}

#???
        for g, keys in groups:
            for key in keys:
                gmap[key.split('_', 1)[1]] = form[key].data
        try:
            REMARKS = form['REMARKS'].data
        except:
            REMARKS = None
        gradeManager = REPORT.wrap(gdata.gradeManager, gmap)
        if REPORT.wrap(enterGrades, suppressok=True):
            pdfBytes = REPORT.wrap(makeOneSheet,
                    schoolyear, DATE_D, pdata,
                    rtag if rtag.isdigit() else DATE_D, rtype)
            session['filebytes'] = pdfBytes
            session['download'] = 'Notenzeugnis_%s.pdf' % (
                    pdata['PSORT'].replace(' ', '_'))
            return redirect(url_for('bp_grades.pupils', klass = klass.klass))

#TODO: ?
# There is no point to +/-, as these won't appear in the report and
# are only intended for Notenkonferenzen. However, they might be of
# interest for future reference?

    # GET
    if rtag in CONF.MISC.TERMS:
        # There must be a date of issue
        term = rtag
        date = gdata.getTermDate(term)
        if not date:
            flash("Ausstellungsdatum für Klasse %s fehlt"
                    % gdata.klassdata, "Error")
            return redirect(url_for('bp_grades.issue', termn = term))
        form.DATE_D.data = datetime.date.fromisoformat(date)
    else:
        term = None


#    return repr(groups)


    return render_template(os.path.join(_BPNAME, 'make1.html'),
                            form = form,
                            groups = groups,
                            heading = _HEADING,
                            pid = pid,
                            pname = pname,
                            rtype = rtype,
                            termn = term,
                            klass = gdata.klassdata.klass,
                            stream = gdata.klassdata.stream
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
