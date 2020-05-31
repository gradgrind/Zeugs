### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/settings/teacherdata.py

Last updated:  2020-05-31

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

import os

from flask import (Blueprint, render_template, request, session,
        url_for, redirect, flash)
from flask import current_app as app

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from werkzeug.security import generate_password_hash

from wz_core.db import DBT
from wz_core.teachers import TeacherData, readTeacherTable, exportTeachers
from ..auth.passwords import Password
from ..auth.auth import AuthenticationForm, PasswordStrength


# Set up Blueprint
_BPNAME = 'bp_teacherdata'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET'])
def index_s():
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading=_HEADING)


def checkyear():
    thisyear = DBT().schoolyear
    schoolyear = session['year']
    if schoolyear == thisyear:
        return schoolyear
    flash("Lehrerdaten können nur im aktiven Schuljahr (%d) geändert werden"
            % thisyear, "Error")
    return None


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

    schoolyear = checkyear()
    if not schoolyear:
        return redirect(url_for('bp_settings.index'))
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
    """View: export the teacher database table for the current year as
    an xlsx spreadsheet.
    """
    schoolyear = session['year']
    xlsxBytes = REPORT.wrap(exportTeachers, schoolyear, suppressok=True)
    if xlsxBytes:
        session['filebytes'] = xlsxBytes
        return redirect(url_for('download',
                dfile = 'Lehrer-%d.xlsx' % schoolyear))
    return redirect(url_for('bp_settings.index'))


@bp.route('/choose', methods=['GET'])
def choose():
    """View: choose the teacher whose data is to be updated.
    """
    schoolyear = checkyear()
    if not schoolyear:
        return redirect(url_for('bp_settings.index'))
    teachers = TeacherData(schoolyear)
    tlist = []
    for tid in teachers:
        tdata = teachers[tid]
        if tdata['PERMISSION']:
            tlist.append((tdata['TID'], tdata['NAME']))
    return render_template(os.path.join(_BPNAME, 'choose_teacher.html'),
                            heading = _HEADING,
                            tlist = tlist)


@bp.route('/edit/<tid>', methods=['GET', 'POST'])
def edit(tid):
    schoolyear = checkyear()
    if not schoolyear:
        return redirect(url_for('bp_settings.index'))
    try:
        teachers = TeacherData(schoolyear)
        tdata = teachers[tid]
    except:
        abort(404)
    form = FlaskForm()
    if app.isPOST(form):
        # POST
        changes = {}
        # A normal user (generally a teacher) has permission 'u', an
        # administrator 'us'.
        perms = tdata['PERMISSION']
        if request.form.get('perm_s'):
            if 's' not in perms:
                changes['PERMISSION'] = 'u'
        elif 's' in perms:
            changes['PERMISSION'] = 'us'

        for field in 'TID', 'NAME', 'SHORTNAME', 'MAIL':
            newval = request.form[field]
            if newval:
                if newval != tdata[field]:
                    changes[field] = newval
            else:
                badfields.append(field)
        # update database
        tidx = changes.pop('TID', None)
        if tidx:
            # tid changed: create a new entry, checking that the new tid
            # doesn't exist, then delete the old one.
            # First ensure all fields are there:
            for field in 'NAME', 'SHORTNAME', 'MAIL', 'PERMISSION', 'PASSWORD':
                if field not in changes:
                    changes[field] = tdata[field]
            if newTeacher(teachers, tidx, changes):
                teachers.remove(tid)
                flash("Kürzel %s wurde gelöscht" % tid, "Info")
                return redirect(url_for('bp_teacherdata.choose'))
        elif changes:
            teachers.update(tid, changes)
            for f, v in changes.items():
                flash("%s: %s ist jetzt '%s'" % (tid, f, v), "Info")
            flash("Daten für %s wurden aktualisiert"
                    % request.form['NAME'], "Info")
            return redirect(url_for('bp_teacherdata.choose'))
        else:
            flash("%s: keine Änderungen" % tdata['NAME'], "Info")

    # GET
    return render_template(os.path.join(_BPNAME, 'edit_teacher.html'),
                            heading = _HEADING,
                            form = form,
                            tdata = tdata)


