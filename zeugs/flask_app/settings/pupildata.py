### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/settings/pupildata.py

Last updated:  2020-06-05

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
        url_for, redirect, flash, abort)
from flask import current_app as app

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wz_core.db import DBT
from wz_core.configuration import Dates
from wz_core.pupils import Pupils, Klass
from wz_compat.import_pupils import (DeltaRaw, exportPupils,
        migratePupils, PID_CHANGE, PID_REMOVE, PID_ADD)
from wz_compat.grade_classes import klass2streams
from wz_compat.config import pupil_xfields, name_filter


# Set up Blueprint
_BPNAME = 'bp_pupildata'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
def index_s():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


@bp.route('/klass', methods=['GET'])
def klass():
    """View: choose the class with the pupil whose data is to be updated.
    """
    schoolyear = session['year']
    pupils = Pupils(schoolyear)
    classes = pupils.classes()
    return render_template(os.path.join(_BPNAME, 'choose_class.html'),
                            heading = _HEADING,
                            classes = classes)


@bp.route('/pupil/<klass>', methods=['GET'])
def pupil(klass):
    """View: choose the pupil whose data is to be updated.
    """
    schoolyear = session['year']
    pupils = Pupils(schoolyear)
    try:
        plist = pupils.classPupils(Klass(klass))
        if not plist:
            raise ValueError
    except:
        abort(404)
    return render_template(os.path.join(_BPNAME, 'choose_pupil.html'),
                            heading = _HEADING,
                            klass = klass,
                            plist = plist)


@bp.route('/new/<klass>', methods=['GET', 'POST'])
def new(klass):
    """View: add new pupil to the given school-class.
    """
    try:
        klass2streams(klass)
    except:
        abort(404)
    schoolyear = session['year']
    pupils = Pupils(schoolyear)
    # Special pupil fields
    xfields = []
    for field, val in pupil_xfields(klass).items():
        title, desc, values = val
        xfields.append((field, title, desc, None, values))
    fieldnames = CONF.TABLES.PUPILS_FIELDNAMES

    form = FlaskForm()
    if app.isPOST(form):
        # POST
        # The html 'required' attribute doesn't block an entry with only
        # spaces! Thus an extra check is done here.
        emptyfields = []
        newvals = {}
        for field in ('PID', 'STREAM', 'FIRSTNAMES', 'LASTNAME',
                    'DOB_D', 'POB', 'SEX', 'HOME', 'ENTRY_D'):
            newval = request.form[field].strip()
            newvals[field] = newval
            if not newval:
                emptyfields.append(field)
        if emptyfields:
            for field in emptyfields:
                flash("Feld '%s' darf nicht leer sein" % fieldnames[field],
                        "Error")
        else:
            # This field *may* be empty
            fname = request.form['FIRSTNAME'].strip() or newvals['FIRSTNAMES']
            newvals['FIRSTNAME'] = fname

            # Manage "custom" fields (XDATA)
            xvals = {}
            for field, desc, val, vals in xfields:
                newval = request.form.get(field).strip()
                if newval:
                    xvals[field] = newval
            newvals['XDATA'] = pdata.setXdata(xvals) if xvals else None

            # Process the names
            ndata = name_filter(newvals['FIRSTNAMES'],
                    newvals['LASTNAME'], newvals['FIRSTNAME'])
            newvals['FIRSTNAMES'] = ndata[0]
            newvals['LASTNAME'] = ndata[1]
            newvals['FIRSTNAME'] = ndata[2]
            newvals['PSORT'] = ndata[3]

            # update database
            newvals['CLASS'] = klass
            pid = newvals['PID']
            if pupils.check_pupil(pid):
                flash("Schülernummer %s existiert schon!" % pid, "Error")
            else:
                pupils.new(newvals)
                flash("Neuer Schüler / neue Schülerin: „%s %s“"
                        % (newvals['FIRSTNAME'], newvals['LASTNAME']), "Info")
                return redirect(url_for('bp_pupildata.pupil', klass=klass))

    # GET
    streams = klass2streams(klass)
    return render_template(os.path.join(_BPNAME, 'edit_pupil.html'),
                            heading = _HEADING,
                            form = form,
                            fieldnames = fieldnames,
                            pdata = None,
                            klass = klass,
                            streams = streams,
                            xfields = xfields)


@bp.route('/change_class/<pid>', methods=['GET', 'POST'])
def change_class(pid):
    schoolyear = session['year']
    pupils = Pupils(schoolyear)
    pdata = REPORT.wrap(pupils.pupil, pid, suppressok = True)
    if not pdata:
        abort(404)

    form = FlaskForm()
    if app.isPOST(form):
        # POST
        newclass = request.form['CLASS']
        if newclass == pdata['CLASS']:
            flash("Die Klasse wurde nicht geändert", "Warning")
        else:
            changes = {'CLASS': newclass}
            streams = klass2streams(newclass)
            if pdata['STREAM'] in streams:
                warn = False
            else:
                warn = True
                changes['STREAM'] = streams[0]
            # Apply changes to db table
            pupils.update(pid, changes)
            flash("Klasse von %s zu %s geändert" % (pdata['CLASS'], newclass),
                    "Info")
            if warn:
                flash("Der Bewertungsmaßstab ist in Klasse %s nicht gültig"
                        % pdata['STREAM'], "Warning")
        return redirect(url_for('bp_pupildata.edit', pid=pid))

    # GET
    klass = Klass(pdata['CLASS'])
    pyear = klass.year
    allclasses = pupils.classes()
    classes = []
    for c in allclasses:
        cx = Klass(c)
        if cx.year < pyear - 1:
            continue
        if cx.year > pyear + 1:
            continue
        classes.append(c)
    return render_template(os.path.join(_BPNAME, 'change_class.html'),
                            heading = _HEADING,
                            form = form,
                            pdata = pdata,
                            classes = classes)


