### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades.py

Last updated:  2020-01-18

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

_HEADING = "Notenzeugnis"

_NEWDATE = "*** neu ***"
_DEFAULT_RTYPE = "Abgang"

import datetime, io, os
#from types import SimpleNamespace

from flask import (Blueprint, render_template, request, session,
        send_file, url_for, abort, redirect, flash)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired #, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
#from werkzeug.utils import secure_filename

from wz_core.configuration import Dates
from wz_core.pupils import Pupils, toKlassStream, fromKlassStream, match_klass_stream
from wz_core.db import DB
#from wz_compat.config import sortingName
from wz_grades.gradedata import readGradeTable, grades2db, db2grades
from wz_grades.makereports import makeReports


# Set up Blueprint
_BPNAME = 'bp_grades'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
#@admin_required
def index():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


@bp.route('/term/<termn>', methods=['GET'])
#@admin_required
def term(termn):
    def prepare(schoolyear, termn, kmap):
        """Gather the possible klasses/streams.
        """
#TODO: Maybe rather get permissible classes/streams from config list(s)?
        p = Pupils(schoolyear)
        klasses = []
        # Only if all streams have the same report type and template
        # can the whole klass be done together.
        # Pupils with no stream will be handled separately, with stream '_'.
        for klass in p.classes():
            allmatch = True     # whole klass possible
            template = None     # for template matching
            klist = []          # klass.stream list
            for stream in p.streams(klass):
                rtype = match_klass_stream(klass, kmap, stream)
                if rtype:
                    rtype_tpl = match_klass_stream(klass,
                            CONF.GRADES.REPORT_TEMPLATES[rtype], stream)
                    if rtype_tpl:
                        klist.append(toKlassStream(klass, stream))
                        if template:
                            if rtype_tpl == template:
                                continue
                        else:
                            template = rtype_tpl
                            continue
                allmatch = False
            if allmatch:
                # Add the whole class as an option
                klasses.append (klass)
                if len(klist) > 1:
                    # Only add the individual groups if there are more than one
                    klasses += klist
            else:
                klasses += klist
        return klasses

    # Start of method
    try:
        dfile = session.pop('download')
    except:
        dfile = None
    schoolyear = session['year']
    try:
        kmap = CONF.GRADES.REPORT_TEMPLATES['_' + termn]
    except:
        abort(404)
    klasses = REPORT.wrap(prepare, schoolyear, termn, kmap,
            suppressok=True)
    if not klasses:
        return index()
    return render_template(os.path.join(_BPNAME, 'term.html'),
                            heading=_HEADING,
                            termn=termn,
                            klasses=klasses,
                            dfile=dfile)


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


@bp.route('/pupils/<klass>', methods=['GET'])
def pupils(klass):
    """View: select pupil from given school-class (single report generation).
    """
    schoolyear = session['year']
    # Collect list of pupils for this school-class.
    pupils = Pupils(schoolyear)
    # List the classes with the oldest pupils first, as these are more
    # likely to need grades.
    plist = pupils.classPupils(klass)
    return render_template(os.path.join(_BPNAME, 'pupils.html'),
            heading = _HEADING,
            klass = klass,
            pupils = plist
    )


