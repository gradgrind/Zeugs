##### python >= 3.7: Start only using run-zeugs.sh in top-level folder.
# -*- coding: utf-8 -*-

"""
flask_app/__init__.py

Last updated:  2019-12-26

The Flask application: zeugs front-end.

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

import os, sys, datetime

from flask import (Flask, render_template, request, redirect, session,
        send_from_directory, url_for, flash)
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

ZEUGS_BASE = os.environ['ZEUGS_BASE']
ZEUGS_DATA = os.path.join (ZEUGS_BASE, 'zeugs_data')
from wz_core.configuration import init, Paths

from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()


def logger(messages):
    for mi, mt, msg in messages:
        flash(mt + '::: ' + msg, mt)
    l = session.get('logger')
    if not l:
        user = session.get('user_id', '##')
        l = datetime.datetime.now().isoformat(timespec='seconds') + '-' + user
        session['logger'] = l
    return Paths.logfile(l)

init(ZEUGS_DATA, xlog=logger)


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_path=ZEUGS_DATA,
            instance_relative_config=True,
            static_folder=os.path.join(ZEUGS_BASE, 'static'),
            template_folder=os.path.join(ZEUGS_BASE, 'templates'))
    app.config.from_mapping(
#       SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess',
        SECRET_KEY = 'not-very-secret', # generate with: os.urandom(24)
#        DATABASE = os.path.join(app.instance_path, 'flask.sqlite'),
        USERS = os.path.join(app.instance_path, 'users'),
    )
#    app.config.from_object('flask_config') # Load module config.py (this directory).
    if test_config is None:
        # Load the config from the instance directory, if it exists, when not testing
        # Might be better to get secret key from environment?
        # Are there any other differences to development mode?
        app.config.from_pyfile('flaskconfig.py',
                silent=(app.config['ENV']=='development'))
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

#    for k,v in app.config.items():
#        print ("§§§ %s:" % k, v)

    # Register csrf protection
    csrf.init_app(app)

#    from . import db
#    db.init_app(app)

    from .auth import auth
    app.register_blueprint(auth.bp, url_prefix='/auth')

    @app.before_request
    def check_access():
        """Handle access to pages which require authentication.
        """
        request_endpoint = request.endpoint
        request_path = request.path
        print ("--->", request_endpoint)
        print (" @@@", request_path)

        if request_endpoint in (None, 'index', 'bp_auth.login', 'static', 'zeugs_data'):
            return None
        if request_endpoint.startswith('bp_info.'):
            return None
#        print ("SESSION:", session)
        perms = session.get('permission', '')
        print("ACCESS:", perms, request_endpoint, request_path)
#TODO: more elaborate access controls ...
        if 's' in perms:
            return None
        if 'u' in perms and request_path.startswith ('/user/'):
            return None
        return redirect(url_for('bp_auth.login'))


    @app.route('/', methods=['GET','POST'])
    def index():
        """The landing page.
        """
        """
        ### Some test code ...
        from flask import render_template_string
        from wtforms import SelectMultipleField, SubmitField
        from wtforms.widgets import ListWidget, CheckboxInput
        class MultiCheckboxField(SelectMultipleField):
            widget = ListWidget(prefix_label=False)
            option_widget = CheckboxInput()
            def iter_choices(self):
                '''Overridden method to force all boxes to 'checked'.
                '''
                for value, label in self.choices:
                    yield (value, label, True)

        class ExampleForm(FlaskForm):
            example = MultiCheckboxField(
                'Pick Things!',
                choices=[('value_a','<a href="/Page_A">Value A</a>'),
                         ('value_b','Value B'),
                         ('value_c','Value C')],
#                default=['value_a','value_c']
            )
            submit = SubmitField('Post')
        form = ExampleForm()
        #if request.method == 'POST':
        if form.validate_on_submit():
            return repr(form.example.data)
        return render_template_string('<form method="POST">'
                                      '{{ form.csrf_token }}'
                                      '{{ form.example }}'
                                      '{{ form.submit }}</form>'
                ,form=form)


        if request.method == 'POST':
#TODO: validation ...
            return 'Pupils: {}'.format(
                    repr(request.form.getlist('Pupil')),
#                    repr (request.form))
            )
        return render_template('test1.html')
        """
        return render_template('index.html')


    # Serve images (etc.?) from zeugs data
    @app.route('/zeugs_data/<path:filename>', methods=['GET'])
    def zeugs_data(filename):
        _dir = os.path.join(ZEUGS_DATA, *CONF.PATHS.DIR_TEMPLATES)
        return send_from_directory(os.path.join(ZEUGS_DATA,
                *CONF.PATHS.DIR_TEMPLATES),
                               filename)


    from .text import text
    app.register_blueprint(text.bp, url_prefix='/text_report')

    from .text_cover import text_cover
    app.register_blueprint(text_cover.bp, url_prefix='/text_cover')

    from .grades import grades
    app.register_blueprint(grades.bp, url_prefix='/grade_report')

    return app
