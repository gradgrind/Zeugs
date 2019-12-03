from flask import Blueprint, render_template, request
from flask import current_app as app

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

import datetime

from wz_core.pupils import Pupils
from wz_text.coversheet import TextReportCovers


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
    p = Pupils(_schoolyear)
    klasses = [k for k in p.classes() if k >= '01' and k < '13']
#TODO: Maybe a validity test for text report classes?
#TODO: dateofissue
    return render_template('text_cover_entry.html',
                           schoolyear=str(_schoolyear),
                           dateofissue='15.07.2020',
                           klasses=klasses) #['01', '01K', '02', '02K', '03', '03K']

"""
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
"""

#TODO: backlink to klasses list (entry page)?
@bp.route('/class/<klass>', methods=['GET','POST'])
#@admin_required
def klassview(klass):
#TODO: dateofissue
    class Form(FlaskForm):
        dateofissue = DateField('Ausgabedatum',
                                default=datetime.date.fromisoformat('2020-07-15'),
                                validators=[InputRequired()])
    form = Form()
    if form.validate_on_submit():
# Use a special template to show the results. From there one can select
# another class, etc.
        return ('<p>Klasse {0}: Das AusgabeDatum ist {1}.</p>'
                '<p>Schüler: {2}</p>').format(
                        klass,
                        form.dateofissue.data,
                        repr(request.form.getlist('Pupil')))
    p = Pupils(_schoolyear)
    pdlist = p.classPupils(klass)
    klasses = [k for k in p.classes() if k >= '01' and k < '13']
    return render_template('text_cover_klass.html', form=form,
                           schoolyear=str(_schoolyear),
                           klass=klass,
                           klasses=klasses,
                           pupils=[(pd['PID'], pd.name()) for pd in pdlist])
#TODO: The form has the date (or should that be in iso format, the
# "translation" being done by the generator?) and the school-year.
# Each pupil is listed with a checkbox (include or not).
# There might be a checkbox/switch for print/pdf, but print might not
# be available on all hosts.
# The submit button could be labelled "Ausführen".
# It might be helpful to a a little javascript to implement a pupil-
# selection toggle (all/none).
# Would it make sense to make the pupil entries in the form links to
# the page for the individual pupil? Then the side panel would be
# superfluous – for pupils. It could be used for klasses.

@bp.route('/pupil/<pid>', methods=['GET','POST'])
#@admin_required
def pupilview(pid):
    return "TODO: Pupil %s" % pid
