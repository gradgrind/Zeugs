### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/text_cover/text_cover.py

Last updated:  2020-01-18

Flask Blueprint for text report cover sheets

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

from flask import (Blueprint, render_template, request, session,
        send_file, url_for, flash, abort)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

import datetime, io, os
from types import SimpleNamespace

from wz_core.configuration import Dates
from wz_core.db import DB
from wz_core.pupils import Pupils, match_klass_stream
from wz_compat.config import sortingName
from wz_compat.template import getTextTemplate, getTemplateTags, pupilFields
from wz_text.coversheet import makeSheets, makeOneSheet

_HEADING = "Textzeugnis"

class DateForm(FlaskForm):
    DATE_D = DateField('Ausgabedatum',
                            validators=[InputRequired()])

    def getDate(self):
        return self.DATE_D.data.isoformat()

    def defaultIssueDate(self, schoolyear):
        db = DB(schoolyear)
        _date = db.getInfo('TEXT_DATE_OF_ISSUE')
        if not _date:
            _date = Dates.getCalendar(schoolyear).get('END')
            if not _date:
                flash("Schuljahresende ('END') fehlt im Kalender für %d"
                        % schoolyear, 'Error')
                _date = Dates.today()
        self.DATE_D.data = datetime.date.fromisoformat(_date)


# Set up Blueprint
_BPNAME = 'bp_text_cover'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET','POST'])
#@admin_required
def index():
    schoolyear = session['year']
    form = DateForm()
    if form.validate_on_submit():
        # POST
        # Store date of issue
        _date = form.getDate()
        db = DB(schoolyear)
        db.setInfo('TEXT_DATE_OF_ISSUE', _date)

    # GET
    form.defaultIssueDate(schoolyear)
    p = Pupils(schoolyear)
    _kmap = CONF.TEXT.REPORT_TEMPLATES['Mantelbogen']
    klasses = [k for k in p.classes() if match_klass_stream(k, _kmap)]
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            form=form,
                            heading=_HEADING,
                            klasses=klasses) #['01', '01K', '02', '02K', '03', '03K']


@bp.route('/klass/<klass>', methods=['GET','POST'])
#@admin_required
def klassview(klass):
    form = DateForm()
    # Set date
    schoolyear = session['year']
    if form.validate_on_submit():
        # POST
        _d = form.getDate()
        pdfBytes = makeSheets (schoolyear, _d, klass,
#TODO check list not empty ...
                pids=request.form.getlist('Pupil'))
        return send_file(
            io.BytesIO(pdfBytes),
            attachment_filename='Mantel_%s.pdf' % klass,
            mimetype='application/pdf',
            as_attachment=True
        )
    # GET
    form.defaultIssueDate(schoolyear)
    p = Pupils(schoolyear)
    pdlist = p.classPupils(klass)
    return render_template(os.path.join(_BPNAME, 'text_cover_klass.html'),
                            form=form,
                            heading=_HEADING,
                            klass=klass,
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
    schoolyear = session['year']
    template = getTextTemplate('Mantelbogen', klass)
    tags = getTemplateTags(template)
    _fields = dict(pupilFields(tags))
    fields = [(f0, f1) for f0, f1 in CONF.TABLES.PUPILS_FIELDNAMES.items()
            if f0 in _fields]
    form = DateForm()
    if form.validate_on_submit():
        # POST
        _d = form.getDate()
        pupil = SimpleNamespace (**{f: request.form[f] for f, _ in fields})
        pdfBytes = makeOneSheet(schoolyear, _d, klass, pupil)
        return send_file(
            io.BytesIO(pdfBytes),
            attachment_filename='Mantel_%s.pdf' % sortingName(
                    pupil.FIRSTNAMES, pupil.LASTNAME),
            mimetype='application/pdf',
            as_attachment=True
        )
    # GET
    form.defaultIssueDate(schoolyear)
    p = Pupils(schoolyear)
    try:
        pdlist = p.classPupils(klass)
        pdata = pdlist.pidmap[pid]
        pupil = {f: (fname, pdata[f]) for f, fname in fields}
    except:
        abort(404)
    return render_template(os.path.join(_BPNAME, 'text_cover_pupil.html'),
                            form=form,
                            heading=_HEADING,
                            klass=klass,
                            pupil=pupil)
