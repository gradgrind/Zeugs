# python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/text/text.py

Last updated:  2020-02-10

Flask Blueprint for text reports

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

#TODO ...

from flask import (Blueprint, render_template, request, send_file,
        session, url_for)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import RadioField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired

import os, datetime, io

from wz_core.configuration import Dates
from wz_core.teachers import Users
from wz_text.summary import tSheets, ksSheets

# Filenames for downloading
_TEACHER_TABLE = 'Lehrer-Klasse-Tabelle'
_KLASS_TABLE = 'Klasse-Fach-Tabelle'

_HEADING = "Textzeugnis"


# Set up Blueprint
_BPNAME = 'bp_text'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET','POST'])
def index():
#    p = Pupils(_schoolyear)
#    klasses = [k for k in p.classes() if k >= '01' and k < '13']
#TODO: Maybe a validity test for text report classes?
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING,
                            uplink=url_for('dispatch'),
                            uplink_help="Zeugs: Funktionen")



@bp.route('/summary', methods=['GET','POST'])
def summary():
    class RadioForm(FlaskForm):
        choice = RadioField(choices=[
            ('teachers','Kontrollblätter für die Lehrer'),
            ('classes','Fach-Lehrer-Zuordnung für die Klassen')
        ], default='teachers')
    form = RadioForm()
    if form.validate_on_submit():
        # POST
        user = session['user_id']
        name = Users().name(user)
        if form.choice.data == 'teachers':
            pdfBytes = tSheets(session['year'],
                            name,
                            Dates.today())
            filename = _TEACHER_TABLE
        elif form.choice.data == 'classes':
            pdfBytes = ksSheets(session['year'],
                            name,
                            Dates.today())
            filename = _KLASS_TABLE
        else:
            pdfBytes = None
        if pdfBytes:
            return send_file(
                io.BytesIO(pdfBytes),
                attachment_filename=filename + '.pdf',
                mimetype='application/pdf',
                as_attachment=True
            )
    # GET
    return render_template(os.path.join(_BPNAME, 'summary.html'),
                            form=form,
                            heading=_HEADING,
                            uplink=url_for('bp_text.index'),
                            uplink_help="Textzeugnis: Startseite")