@bp.route('/pupil/<pid>', methods=['GET','POST'])
#@admin_required
def pupil(pid):
    """View: select report type and edit-existing / new for single report.

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
    klass, stream = pdata['CLASS'], pdata['STREAM']
    # Get existing dates.
    db = DB(schoolyear)
    rows = db.select('GRADES', PID=pid)
#TODO: It is possible that the date field is empty – if the grades for a
# term have been entered, but no reports generated.
# Is it reasonable to use the TERM in such a case? Not in a date field ...
# Would it be ok to just have the REPORT_TYPE field of a pending term
# report empty? There would need to be a default date ...
# At present I am including undated term reports as _1 or _2 ...
    dates = [_NEWDATE]
    for row in db.select('GRADES', PID=pid):
        dates.append(row['DATE_D'] or '_' + row['TERM'])
    # If the stream, or even school-class have changed since an
    # existing report, the templates and available report types may be
    # different. To keep it simple, a list of all report types from the
    # configuration file GRADES.REPORT_TEMPLATES is presented for selection.
    # An invalid choice can be flagged at the next step.
    # If there is a mismatch between school-class/stream of the pupil as
    # selected on this page and that of the existing GRADES entry, a
    # warning can be shown at the next step.
    rtypes = [rtype for rtype in CONF.GRADES.REPORT_TEMPLATES if rtype[0] != '_']

    form = _Form(KLASS = klass, STREAM = stream, RTYPE = _DEFAULT_RTYPE)
    form.KLASS.choices = [(k, k) for k in reversed(pupils.classes())]
    form.STREAM.choices = [(s, s) for s in CONF.GROUPS.STREAMS]
    form.EDITNEW.choices = [(d, d) for d in dates]
    form.RTYPE.choices = [(t, t) for t in rtypes]

    if form.validate_on_submit():
        # POST
        klass = form.KLASS.data
        stream = form.STREAM.data
        date = form.EDITNEW.data
        rtype = form.RTYPE.data
        kmap = CONF.GRADES.REPORT_TEMPLATES[rtype]
        tfile = match_klass_stream(klass, kmap, stream)
        if tfile:
            return redirect(url_for('bp_grades.make1',
                    pid = pid,
                    klass = klass,
                    stream = stream,
                    date = date,
                    rtype = rtype
            ))
        else:
            flash("Zeugnistyp '%s' nicht möglich für Gruppe %s" % (
                    rtype, toKlassStream(klass, stream)), "Error")

    # GET
    return render_template(os.path.join(_BPNAME, 'pupil.html'),
                            form = form,
                            heading = _HEADING,
                            klass = klass,
                            pname = pname)


#TODO
@bp.route('/make1/<pid>/<rtype>/<date>/<klass>/<stream>', methods=['GET','POST'])
#@admin_required
def make1(pid, rtype, date, klass, stream):
    """View: Edit data for the report to be created, submit to build it.
    """
    return "PID: %s, RTYPE: %s, DATE: %s, CLASS: %s, STREAM: %s" %(
            pid, rtype, date, klass, stream)







@bp.route('/klass/<termn>/<klass_stream>', methods=['GET','POST'])
#@admin_required
def klassview(termn, klass_stream):
    class KlassForm(FlaskForm):
        DATE_D = DateField('Ausgabedatum', validators=[InputRequired()])

    schoolyear = session['year']
    form = KlassForm()
    if form.validate_on_submit():
        # POST
        _d = form.DATE_D.data.isoformat()
        pids=request.form.getlist('Pupil')
        if pids:
            pdfBytes = REPORT.wrap(makeReports,
                    schoolyear, termn, klass_stream, _d, pids)
            session['filebytes'] = pdfBytes
            session['download'] = 'Notenzeugnis_%s.pdf' % klass_stream
            return redirect(url_for('bp_grades.term', termn=termn))
        else:
            flash("** Keine Schüler ... **", "Warning")

    # GET
    form.DATE_D.data = datetime.date.today ()
    klass, stream = fromKlassStream(klass_stream)
    pdlist = db2grades(schoolyear, termn, klass, stream, checkonly=True)
    return render_template(os.path.join(_BPNAME, 'klass.html'),
                            form=form,
                            heading=_HEADING,
                            termn=termn,
                            klass_stream=klass_stream,
                            pupils=pdlist)
#TODO:
# There might be a checkbox/switch for print/pdf, but print might not
# be available on all hosts.
# It might be helpful to a a little javascript to implement a pupil-
# selection toggle (all/none).

@bp.route('/download/<dfile>', methods=['GET'])
#@admin_required
def download(dfile):
    pdfBytes = session.pop('filebytes')
    return send_file(
        io.BytesIO(pdfBytes),
        attachment_filename=dfile,
        mimetype='application/pdf',
        as_attachment=True
    )


@bp.route('/upload/<termn>', methods=['GET','POST'])
#@admin_required
def addgrades(termn):
    class UploadForm(FlaskForm):
        upload = FileField('Notentabelle:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Notentabelle')
        ])

    def readdata(f):
        gtbl = readGradeTable(f)
        grades2db(session['year'], gtbl, term=termn)

    form = UploadForm()
    if form.validate_on_submit():
        REPORT.wrap(readdata, form.upload.data)

    return render_template(os.path.join(_BPNAME, 'grades_upload.html'),
                            heading=_HEADING,
                            termn=termn,
                            form=form)


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
