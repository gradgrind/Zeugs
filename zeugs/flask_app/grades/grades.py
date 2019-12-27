### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades.py

Last updated:  2019-12-24

Flask Blueprint for grade reports

=+LICENCE=============================
Copyright 2019 Michael Towers

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

import datetime, io, os
from types import SimpleNamespace

from flask import (Blueprint, render_template, request, session,
        send_file, url_for, abort, redirect, flash)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
from werkzeug.utils import secure_filename

from wz_core.configuration import Dates
from wz_core.pupils import Pupils
from wz_compat.config import sortingName, toKlassStream
from wz_compat.grades import GRADE_TEMPLATES, findmatching
from wz_grades.gradedata import grade_data
from wz_grades.makereports import makeReports

_HEADING = "Notenzeugnis"

# Set up Blueprint
_BPNAME = 'bp_grades'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
#@admin_required
def index():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


@bp.route('/term/<termn>', methods=['GET','POST'])
#@admin_required
def term(termn):
    class TermForm(FlaskForm):
        DATE_D = DateField('Ausgabedatum', validators=[InputRequired()])
        KLASS = SelectField('Klasse/Gruppe')

    form = TermForm()
    schoolyear = session['year']
    try:
        kmap = GRADE_TEMPLATES[termn]
    except KeyError:
        abort(404)
    p = Pupils(schoolyear)
    klasses = []
    # Only if all groups have the same template
    # can the whole klass be done together.
    for c in p.classes():
        allmatch = True     # whole klass possible
        template = None     # for template matching
        klist = []          # klass.stream list
        for s in p.streams(c):
            ks = toKlassStream(c, s, forcestream=True)
            rtype_tpl = findmatching(ks, kmap)
            if rtype_tpl:
                klist.append(toKlassStream(c, s))
                if template:
                    if rtype_tpl[1] != template:
                        allmatch = False
                else:
                    template = rtype_tpl[1]
            else:
                allmatch = False
        if allmatch:
            # Add the whole class as an option
            klasses.append (c)
            if len(klist) > 1:
                # Only add the individual groups if there are more than one
                klasses += klist
        else:
            klasses += klist
    form.KLASS.choices = [(k, k) for k in klasses]
    if form.validate_on_submit():
        klass_stream = form.KLASS.data
        g = grade_data(schoolyear, termn=termn, klass_stream=klass_stream)
        if not g:
            return redirect(url_for('bp_grades.nogrades',
                    klass_stream = klass_stream, termn = termn))

        date = str(form.DATE_D.data)
#TODO
        return "??? %s:%s %s (%s)" % (schoolyear, termn, klass_stream, date)

#TODO: get date from year data
    form.DATE_D.data = datetime.date.fromisoformat(
            '2020-01-29' if termn == '1' else '2020-07-15')
    errors = []
    return render_template(os.path.join(_BPNAME, 'term.html'),
                            heading=_HEADING,
                            termn=termn,
                            form=form,
                            errors=errors)


@bp.route('/nogrades/<klass_stream>/<termn>', methods=['GET','POST'])
#@admin_required
def nogrades(klass_stream, termn):
#TODO
#TODO: Get from file? ... upload?
    return "%s: Keine Noten für  %s im Halbjahr %s" % (
            session['year'], klass_stream, termn)




@bp.route('/single/<rtype>', methods=['GET','POST'])
#@admin_required
def single(rtype):
    return "TODO report type %s" % rtype


@bp.route('/upload/<termn>', methods=['GET','POST'])
#@admin_required
def addgrades(termn):
#    return "%s: TODO upload for term %s" % (session['year'], termn)

    class UploadForm(FlaskForm):
        upload = FileField('Notentabelle:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'nur Tabellen')
        ])

    form = UploadForm()
    if form.validate_on_submit():
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

        from wz_grades.gradedata import readGradeTable
        def readdata(f):
            gtbl = readGradeTable(f)

#            flash("INFO: %s" % repr(gtbl.info))
#        flash("DATA: %s" % repr(gtbl))

            transl = CONF.TABLES.COURSE_PUPIL_FIELDNAMES
            y0, y1 = session['year'], int(gtbl.info[transl['SCHOOLYEAR']])
            if y1 != y0:
                REPORT.Fail("Falsches Jahr: %s in %s" % (y1, f.filename))
#TODO: Check that the data matches year and term.
            REPORT.Info("Datei erfasst: %s" % f.filename)

        REPORT.wrap(readdata, f)

#TODO: make a wrapper for run/trap/print, taking handler function?
# Maybe pass the error message to the logfile but not the display?

#TODO: signal success

    return render_template(os.path.join(_BPNAME, 'grades_upload.html'),
                            heading=_HEADING,
                            termn=termn,
                            form=form)






###### old ############################################################

#TODO: the date should be saved with the year ...
_date = '2020-07-15'
class DateForm(FlaskForm):
    DATE_D = DateField('Ausgabedatum',
                            default=datetime.date.fromisoformat(_date),
                            validators=[InputRequired()])


@bp.route('/klass/<klass>', methods=['GET','POST'])
#@admin_required
def klassview(klass):
    form = DateForm()
    if form.validate_on_submit():
        # POST
        _d = form.DATE_D.data.isoformat()

#TODO
        pdfBytes = makeSheets (session['year'], _d, klass,
#TODO check list not empty ...
                pids=request.form.getlist('Pupil'))
        return send_file(
            io.BytesIO(pdfBytes),
            attachment_filename='Notenzeugnis_%s.pdf' % klass,
            mimetype='application/pdf',
            as_attachment=True
        )
    # GET
    p = Pupils(session['year'])
    pdlist = p.classPupils(klass)
    klasses = [k for k in p.classes() if k >= '01' and k < '13']
    return render_template(os.path.join(_BPNAME, 'grades_klass.html'),
                            form=form,
                            heading=_HEADING,
                            klass=klass,
                            streams=p.streams(klass),
                            klasses=klasses,
                            pupils=[(pd['PID'], pd.name()) for pd in pdlist])
#TODO:
# There might be a checkbox/switch for print/pdf, but print might not
# be available on all hosts.
# It might be helpful to a a little javascript to implement a pupil-
# selection toggle (all/none).

#TODO: generate a zip of all classes ...
def _allklasses(schoolyear, klasses):
    pass


@bp.route('/pupil/<klass>/<pid>', methods=['GET','POST'])
#@admin_required
def pupilview(klass, pid):
    fields = pupilFields(klass)
    form = DateForm()
    if form.validate_on_submit():
        # POST
        _d = form.DATE_D.data.isoformat()
        pupil = SimpleNamespace (**{f: request.form[f] for f, _ in fields})
        pdfBytes = makeOneSheet(session['year'], _d, klass, pupil)
        return send_file(
            io.BytesIO(pdfBytes),
            attachment_filename='Mantel_%s.pdf' % sortingName(
                    pupil.FIRSTNAMES, pupil.LASTNAME),
            mimetype='application/pdf',
            as_attachment=True
        )
    # GET
    p = Pupils(session['year'])
    pdlist = p.classPupils(klass)
    pupils = []
    for pdata in pdlist:
        _pid = pdata['PID']
        pupils.append((_pid, pdata.name()))
        if _pid == pid:
            pupil = {f: (fname, pdata[f]) for f, fname in fields}
    return render_template(os.path.join(_BPNAME, 'text_cover_pupil.html'),
                            form=form,
                            heading=_HEADING,
                            klass=klass,
                            pupil=pupil,
                            pupils=pupils)
