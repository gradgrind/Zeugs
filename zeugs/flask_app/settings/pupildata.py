### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/settings/pupildata.py

Last updated:  2020-05-08

Flask Blueprint for updating pupil data.

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

_HEADING = "Schülerdaten"   # page heading

# Messages
# ---


import datetime, os

from flask import (Blueprint, render_template, request, session,
        url_for, redirect, flash)

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wz_core.db import DBT
from wz_compat.import_pupils import (readRawPupils, DeltaRaw,
        PID_CHANGE, PID_REMOVE, PID_ADD, exportPupils)


# Set up Blueprint
_BPNAME = 'bp_pupildata'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


################## NOTE ##################
# The code here is for a school in which the master pupil-database is
# not directly accessible. The relevant content can be exported to a
# table (spreadsheet) and imported here.
#
# This data should not be taken on blindly, the differences to the
# current local database are listed and can be individually rejected,
# e.g. when it is known that the local information is more accurate
# than the master data (of course in this case the master data should
# be updated as soon as possible).
##########################################

### Upload a pupil table containing all necessary information from the
### school database concerning the pupils.
@bp.route('/upload', methods=['GET','POST'])
def upload():
    """View: allow a file (pupil table) to be uploaded to the server.
    The data will be compared with that in the database, the differences
    will then be presented for selective updating.
    """
# Do I want the option to do a complete reinstall (or initial install)
# from this file? That would mean skipping the selection view.
# It could be a checkbox.
# To initialize a year completely, the starting date would be needed.
# In other cases, that might already be available.
# I suppose in the absence of a startdate, there could be an extra
# compulsory field ...
    class UploadForm(FlaskForm):
        upload = FileField('Schülerdaten:', validators=[
            FileRequired(),
            FileAllowed(['xlsx', 'ods'], 'Schülertabelle')
        ])

    schoolyear = session['year']
    # Get date of first school day
    with DBT(schoolyear) as db:
        startdate = db.getInfo("CALENDAR_FIRST_DAY")
    if not startdate:
        flash("Sie müssen den ersten Schultag setzen.")
        session['nextpage'] = url_for('bp_pupildata.upload')
        return redirect(url_for('bp_settings.calendar'))

    form = UploadForm()
    if form.validate_on_submit():
        # POST
        rawdata = REPORT.wrap(readRawPupils, schoolyear, form.upload.data,
                startdate, suppressok=True)
        if rawdata:
            session['rawpupildata'] = rawdata
            return redirect(url_for('bp_pupildata.update'))

    # GET
    return render_template(os.path.join(_BPNAME, 'pupils_upload.html'),
                            heading=_HEADING,
                            form=form)


@bp.route('/update', methods=['GET','POST'])
def update():
    """View: Present differences between the current pupil database and
    a table providing (supposedly) updated content.
    A list of differences with checkboxes is displayed, so that some can
    be deselected. Submitting the form initiates the actual update.
    """
    def readable(updates):
        """Convert the given changes-list into a human-readable form.
        """
        fnames = DBT.pupilFields()
        changes = []
        for line in updates:
            op, pdata = line[0], line[1]
            if op == PID_CHANGE:
                f = line[2]
                x = "FELD „%s“ (%s -> %s)" % (fnames[f], line[3], pdata[f])
            elif op == PID_ADD:
                x = "NEU"
            elif op == PID_REMOVE:
                x = "ABGANG"
            changes.append("%s: %s" % (pdata.name(), x))
        return changes

    schoolyear = session['year']
#    delta = session.pop('pupildelta', None)
#    if (not delta):
#    if delta.schoolyear != schoolyear:
#        flash("Das Schuljahr stimmt mit den Daten nicht überein", "Error")
#        return redirect('bp_pupildata.upload')
    form = FlaskForm()
    if form.validate_on_submit():
        # POST
        changes = request.form.getlist('Change')
        delta = session.pop('pupildelta', None)
        if not delta:
            flash("Keine Aktualisierungsdaten", "Error")
            return redirect('bp_pupildata.upload')
        if changes:
            updates = REPORT.wrap(delta.updateFromClassDelta, changes)
            # <updates>: {klass -> [delta-item, ...]}
            if updates:
                cmap = [(k, readable(updates[k]))
                        for k in sorted(updates)]
                return render_template(os.path.join(_BPNAME,
                        'pupils_changed.html'),
                                    heading = _HEADING,
                                    changes = cmap)
        else:
            return render_template(os.path.join(_BPNAME,
                    'no_pupils_changed.html'),
                                heading = _HEADING)

    # GET
    rawdata = session.pop('rawpupildata', None)
    if not rawdata:
        return redirect('bp_pupildata.upload')
    delta = REPORT.wrap(DeltaRaw, schoolyear, rawdata, suppressok=True)
    if not delta:
        return redirect('bp_pupildata.upload')

    # Present the changes tagged with school-class.
    cmap = [(k, readable(delta.cdelta[k])) for k in sorted(delta.cdelta)]
    session['pupildelta'] = delta
    return render_template(os.path.join(_BPNAME, 'pupils_update.html'),
                            form = form,
                            heading = _HEADING,
                            kchanges = cmap)


@bp.route('/export', methods=['GET'])
def export():
    """View: Export the pupil database table for the current year as
    an xlsx spreadsheet.
    """
    schoolyear = session['year']
    pdfBytes = REPORT.wrap(exportPupils, schoolyear, suppressok=True)
    if pdfBytes:
        session['filebytes'] = pdfBytes
        return redirect(url_for('download',
                dfile = 'Schueler-%d.xlsx' % schoolyear))
    return redirect('bp_settings.index')
