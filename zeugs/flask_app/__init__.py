### python >= 3.7
# -*- coding: utf-8 -*-
# Start only using run-zeugs.sh in top-level folder to use the production
# server, or run-gui.sh for the development server.

"""
flask_app/__init__.py

Last updated:  2020-05-21

The Flask application: zeugs front-end.

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

import os, sys, datetime, io, builtins
builtins.active_year =  None

from flask import (Flask, render_template, request, redirect, session,
        send_from_directory, url_for, flash, make_response, send_file,
        abort
    )
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

from wz_core.configuration import init, Paths
from wz_core.db import DBT

ZEUGS_BASE = os.environ['ZEUGS_BASE']

# USER LEVELS: values chosen such that comparisons work logically ...
NO_USER = 0
NORMAL_USER = 1
ADMIN_USER = 2
X_USER = 3


ERROR_TYPES = {
    -1: "Test",     # Test
    0: "(-->)",     # Output
    2: "",          # Info
    4: "Warnung",   # Warning
    6: "Fehler",    # Error
    8: "Kritischer Fehler", # Fail
    9: "Programmfehler" # Bug
}

def logger(messages, suppressok):
    l = session.get('logger')
    if not l:
        user = session.get('user_id', '##')
        now = datetime.datetime.now()
        # Make new log-file
        l = now.isoformat(timespec='seconds') + '-' + user
        session['logger'] = l
        session['messages'] = []
    mimax = -10
    toflash = []
    for mi, mt, msg in messages:
        if mi > 9:
            msg = "Unerwarter Programmfehler: siehe Log-Datei %s" % l
        elif mi > mimax:
            mimax = mi
        try:
            etype = ERROR_TYPES[mi]
        except:
            etype = "ERROR %d" % mi
            mimax = 10
        toflash.append ((etype + '::: ' + msg, mt))

    # Add a headline (the template will render this to the top, visible, line)
    if mimax >= 6:
        toflash.append(("!!! Aktion mit Fehler(n) abgeschlossen ...",
                "Error"))
    elif mimax >= 4:
        toflash.append(("*** Aktion mit Warnung(en) abgeschlossen ...",
                "Warning"))
    elif not suppressok:
        toflash.append(("+++ Aktion erfolgreich abgeschlossen ...",
                "Info"))
    if toflash:
        # Keep 3 message groups
        session['messages'] = session['messages'][-2:]
        session['messages'].append(toflash)
    for msg in toflash:
        flash(*msg)
    return Paths.logfile(l)


def isPOST(form):
    """Test for POST method and validate form.
    Return <True> if valid POST.
    """
    if request.method == 'POST':
        if form.validate():
            return True
        else:
            for e, val in form.errors.items():
                flash("%s: %s" % (e, val), "Error")
            flash("Validation Error", "Fail")
    return False


ZEUGS_DATA = init(None, xlog=logger)

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_path=ZEUGS_DATA,
            instance_relative_config=True,
            static_folder=os.path.join(ZEUGS_BASE, 'static'),
            template_folder=os.path.join(ZEUGS_BASE, 'templates'))
    app.isPOST = isPOST
    SECRET_KEY0 = "not-very-secret" # generate real one with: os.urandom(24)
#    SECRET_KEY0 = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    app.config.from_mapping(
        SECRET_KEY = SECRET_KEY0,
#        DATABASE = os.path.join(app.instance_path, 'flask.sqlite'),
    )
    if test_config is None:
        # Load the config from the instance directory, if it exists, when not testing
        # Might be better to get secret key from environment?
        # Are there any other differences to development mode?
        app.config.from_pyfile('flaskconfig.py',
                silent=(app.config['ENV']=='development'))
        if (app.config['SECRET_KEY'] == SECRET_KEY0
                and app.config['ENV'] != 'development'):
            raise ValueError("Must set SECRET_KEY")
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
# For more configuration options see Configuration Handling in the flask docs.

    # Set up Flask-Session
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(app.instance_path, 'flask_session')
    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=20)
    # The following line stops caching of "downloaded" files by the
    # browser. This is good (necessary!) for dynamically generated files,
    # but it also prevents caching of css (and js), which might be annoying?
    #    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    # Dynamic file generation is handled at present in the download
    # view (see grades/grades.py:download()).

    Session(app)
#    for k,v in app.config.items():
#        print ("§§§ %s:" % k, v)

    # Register csrf protection
    csrf.init_app(app)

    from .auth import auth
    app.register_blueprint(auth.bp, url_prefix='/auth')

    @app.before_request
    def check_access():
        """Handle access to pages which require authentication.
        """
        session.modified = True     # to hinder session expiry
        request_endpoint = request.endpoint
        request_path = request.path
#        print ("--->", request_endpoint)
#        print (" @@@", request_path)

        if request_endpoint in (None, 'bp_auth.login', 'static', 'zeugs_data'):
            return None
        if (request_endpoint.endswith('index')
                or request_endpoint.endswith('_info')):
            return None
        perms = access()
#TODO: Maybe 'x' can do more than 's'?
        if perms >= ADMIN_USER: return None
        if not perms:
            session['redirect_login'] = request_endpoint
            return redirect(url_for('bp_auth.login'))
        if request_endpoint.endswith('_user'):
            return None
        abort(404)


#    # No caching at all for API endpoints.
#    @app.after_request
#    def add_header(response):
#        response.cache_control.no_store = True
##        response.cache_control.no_cache = True
##        response.cache_control.max_age = 0
##        response.cache_control.must_revalidate = True
#        return response

#@app.context_processor? (see templating docs for flask)

    @app.template_global()
    def access():
        perms = session.get('permission')
        if perms:
            if 'x' in perms: return X_USER
            if 's' in perms: return ADMIN_USER
            return NORMAL_USER
        return NO_USER


    DBT()   # set up <builtins.active_year>
    @app.template_global()
    def activeYear():
        return active_year


    @app.route('/', methods=['GET'])
    def index():
        """The landing page.
        """
        return render_template('index.html')


    # Links to useful functions
    @app.route('/logs', methods=['GET'])
    def logs():
        """Show the most recent logs.
        """
        return render_template('logs.html')


    @app.route('/zeugs_data/<path:filename>', methods=['GET'])
    def zeugs_data(filename):
        """Serve images (etc.?) from the data area.
        """
        _dir = os.path.join(ZEUGS_DATA, *CONF.PATHS.DIR_TEMPLATES)
        return send_from_directory(os.path.join(ZEUGS_DATA,
                *CONF.PATHS.DIR_TEMPLATES),
                               filename)


    from .settings import settings
    app.register_blueprint(settings.bp, url_prefix='/settings')

    from .text import text
    app.register_blueprint(text.bp, url_prefix='/text_report')

    from .text_cover import text_cover
    app.register_blueprint(text_cover.bp, url_prefix='/text_cover')

    from .grades import grades
    app.register_blueprint(grades.bp, url_prefix='/grade_report')

    from .grades import abitur
    app.register_blueprint(abitur.bp, url_prefix='/abitur')

    from .settings import pupildata
    app.register_blueprint(pupildata.bp, url_prefix='/pupils')

    from .settings import teacherdata
    app.register_blueprint(teacherdata.bp, url_prefix='/teachers')


    ### Handle download link for generated files.
    @app.route('/download/<dfile>', methods=['GET'])
    def download(dfile):
        """Handle downloading of generated files.
        The files are not stored permanently. Only one is available (per
        session) and when it has been downloaded – or just clicked on – it
        will be removed.
        """
        ftype = dfile.rsplit('.', 1)[-1]
        if ftype == 'pdf':
            mimetype = 'application/pdf'
        elif ftype == 'xlsx':
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            mimetype = None
            flash("Unbekannte Dateitype: " + ftype, "Error")
        try:
            pdfBytes = session.pop('filebytes')
        except:
            flash("Die Datei '%s' steht nicht mehr zur Verfügung" % dfile, "Warning")
            return redirect(request.referrer)
        response = make_response(send_file(
            io.BytesIO(pdfBytes),
            attachment_filename=dfile,
            mimetype=mimetype,
            as_attachment=True
        ))
        # Prevent caching:
        response.headers['Cache-Control'] = 'max-age=0'
        return response


    return app
