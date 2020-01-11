### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/settings/settings.py

Last updated:  2020-01-11

Flask Blueprint for application settings.

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

from flask import (Blueprint, render_template, request, session,
        send_file, url_for, flash, abort)
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField
#from wtforms.fields.html5 import DateField
#from wtforms.validators import InputRequired, Length

import os
#from types import SimpleNamespace

from wz_core.configuration import Paths
#from wz_core.db import DB
#from wz_core.pupils import Pupils, match_klass_stream
#from wz_compat.config import sortingName
#from wz_compat.template import getTemplate, getTemplateTags, pupilFields
#from wz_text.coversheet import makeSheets, makeOneSheet

_HEADING = "Einstellungen"

# Set up Blueprint
_BPNAME = 'bp_settings'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


@bp.route('/', methods=['GET','POST'])
#@admin_required
def index():
    class YearForm(FlaskForm):
        YEAR = SelectField("Schuljahr", coerce=int)

    schoolyear = session['year']
    form = YearForm()
    form.YEAR.choices = [(y, y) for y in Paths.getYears()]
    if form.validate_on_submit():
        # POST
        y = form.YEAR.data
        if y != schoolyear:
            schoolyear = y
            session['year'] = y

    # GET
    form.YEAR.default = schoolyear
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            form=form,
                            heading=_HEADING)


@bp.route('/newyear', methods=['GET','POST'])
#@admin_required
def newyear():
    return "'newyear' not yet implemented"
