### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/settings/settings.py

Last updated:  2020-05-22

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
        url_for, flash, redirect, request, send_file, make_response)
from flask import current_app as app

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Optional

import os, datetime, shutil
from zipfile import ZipFile
from io import BytesIO

from wz_core.configuration import Paths, Dates
from wz_core.db import DBT
from wz_core.pupils import Pupils, Klass
from wz_core.setup import newYear
from wz_core.teachers import migrateTeachers
from wz_table.dbtable import readPSMatrix
from wz_compat.grade_classes import choices2db
from wz_compat.import_pupils import migratePupils


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
    def makeNewYear(year, migrate):
        if migrate:
            migratePupils(year)
            migrateTeachers(year)
        newYear(year)
        return True
    # The start date of a new school-year must be after <setyear>. If no
    # year is "set" (which should only be possible during set-up of
    # the application), then no earlier than the beginning of the current
    # school-year.
    # Dates after the next school-year should also not be accepted.
    years = Paths.getYears()        # List of available school-years
    setyear = DBT().schoolyear      # Currently "open" school-year
    thisyear = Dates.getschoolyear() # Current school-year
    # <setyear> and <thisyear> will normally be the same
    form = FlaskForm()
    if app.isPOST(form):
        # POST
        if request.form['action'] == 'new_year':
            day_1 = request.form['day_1_D']
            year_1 = Dates.getschoolyear(day_1)
            if year_1 in years:
                flash("Schuljahr %d ist schon angelegt" % year_1, "Warning")
                return redirect(request.referrer)
            db = DBT(year_1, mustexist = False)
            with db:
                db.setInfo('CALENDAR_FIRST_DAY', day_1)
            lastyear = year_1 - 1
            if lastyear in years:
                # A data migration is possible
                migrate = request.form.get('migrate')
            else:
                migrate = False
            if REPORT.wrap(makeNewYear, year_1, migrate):
                return redirect(url_for('bp_settings.new_year'))
            else:
                return redirect(request.referrer)

        else:
            year = int(request.form['year'])
            if request.form['action'] == 'change':
                if year == session.get('year'):
                    flash("Schuljahr (%d) nicht geändert." % year, "Info")
                else:
                    if year in years:
                        session['year'] = year
                        flash("Schuljahr auf %d gesetzt." % year, "Info")
                return redirect(url_for('bp_settings.index'))

            if request.form['action'] == 'delete':
                return redirect(url_for('bp_settings.delete_year', year = year))

            if request.form['action'] == 'download':
                return redirect(url_for('bp_settings.dl_year', year = year))

        abort(404)

    # GET
    # Possible new years:
    #  - the one after <setyear>
    #  - the current one (<thisyear>)
    #  - the next one (<thisyear + 1>)
    # Ones that already exist are excluded.
    nextyear = thisyear + 1
    MIN_D = None
    if nextyear not in years:
        MIN_D, MAX_D = Dates.checkschoolyear(nextyear)
        if thisyear not in years:
            MIN_D = Dates.day1(thisyear)
    elif thisyear not in years:
        MIN_D, MAX_D = Dates.checkschoolyear(thisyear)
    if setyear:
        nextset = setyear + 1
        if nextset < thisyear and nextset not in years:
            # A special case: the "open" year lies a while back
            if MIN_D:
                MIN_D = Dates.day1(nextset)
            else:
                MIN_D, MAX_D = Dates.checkschoolyear(nextset)
    # If MIN_D is not set, no new year can be created.
    return render_template(os.path.join(_BPNAME, 'schoolyear.html'),
                            form=form,
                            heading=_HEADING,
                            setyear = setyear,
                            years = years,
                            MIN_D = MIN_D,
                            MAX_D = MAX_D)


#TODO
@bp.route('/new_year', methods=['GET'])
def new_year():
    return "New year added: still need things to do (links)"


@bp.route('/delete_year/<int:year>', methods=['GET','POST'])
def delete_year(year):
    years = Paths.getYears()
    if len(years) <= 1:
        flash("Keine Jahre können gelöscht werden", "Error")
        return redirect(url_for('bp_settings.year'))
    setyear = DBT().schoolyear
    if year == setyear:
        flash("Das aktive Jahr kann nicht gelöscht werden", "Error")
        return redirect(url_for('bp_settings.year'))
    thisyear = Dates.getschoolyear()
    if (thisyear - year < 3) and setyear > year:
        flash("Nur ältere Daten können gelöscht werden", "Error")
        return redirect(url_for('bp_settings.year'))

    form = FlaskForm()
    if app.isPOST(form):
        # POST
        if request.form['action'] == 'delete':
            dpath = Paths.getYearPath(year)
            if os.path.isdir(dpath):
                shutil.rmtree(dpath)
            flash("Die Daten für %d wurden gelöscht" % year, "Info")
            session['year'] = setyear
        return redirect(url_for('bp_settings.year'))

    # GET
    return render_template(os.path.join(_BPNAME, 'delete_year.html'),
                            form=form,
                            heading=_HEADING,
                            setyear = setyear,
                            year = year)


@bp.route('/dl_year', methods=['GET'])
@bp.route('/dl_year/<int:year>', methods=['GET'])
def dl_year(year = None):
    if not year:
        year = session.get('year')
        if not year:
            flash("Kein Schuljahr zum Herunterladen", "Error")
            return redirect(url_for('bp_settings.year'))
    ### Prepare a zip-archive of the year for downloading
    ## Get all file paths
    directory = Paths.getYearPath(year)
    if not os.path.isdir(directory):
        flash("Keine Daten für %d" % year, "Error")
        return redirect(url_for('bp_settings.year'))
    # Initialize empty file paths list
    file_paths = []
    ## Crawl through directory and subdirectories
    for root, directories, files in os.walk(directory):
        for filename in files:
            # join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
    ## Write files to zipfile
    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zipm:
        # Write each file one by one, remove root paths!
        l = len(directory)
        for ifile in file_paths:
            zipm.write(ifile, str(year) + ifile[l:])
    memory_file.seek(0)     # Reset reading position (important!)
    response = make_response(send_file(
        memory_file,
        attachment_filename = 'Daten_%d.zip' % year,
        mimetype = 'application/zip',
        as_attachment=True
    ))
    # Prevent caching:
    response.headers['Cache-Control'] = 'max-age=0'
    return response


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
