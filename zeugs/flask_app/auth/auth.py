# Check imports

# A flask "Blueprint" for authentication.
import functools

from flask import (
    Blueprint, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

# Set up Blueprint
bp = Blueprint('bp_auth',           # internal name of the Blueprint
        __name__,                   # allows the current package to be found
        template_folder='templates') # package-local templates

"""
@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Ein Benutzername ist notwendig.'
        elif not password:
            error = 'Ein Passwort ist notwendig.'
        elif db.execute(
            'SELECT id FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = 'Benutzer {} ist schon registriert.'.format(username)

        if error is None:
            db.execute(
                'INSERT INTO user (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            db.commit()
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')
"""

##### LOGIN #####
#TODO: Remove the test data ...
_USERDATA = {
    'u1': ('UID100', ),

    'a1': ('UID1', )
}


class LoginForm(FlaskForm):
    USER = StringField('Benutzername', validators=[DataRequired()])
    PASSWORD = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Einloggen')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        print('### Login requested for user {}, pw={}'.format(
            form.USER.data, form.PASSWORD.data))
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

    """
        uname = request.form['USER']
        pword = request.form['PASSWORD']
        print ("### LOGIN:", uname, pword)
#???
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Ungültiger Benutzername.'
        elif not check_password_hash(user['password'], pword):
            error = 'Ungültiges Passwort.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('login.html')
    """


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
