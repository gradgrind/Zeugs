### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades.py

Last updated:  2019-12-30

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

_HEADING = "Notenzeugnis"


import datetime, io, os
#from types import SimpleNamespace

from flask import (Blueprint, render_template, request, session,
        send_file, url_for, abort, redirect, flash)
#from flask import current_app as app

from flask_wtf import FlaskForm
#from wtforms import SelectField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired #, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
#from werkzeug.utils import secure_filename

from wz_core.configuration import Dates
from wz_core.pupils import Pupils
from wz_compat.config import toKlassStream #, sortingName
from wz_compat.grades import GRADE_TEMPLATES, findmatching
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


@bp.route('/term/<termn>', methods=['GET','POST'])
#@admin_required
def term(termn):
    def prepare(schoolyear, termn, kmap):
        """Gather the possible klasses/streams.
        """
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
        return klasses

    # Start of method
    schoolyear = session['year']
    try:
        kmap = GRADE_TEMPLATES[termn]
    except KeyError:
        abort(404)
    klasses = REPORT.wrap(prepare, schoolyear, termn, kmap,
            suppressok=True)
    if not klasses:
        return index()
    return render_template(os.path.join(_BPNAME, 'term.html'),
                            heading=_HEADING,
                            termn=termn,
                            klasses=klasses)


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
#TODO
            return "GRADE REPORT class %s, {%s/%s}: %s" % (klass_stream,
                    termn, _d, repr(pids))

            pdfBytes = makeReports(schoolyear, termn, klass_stream, _d, pids)
            return send_file(
                io.BytesIO(pdfBytes),
                attachment_filename='Notenzeugnis_%s.pdf' % klass_stream,
                mimetype='application/pdf',
                as_attachment=True
            )
        else:
            flash("** Keine Schüler ... **", "Warning")

    # GET
    cal = Dates.getCalendar(schoolyear)
    form.DATE_D.data = datetime.date.fromisoformat(cal['REPORTS_' + termn])
    pdlist = db2grades(schoolyear, termn, klass_stream, checkonly=True)
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






###### old ############################################################

#TODO: the date should be saved with the year ...
_date = '2020-07-15'
class DateForm(FlaskForm):
    DATE_D = DateField('Ausgabedatum',
                            default=datetime.date.fromisoformat(_date),
                            validators=[InputRequired()])


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
