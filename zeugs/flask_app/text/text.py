### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/text_cover/text.py

Last updated:  2019-12-11

Flask Blueprint for text reports

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

#TODO ...

from flask import (Blueprint, render_template, request, send_file,
        session, url_for)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import RadioField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired

import os, datetime, io
#from types import SimpleNamespace

from wz_core.configuration import Dates
#from wz_text.checksubjects import makeSheets as tSheets
from wz_text.summary import tSheets, ksSheets
#from wz_text.print_klass_subject_teacher import makeSheets as ksSheets

# Filenames for downloading
_TEACHER_TABLE = 'Lehrer-Klasse-Tabelle'
_KLASS_TABLE = 'Klasse-Fach-Tabelle'

_HEADING = "Textzeugnis"

#TODO: the date should be saved with the year ...
_date = '2020-07-15'
class DateForm(FlaskForm):
    DATE_D = DateField('Ausgabedatum',
                            default=datetime.date.fromisoformat(_date),
                            validators=[InputRequired()])

# Set up Blueprint
_BPNAME = 'bp_text'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET','POST'])
def index():
#    p = Pupils(_schoolyear)
#    klasses = [k for k in p.classes() if k >= '01' and k < '13']
#TODO: Maybe a validity test for text report classes?
#TODO: DATE_D
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING,
                            DATE_D=Dates.dateConv(_date),
                            uplink=url_for('index'),
                            uplink_help="Zeugs: Startseite")


#TODO: Put something "like" this in the db?
def getManager():
    return {
        "name": "Michael Towers",
        "mail": "michael.towers@waldorfschule-bothfeld.de"
    }

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
        if form.choice.data == 'teachers':
            pdfBytes = tSheets(session['year'],
                            getManager()['name'],
                            Dates.today())
            filename = _TEACHER_TABLE
        elif form.choice.data == 'classes':
            pdfBytes = ksSheets(session['year'],
                            getManager()['name'],
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


