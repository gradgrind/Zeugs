from flask import Blueprint, render_template
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

import datetime

#TODO: school year should be the latest one by default (?), but can be
# stored in the session data to allow access to other years.
_schoolyear = 2020

# Set up Blueprint
bp = Blueprint('bp_text_cover',     # internal name of the Blueprint
        __name__,                   # allows the current package to be found
        template_folder='templates') # package-local templates


@bp.route('/', methods=['GET','POST'])
#@admin_required
def textCover():
    class Form(FlaskForm):
        dateofissue = DateField('Ausgabedatum', #default=datetime.date.today,
                                validators=[InputRequired()])
        itemB = StringField('Anderes Feld', validators=[Length(4, 10,
                "Das Feld muss zwischen 4 und 10 Zeichen enthalten.")])

    from wz_core.pupils import Pupils
    p = Pupils(_schoolyear)
    klasses = [k for k in p.classes() if k >= '01' and k < '13']
#TODO: Maybe a validity test for text report classes?
    form = Form()
    if form.validate_on_submit():
        return 'Das AusgabeDatum ist {}.'.format(form.dateofissue.data)
    return render_template('text_cover_base.html', form=form,
                           schoolyear=str(_schoolyear),
                           klasses=klasses) #['01', '01K', '02', '02K', '03', '03K']

@bp.route('/class/<klass>', methods=['GET','POST'])
#@admin_required
def klassview(klass):
    return "Klasse %s gewählt" % klass
