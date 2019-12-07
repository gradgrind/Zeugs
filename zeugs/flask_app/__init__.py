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

from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, ZEUGS_DATA, instance_relative_config=True)
#    app.config.from_mapping(
#        SECRET_KEY=os.urandom(24),
#        DATABASE=os.path.join(app.instance_path, 'flask.sqlite'),
#    )

    app.config.from_object('flask_config') # Load module config.py (this directory).
    if test_config is None:
        # Load the config from the instance directory, if it exists, when not testing
        # Might be better to get secret key from environment?
        # Are there any other differences to development mode?
#        app.config.from_pyfile('config.py', silent=True)
        app.config.from_pyfile('config.py',
                silent=(app.config['ENV']=='development'))
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

#    for k,v in app.config.items():
#        print ("§§§ %s:" % k, v)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register csrf protection
    csrf.init_app(app)


    @app.route('/', methods=['GET','POST'])
    def index(): ### Just test code at the moment ...
        from flask import render_template_string
        from wtforms import SelectMultipleField, SubmitField
        from wtforms.widgets import ListWidget, CheckboxInput
        class MultiCheckboxField(SelectMultipleField):
            widget = ListWidget(prefix_label=False)
            option_widget = CheckboxInput()
            def iter_choices(self):
                """Overridden method to force all boxes to 'checked'.
                """
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


    from .text_cover import text_cover
    app.register_blueprint(text_cover.bp, url_prefix='/text_cover')

#    from . import db
#    db.init_app(app)

    from .auth import auth
    app.register_blueprint(auth.bp, url_prefix='/auth')

#    from . import blog
#    app.register_blueprint(blog.bp)
#    app.add_url_rule('/', endpoint='index')

    return app