def newTeacher(teachers, tid, data):
    if teachers.checkTeacher(tid, report = False):
        flash("Kürzel %s ist schon vergeben" % tid, "Error")
        return False
    teachers.new(tid, data)
    for f, v in data.items():
        if len(v) > 30:
            v = v[:26] + " ..."
        flash("%s: %s = '%s'" % (tid, f, v), "Info")
    flash("Neue Lehrkraft (%s)" % data['NAME'], "Info")
    return True


@bp.route('/new', methods=['GET', 'POST'])
def new():
    schoolyear = checkyear()
    if not schoolyear:
        return redirect(url_for('bp_settings.index'))
    form = FlaskForm()
    if app.isPOST(form):
        # POST
        data = {}
        data['PERMISSION'] = 'us' if request.form.get('perm_s') else 'u'
        for field in 'NAME', 'SHORTNAME', 'MAIL':
            data[field] = request.form[field]
        # Generate a random password
        pw = Password(12).get()
        pwhash = generate_password_hash(pw)
        data['PASSWORD'] = pwhash
        teachers = TeacherData(schoolyear)
        tid = request.form['TID']
        if newTeacher(teachers, tid, data):
            # This is not really an error, it's just for the colour:
            flash("PASSWORT für %s (abschreiben!): %s" % (tid, pw), "Error")
            return redirect(url_for('bp_teacherdata.index'))

    # GET
    return render_template(os.path.join(_BPNAME, 'edit_teacher.html'),
                            heading = _HEADING,
                            form = form,
                            tdata = None)


@bp.route('/pw_user/<tid>', methods=['GET', 'POST'])
def pw_user(tid):
    schoolyear = checkyear()
    if not schoolyear:
        return redirect(url_for('bp_settings.index'))
    try:
        teachers = TeacherData(schoolyear)
        tdata = teachers[tid]
    except:
        abort(404)
    uid = session['user_id']
    if uid == tid:
        ownpw = True
    else:
        perms = session['permission']
        if not ('s' in perms or 'x' in perms):
            abort(404)
        ownpw = False

    form = AuthenticationForm()
    if form.validate_on_submit():
        # POST
        pwd1 = request.form['pwd1']
        pwd2 = request.form['pwd2']
        if pwd1 == pwd2:
            # Check password strength
            fails = PasswordStrength(pwd1).fail
            if fails:
                for f in fails:
                    flash(f, "Warning")
                flash("Ungültiges Passwort", "Error")
            else:
                pwhash = generate_password_hash(pwd1)
                data = {'PASSWORD': pwhash}
                teachers.update(tid, data)
                flash("Passwort geändert für %s" % tid, "Info")
                return redirect(url_for('bp_settings.index'))
        else:
            flash("Die neuen Passwörter stimmen nicht überein", "Error")

    # GET
    return render_template(os.path.join(_BPNAME, 'pw_user.html'),
                            heading = _HEADING,
                            form = form,
                            tdata = tdata,
                            ownpw = ownpw,
                            pwdata = PasswordStrength)


@bp.route('/delete/<tid>', methods=['GET', 'POST'])
def delete(tid):
    schoolyear = checkyear()
    if not schoolyear:
        return redirect(url_for('bp_settings.index'))
    try:
        teachers = TeacherData(schoolyear)
        tdata = teachers[tid]
    except:
        abort(404)
    form = FlaskForm()
    if app.isPOST(form):
        # POST
        teachers.remove(tid)
        flash("Lehrkraft mit Kürzel %s wurde aus der Datenbank entfernt"
                % tid, "Info")
        return redirect(url_for('bp_teacherdata.choose'))

    # GET
    return render_template(os.path.join(_BPNAME, 'delete_teacher.html'),
                            heading = _HEADING,
                            form = form,
                            tdata = tdata)
