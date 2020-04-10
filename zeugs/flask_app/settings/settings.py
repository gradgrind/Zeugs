### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/settings/settings.py

Last updated:  2020-04-09

Flask Blueprint for application settings.

=+LICENCE=============================
Copyright 2020 Michael Towers

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

from flask import (Blueprint, render_template, session,
        url_for, flash, redirect)
#from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import SelectField
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Optional

import os, datetime

from wz_core.configuration import Paths, Dates
from wz_core.db import DBT
from wz_table.dbtable import readPSMatrix
from wz_core.pupils import Pupils, Klass


_HEADING = "Einstellungen"

# Set up Blueprint
_BPNAME = 'bp_settings'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
def index():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


@bp.route('/year', methods=['GET','POST'])
def year():
    class YearForm(FlaskForm):
        YEAR = SelectField("Schuljahr", coerce=int)

    schoolyear = session['year']
    form = YearForm()
    form.YEAR.choices = [(y, y) for y in Paths.getYears()]
    if form.validate_on_submit():
        # POST
        y = form.YEAR.data
        if y != schoolyear:
            schoolyear = y
            session['year'] = y
            flash("Schuljahr auf %d gesetzt." % y)

    # GET
    form.YEAR.default = schoolyear
    return render_template(os.path.join(_BPNAME, 'schoolyear.html'),
                            form=form,
                            heading=_HEADING)


@bp.route('/newyear', methods=['GET','POST'])
def newyear():
    return "'newyear' not yet implemented"


@bp.route('/calendar', methods=['GET','POST'])
def calendar():
    class _Form(FlaskForm):
        START_D = DateField("Erster Schultag", validators=[InputRequired()])
        END_D = DateField("Letzter Schultag", validators=[InputRequired()])

    schoolyear = session['year']
    db = DBT(schoolyear)
    form = _Form()
    if form.validate_on_submit():
        # POST
        START_D = form.START_D.data
        END_D = form.END_D.data
        # Check start and end dates
        ystart = datetime.date.fromisoformat(Dates.day1(schoolyear))
        nystart = datetime.date.fromisoformat(Dates.day1(schoolyear+1))
        tdelta = datetime.timedelta(days=60)
        ok = True
        if START_D < ystart:
            ok = False
            flash("Erster Tag vor Schuljahresbeginn", "Error")
        elif START_D > ystart + tdelta:
            ok = False
            flash("Erster Tag > 60 Tage nach Schuljahresbeginn", "Error")
        if END_D >= nystart:
            ok = False
            flash("Letzter Tag nach Schuljahresende", "Error")
        elif END_D < nystart - tdelta:
            ok = False
            flash("Letzter Tag > 60 Tage vor Schuljahresende", "Error")
        if ok:
            with db:
                db.setInfo("CALENDAR_FIRST_DAY", START_D.isoformat())
                db.setInfo("CALENDAR_LAST_DAY", END_D.isoformat())
            nextpage = session.pop('nextpage', None)
            if nextpage:
                return redirect(nextpage)

    # GET
    with db:
        START_D = db.getInfo("CALENDAR_FIRST_DAY")
        if START_D:
            form.START_D.data = datetime.date.fromisoformat(START_D)
        END_D = db.getInfo("CALENDAR_LAST_DAY")
    if END_D:
        form.END_D.data = datetime.date.fromisoformat(END_D)
    return render_template(os.path.join(_BPNAME, 'calendar.html'),
                            form=form,
                            heading=_HEADING)


@bp.route('/subjects', methods=['GET'])
def subjects():
    return "Not yet implemented"


@bp.route('/choices', methods=['GET','POST'])
def choices():

    class UploadForm(FlaskForm):
        upload = FileField('Kurswahl-Tabelle:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Kurswahl-Tabelle')
        ])

    def readdata(f):
        table = readPSMatrix(f)
        choices2db(schoolyear, table)

    schoolyear = session['year']
    form = UploadForm()
    if form.validate_on_submit():
        REPORT.wrap(readdata, form.upload.data)

    pupils = Pupils(schoolyear)
    # List the classes with the oldest pupils first, as these are more
    # likely to have subject choices.
    klasslist = sorted(pupils.classes(), reverse=True)
    try:
        download = session.pop('download')
    except:
        download = None
    return render_template(os.path.join(_BPNAME, 'choices.html'),
                            heading=_HEADING,
                            klasses=klasslist,
                            dfile=download,
                            form=form)


@bp.route('klass_choices/<klass>', methods=['GET'])
def klass_choices(klass):
    """Generate editable subject-choice table to download.
    """
    schoolyear = session['year']
    klass = Klass(klass)
    pdfBytes = REPORT.wrap(choiceTable, schoolyear, klass)
    session['filebytes'] = pdfBytes
    session['download'] = 'Kurswahl_%s.xlsx' % klass.klass
    return redirect(url_for('bp_settings.choices'))
