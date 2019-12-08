### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/auth/auth.py

Last updated:  2019-12-08

Flask Blueprint for user authentication (login).

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


#TODO: Check imports

#import functools

from flask import (Blueprint, g, redirect, render_template, request,
        session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, StopValidation

from wz_table.dbtable import dbTable

class Users:
    def __init__(self):
        self.udb = dbTable(current_app.config['USERS'],
                translate = CONF.TABLES.TEACHER_FIELDNAMES)

    def valid(self, tid):
        return tid in self.udb

    def getHash(self, tid):
        return self.udb[tid]['PASSWORD']

    def permission(self, tid):
        return self.udb[tid]['PERMISSION']


# Set up Blueprint
bp = Blueprint('bp_auth',           # internal name of the Blueprint
        __name__,                   # allows the current package to be found
        template_folder='templates') # package-local templates

##### LOGIN #####
#TODO: Implement a real user-db, then remove the test data ...
_USERDATA = {
    'u1': ('UID100', 'Ernst Normalbenutzer',
            generate_password_hash('passu1'), 1),

    'a1': ('UID1', 'Ina Alleskönner',
            generate_password_hash('passa1'), 5)
}
_BADUSER = "Ungültiger Benutzername"
_BADPW = "Falsches Passwort"

class LoginForm(FlaskForm):
    USER = StringField('Benutzername', validators=[DataRequired()])
    def validate_USER(form, field):
        if not Users().valid(field.data):
#TODO:
#        if field.data not in _USERDATA:
            raise StopValidation(_BADUSER)

    PASSWORD = PasswordField('Passwort', validators=[DataRequired()])
    def validate_PASSWORD(form, field):
        user = form.USER.data
#TODO:
        try:
            pwhash = Users().getHash(user)
#            pwhash = _USERDATA[user][2]
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
#TODO:
#        userdata = _USERDATA[form.USER.data]
#        session['user_id'] = userdata[0]
#        session['level'] = userdata[3]
#TODO:
        session['year'] = 2020
#        print("LOGGED IN:", userdata)
#TODO: remove:
        print("LOGGED IN:", tid, permission)
        return redirect(url_for('bp_text_cover.textCover'))
    return render_template('login.html', form=form)


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
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
"""