#TODO: is there really a need for this?
@bp.route('/delete/<pid>', methods=['GET', 'POST'])
def delete(pid):
    return "TODO: bp_pupildata::delete(%s)" % pid
    schoolyear = session['year']
    pupils = Pupils(schoolyear)
    pdata = REPORT.wrap(pupils.pupil, pid, suppressok = True)
    if not pdata:
        abort(404)
    class_ = pdata['CLASS']
# One possibility would be to tag the entry so that it is not used after
# the leaving date?


@bp.route('/edit/<pid>', methods=['GET', 'POST'])
def edit(pid):
    schoolyear = session['year']
    pupils = Pupils(schoolyear)
    pdata = REPORT.wrap(pupils.pupil, pid, suppressok = True)
    if not pdata:
        abort(404)
    class_ = pdata['CLASS']
    # Special pupil fields
    xfields = []
    pxmap = pdata.xdata()
    for field, val in pupil_xfields(class_).items():
        title, desc, values = val
        xfields.append((field, title, desc, pxmap.get(field), values))
    fieldnames = CONF.TABLES.PUPILS_FIELDNAMES

    form = FlaskForm()
    if app.isPOST(form):
        # POST
        changes = {}
        # The html 'required' attribute doesn't block an entry with only
        # spaces! Thus an extra check is done here.
        emptyfields = []
        newvals = {}
        for field in ('STREAM', 'FIRSTNAMES', 'LASTNAME',
                    'DOB_D', 'POB', 'SEX', 'HOME', 'ENTRY_D'):
            newval = request.form[field].strip()
            newvals[field] = newval
            if newval:
                if newval != pdata[field]:
                    changes[field] = newval
            else:
                emptyfields.append(field)
        if emptyfields:
            for field in emptyfields:
                flash("Feld '%s' darf nicht leer sein" % fieldnames[field],
                        "Error")
        else:
            # These fields *may* be empty
            fname = request.form['FIRSTNAME'].strip() or newvals['FIRSTNAMES']
            newvals['FIRSTNAME'] = fname
            if fname != pdata['FIRSTNAME']:
                changes['FIRSTNAME'] = fname
            exit_d = request.form['EXIT_D'] or None
            if exit_d != pdata['EXIT_D']:
                changes['EXIT_D'] = exit_d

            # Manage "custom" fields (XDATA)
            xchanges = False
            for field, title, desc, val, vals in xfields:
                newval = request.form.get(field).strip()
                if newval:
                    if newval != val:
                        pxmap[field] = newval
                        xchanges = True
                elif val:
                    del(pxmap[field])
                    xchanges = True
            if xchanges:
                changes['XDATA'] = pdata.setXdata(pxmap)

            # Process the names if there has been a change
            if ('FIRSTNAMES' in changes or 'LASTNAME' in changes
                    or 'FIRSTNAME' in changes):
                ndata = name_filter(newvals['FIRSTNAMES'],
                        newvals['LASTNAME'], newvals['FIRSTNAME'])
                changes['FIRSTNAMES'] = ndata[0]
                changes['LASTNAME'] = ndata[1]
                changes['FIRSTNAME'] = ndata[2]
                changes['PSORT'] = ndata[3]

            # update database
            if changes:
                pupils.update(pid, changes)
                for f, v in changes.items():
                    flash("%s: %s ist jetzt '%s'" % (pid, f, v),
                            "Info")
                flash("Daten für %s wurden aktualisiert"
                        % pdata.name(), "Info")
                return redirect(url_for('bp_pupildata.pupil', klass=class_))
            else:
                flash("%s: keine Änderungen" % pdata.name(), "Info")

    # GET
    streams = klass2streams(class_)
    return render_template(os.path.join(_BPNAME, 'edit_pupil.html'),
                            heading = _HEADING,
                            form = form,
                            fieldnames = fieldnames,
                            pdata = pdata,
                            klass = pdata['CLASS'],
                            streams = streams,
                            xfields = xfields)




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
    # Check date of first school day is set
    with DBT(schoolyear) as db:
        startdate = db.getInfo("CALENDAR_FIRST_DAY")
    if not startdate:
        flash("Sie müssen den ersten Schultag setzen.")
        session['nextpage'] = url_for('bp_pupildata.upload')
        return redirect(url_for('bp_settings.calendar'))

    form = UploadForm()
    if form.validate_on_submit():
        # POST
        rawdata = REPORT.wrap(DeltaRaw, schoolyear, form.upload.data,
                suppressok=True)
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
    delta = session.pop('rawpupildata', None)
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
    xlsxBytes = REPORT.wrap(exportPupils, schoolyear, suppressok=True)
    if xlsxBytes:
        session['filebytes'] = xlsxBytes
        return redirect(url_for('download',
                dfile = 'Schueler-%d.xlsx' % schoolyear))
    return redirect(url_for('bp_settings.index'))

