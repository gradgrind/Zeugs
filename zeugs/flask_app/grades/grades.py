### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades.py

Last updated:  2020-06-07

Flask Blueprint for grade reports (modular)

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

import io

from .grades_base import bp, _HEADING, _BPNAME
from wz_grades.gradedata import CurrentTerm
from wz_core.courses import CourseTables

from flask import render_template, session, send_file

# "Sub-modules"
from .grades_term import *
from .grades_single import *
from .grades_user import *


@bp.route('/', methods=['GET'])
def index():
    """View: start-page, select function.
    """
    try:
        schoolyear = session['year']
        curterm = CurrentTerm(schoolyear)
    except:
        term0 = None
        nextterm = None
    else:
        term0 = curterm.TERM
        nextterm = curterm.next()
    return render_template(os.path.join(_BPNAME, 'index.html'),
                            heading = _HEADING,
                            term0 = term0,
                            nextterm = nextterm)


#TODO
@bp.route('/index_info', methods=['GET'])
def index_info():
    return "Grade documentation: TODO"
    render_template(os.path.join(_BPNAME, 'index_info.html'),
                                heading = _HEADING)


@bp.route('/teachers', methods=['GET'])
def teachers():
    """Return a tsv-file containing a table:
        CLASS SUBJECT TEACHER E-MAIL
    """
    schoolyear = session['year']
    clist = CourseTables(schoolyear).klass2subject_teachers(text = False)
    lines = []
    for class_, stlist in clist:
        for sid, subject, tdata in stlist:
            item = (class_, subject, tdata['NAME'], tdata['MAIL'])
            lines.append('\t'.join(item))
    tsv = 'KLASSE\tFACH\tLEHRER\tE-MAIL\n' + '\n'.join(lines)
    print(repr(lines), flush=True)
    return send_file(
        io.BytesIO(tsv.encode()),
        attachment_filename='Klasse-Notenlehrer.tsv',
        mimetype='text/tab-separated-values',
        as_attachment=True
    )



#TODO: remove
"""
Snippet, which may be useful in some context?

        f = form.upload.data
        filename = secure_filename(f.filename)
#TODO: the folder (grades) must exist!
        fpath = os.path.join(app.instance_path, 'grades', filename)
        f.save(fpath)

#TODO: testing – read using openpyxl, save as tsv.
        from wz_table.spreadsheet import XLS_spreadsheet, ODS_spreadsheet
        if f.filename.endswith('.xlsx'):
            sheets = XLS_spreadsheet(f).sheets
        elif f.filename.endswith('.ods'):
            sheets = ODS_spreadsheet(f).sheets
        else:
            return "Invalid file: %s" % f.filename
        with open(fpath.rsplit('.', 1)[0] + '.tsv', 'w',
                encoding='utf-8', newline='') as fh:
            for sheet, lines in sheets.items():
                fh.write(':::::: %s\n' % sheet)
                for line in lines:
                    fh.write('\t'.join([item or '' for item in line]) + '\n')

        flash('Loaded %s' % f.filename, 'Info')
        flash('Some more info', 'Warning')
        flash('Bad news', 'Error')
#        return redirect(url_for('bp_grades.term', termn=termn))
"""
