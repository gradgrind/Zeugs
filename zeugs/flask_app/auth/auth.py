### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/auth/auth.py

Last updated:  2020-05-31

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

import os, time, re

from flask import (Blueprint, g, redirect, render_template, request,
        session, url_for, current_app, flash
)
from werkzeug.security import check_password_hash, generate_password_hash

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, StopValidation

from wz_core.teachers import User
from wz_core.db import DBT


# Set up Blueprint
_BPNAME = 'bp_auth'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found

##### LOGIN #####
_BADUSER = "Ungültiger Benutzername"
_BADPW = "Falsches Passwort"

class LoginForm(FlaskForm):
    USER = StringField(validators=[DataRequired()])
    def validate_USER(form, field):
        udata = User(field.data)
        if not udata.valid:
            raise StopValidation(_BADUSER)

    PASSWORD = PasswordField(validators=[DataRequired()])
    def validate_PASSWORD(form, field):
        user = form.USER.data
        try:
            pwhash = User(user).pwh
        except:
            # Will be handled by <validate_USER>
            return
        if not check_password_hash(pwhash, field.data):
            raise StopValidation(_BADPW)

    submit = SubmitField('Einloggen')


def dologin(user, perms):
    session.clear()
    session['user_id'] = user
    session['permission'] = perms
    # The logging handler will be set when needed, see the start module
    # (<flask_app.__init__>, method <logger>):
    session['logger'] = None
#TODO: really? It is good for development work, but maybe in production
# it would be better to have non-permanent sessions?
#    session.permanent = True
    session.permanent = False

    # Delete old session files
    sdir = current_app.config['SESSION_FILE_DIR']
    now = time.time()
    for f in os.listdir(sdir):
        ff = os.path.join(sdir, f)
        delta = (now - os.path.getmtime(ff))/86400
        if delta > 2:
            os.remove(ff)

    # Set the school-year to the current one:
    year = DBT().schoolyear
    session['year'] =  year
    return bool(year)


@bp.route('/login', methods=('GET', 'POST'))
def login():
    try:
        endpoint = session['redirect_login']
    except KeyError:
        endpoint = 'index'
    try:
        zeugs_user = os.environ['ZEUGS_USER']
    except KeyError:
        pass
    else:
        if current_app.config['ENV'] == 'development':
            u = User(zeugs_user)
            if u.valid:
                if dologin(zeugs_user, u.perms):
                    return redirect(url_for(endpoint))
                else:
                    return redirect(url_for('bp_settings.year'))
            else:
                flash("ZEUGS_USER ist fehlerhaft", "Bug")
        else:
            flash("ZEUGS_USER ist nur gültig in 'development'-Modus", "Bug")
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        tid = form.USER.data
        permission = User(tid).perms
        if not dologin(tid, permission):
            # No school-years known
            return redirect(url_for('bp_settings.year'))
    if session.get('user_id'):
        return redirect(url_for(endpoint))
    return render_template(os.path.join(_BPNAME, 'login.html'), form=form)


@bp.route('/logout_user')
def logout_user():
    session.clear()
    return redirect(url_for('index'))



# For use by other modules
class AuthenticationForm(FlaskForm):
    PASSWORD = PasswordField(validators=[DataRequired()])
    def validate_PASSWORD(form, field):
        user = session['user_id']
        pwhash = User(user).pwh
        if not check_password_hash(pwhash, field.data):
            raise StopValidation(_BADPW)


special_characters = r'!$%&/()=?+_#*,.;:<>@-'
class PasswordStrength:
    pw_length = (8, 16, "Das Passwort muss eine Länge von 8 – 16 Zeichen haben.")
    # Note that the '-' is at the end to avoid the need for a backslash:
    pw_chars = [
            ('a-z', 2, "Das Passwort muss mindestens zwei Kleinbuchstaben (a – z) haben."),
            ('A-Z', 2, "Das Passwort muss mindestens zwei Großbuchstaben (A – Z) haben."),
            ('0-9', 2, "Das Passwort muss mindestens zwei Ziffern (0 – 9) haben."),
            # Note that the '-' is at the end to avoid the need for a backslash:
            (special_characters, 2,
                    "Das Passwort muss mindestens zwei Sonderzeichen haben: %s"
                    % special_characters)
        ]
    pw_spaces = "Das Passwort darf keine Leerzeichen enthalten."
    pw_illegal = "Das Passwort darf folgende Zeichen nicht enthalten: %s"

    def __init__(self, pw):
        """Do a basic check on the strength of a password.
        """
        self.fail = []
        if re.search("\s", pw):
            self.fail.append(self.pw_spaces)
            return fail
        if (len(pw) < self.pw_length[0] or len(pw) > self.pw_length[1]):
            self.fail.append(self.pw_length[2])
            return fail
        pn = pw
        for ch, n, msg in self.pw_chars:
            pn, n1 = re.subn('[%s]' % ch, '', pn)
            if n1 < n:
                self.fail.append(msg)
        if pn:
            self.fail.append(self.pw_illegal % pn)


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
