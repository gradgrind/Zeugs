# python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/auth/auth.py

Last updated:  2020-02-10

Flask Blueprint for user authentication (login).

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


#TODO: Check imports

import os, time

from flask import (Blueprint, g, redirect, render_template, request,
        session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, StopValidation

from wz_table.dbtable import dbTable
from wz_core.configuration import Paths
from wz_core.teachers import Users


# Set up Blueprint
_BPNAME = 'bp_auth'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found

##### LOGIN #####
_BADUSER = "Ungültiger Benutzername"
_BADPW = "Falsches Passwort"

class LoginForm(FlaskForm):
    USER = StringField('Benutzername', validators=[DataRequired()])
    def validate_USER(form, field):
        if not Users().valid(field.data):
            raise StopValidation(_BADUSER)

    PASSWORD = PasswordField('Passwort', validators=[DataRequired()])
    def validate_PASSWORD(form, field):
        user = form.USER.data
        try:
            pwhash = Users().getHash(user)
        except:
            return
        if not check_password_hash(pwhash, field.data):
            raise StopValidation(_BADPW)

    submit = SubmitField('Einloggen')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session.clear()
        tid = form.USER.data
        permission = Users().permission(tid)
        session['user_id'] = tid
        session['permission'] = permission
        # The logging handler will be set when needed, see the start module
        # (<flask_app.__init__>, method <logger>):
        session['logger'] = None
        # Set the school-year to the latest one:
        session['year'] = Paths.getYears()[0]
        session.permanent = True

        # Delete old session files
        sdir = current_app.config['SESSION_FILE_DIR']
        now = time.time()
        for f in os.listdir(sdir):
            ff = os.path.join(sdir, f)
            delta = (now - os.path.getmtime(ff))/86400
            if delta > 2:
                os.remove(ff)

    if session.get('user_id'):
        return redirect(url_for('dispatch'))
    return render_template(os.path.join(_BPNAME, 'login.html'), form=form)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


"""
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('bp_auth.login'))

        return view(**kwargs)

    return wrapped_view
"""
