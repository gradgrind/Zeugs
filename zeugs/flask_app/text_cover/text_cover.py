### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/text_cover/text_cover.py

Last updated:  2019-12-07

Flask Blueprint for text report cover sheets

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

from flask import (Blueprint, render_template, request, session,
        send_file, url_for)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

import datetime, io, os
from types import SimpleNamespace

from wz_core.configuration import Dates
from wz_core.pupils import Pupils
from wz_compat.config import sortingName
from wz_text.coversheet import makeSheets, pupilFields, makeOneSheet

_HEADING = "Textzeugnis"

#TODO: the date should be saved with the year ...
_date = '2020-07-15'
class DateForm(FlaskForm):
    DATE_D = DateField('Ausgabedatum',
                            default=datetime.date.fromisoformat(_date),
                            validators=[InputRequired()])

# Set up Blueprint
_BPNAME = 'bp_text_cover'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__,                   # allows the current package to be found
        template_folder='templates') # package-local templates


@bp.route('/', methods=['GET','POST'])
#@admin_required
def index():
    p = Pupils(session['year'])
    klasses = [k for k in p.classes() if k >= '01' and k < '13']
#TODO: Maybe a validity test for text report classes?
#TODO: DATE_D
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING,
                            DATE_D=Dates.dateConv(_date),
                            klasses=klasses) #['01', '01K', '02', '02K', '03', '03K']


@bp.route('/klass/<klass>', methods=['GET','POST'])
#@admin_required
def klassview(klass):
    form = DateForm()
    if form.validate_on_submit():
        # POST
        _d = form.DATE_D.data.isoformat()
        pdfBytes = makeSheets (session['year'], _d, klass,
#TODO check list not empty ...
                pids=request.form.getlist('Pupil'))
        return send_file(
            io.BytesIO(pdfBytes),
            attachment_filename='Mantel_%s.pdf' % klass,
            mimetype='application/pdf',
            as_attachment=True
        )
    # GET
    p = Pupils(session['year'])
    pdlist = p.classPupils(klass)
    klasses = [k for k in p.classes() if k >= '01' and k < '13']
    return render_template(os.path.join(_BPNAME, 'text_cover_klass.html'),
                            form=form,
                            heading=_HEADING,
                            klass=klass,
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
