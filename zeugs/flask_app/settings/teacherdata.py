### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/settings/pupildata.py

Last updated:  2020-05-21

Flask Blueprint for updating teacher data.

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

_HEADING = "Lehrkräfte"   # page heading

# Messages
# ---


import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, redirect, flash)
from flask import current_app as app

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

#from wz_core.db import DBT
#from wz_core.configuration import Dates
from wz_core.teachers import readTeacherTable, exportTeachers


# Set up Blueprint
_BPNAME = 'bp_teacherdata'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
def index():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


### Upload a table containing all necessary information about the teachers.
@bp.route('/upload', methods=['GET','POST'])
def upload():
    """View: allow a file (teacher table) to be uploaded to the server.
    Existing data will be overwritten.
    """
    class UploadForm(FlaskForm):
        upload = FileField('Lehrkräfte:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Lehrertabelle')
        ])

    schoolyear = session['year']
    form = UploadForm()
    if form.validate_on_submit():
        # POST
        fpath = REPORT.wrap(readTeacherTable, schoolyear, form.upload.data,
                suppressok=True)
        if fpath:
            flash("Die Daten der Lehrkräfte wurden von '%s' aktualisiert"
                    % fpath, "Info")
            return redirect(url_for('bp_settings.index'))

    # GET
    return render_template(os.path.join(_BPNAME, 'teachers_upload.html'),
                            heading=_HEADING,
                            form=form)


@bp.route('/export', methods=['GET'])
def export():
    """View: Export the teacher database table for the current year as
    an xlsx spreadsheet.
    """
    schoolyear = session['year']
    xlsxBytes = REPORT.wrap(exportTeachers, schoolyear, suppressok=True)
    if xlsxBytes:
        session['filebytes'] = xlsxBytes
        return redirect(url_for('download',
                dfile = 'Lehrer-%d.xlsx' % schoolyear))
    return redirect(url_for('bp_settings.index'))

