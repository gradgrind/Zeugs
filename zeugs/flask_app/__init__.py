##### python >= 3.6: Start only using run-zeugs.sh in top-level folder.
# -*- coding: utf-8 -*-
import os, sys
import datetime

from flask import Flask, render_template, request, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

ZEUGS_BASE = os.environ['ZEUGS_BASE']
ZEUGS_DATA = os.path.join (ZEUGS_BASE, 'zeugs_data')
from wz_core.configuration import init
init(ZEUGS_DATA)

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, ZEUGS_DATA, instance_relative_config=True)
#    app.config.from_mapping(
#        SECRET_KEY=os.urandom(24),
#        DATABASE=os.path.join(app.instance_path, 'flask.sqlite'),
#    )

    app.config.from_object('flask_config') # Load module config.py (this directory).
    if test_config is None:
        # load the config from the instance directory, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    """
    @app.route('/textcover/data1', methods=('POST',))
    def data1():
        klass = request.json['klass']
        app.logger.info('REQUEST klass: %s' % klass)
        jsonpeople = {
            "fields": ["itemA", "itemB", "itemC",],
            "pupilList": [
                ["001", "Bernd Förster"],
                ["002", "Juli Läßner"],
                ["003", "Franz Neumann"],
                ["004", "Emily Friederike von Riesighausen"],
            ],
            "pupilData": {
                "001": {"itemA": "val 1A", "itemB": "val 1B", "itemC": "val 1C"},
                "002": {"itemA": "val 2A", "itemB": "val 2B", "itemC": "val 2C"},
                "003": {"itemA": "val 3A", "itemB": "val 3B", "itemC": "val 3C"},
                "004": {"itemB": "val 4B"},
            },
        }
        from time import sleep
        sleep (3)
        return jsonify(jsonpeople)
    """

    from .text_cover import text_cover
    app.register_blueprint(text_cover.bp, url_prefix='/text_cover')

#    from . import db
#    db.init_app(app)

#    from . import auth
#    app.register_blueprint(auth.bp)

#    from . import blog
#    app.register_blueprint(blog.bp)
#    app.add_url_rule('/', endpoint='index')

    return app
