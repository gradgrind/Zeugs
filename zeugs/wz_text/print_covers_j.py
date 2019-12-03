#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_text/print_covers.py

Last updated:  2019-12-01

Prepare text report cover sheets.

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

import os

import jinja2

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils

#TODO ...

#Messages
_WRITTEN = "Output written to:\n  {path}"

_css = '''
    @font-face {
        font-family: ZeugsFont;
        src: url(fonts/DroidSerif.ttf);
        font-weight: normal;
        font-style: normal;
    }
    @font-face {
        font-family: ZeugsFont;
        font-weight: bold;
        font-style: normal;
        src: url(fonts/DroidSerif-Bold.ttf);
    }

    body {
        font-family: ZeugsFont;
        font-size: 12pt;
        color: #0019E6;
    }
'''

#TODO: at the moment just testing ...
def makeSheets (schoolyear, date, klass, pupils=None):
    """
    <schoolyear>: year in which school-year ends (int)
    <data>: date of issue ('YYYY-MM-DD')
    <klass>: name of the school-class
    <pupils>: a list of <PupilData> instances (must all be in same klass).
        If not supplied, whole klass.
    """
    if not pupils:
        pupils = Pupils(schoolyear).classPupils(klass)
    font_config = FontConfiguration()
    tpdir = Paths.getUserPath ('DIR_TEXT_REPORT_TEMPLATES')
    templateLoader = jinja2.FileSystemLoader(searchpath=tpdir)
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
#TODO: use PATH
    TEMPLATE_FILE = "cover.html"
    template = templateEnv.get_template(TEMPLATE_FILE)
    class _klass:
        final = klass.startswith('12')
        name = klass.lstrip('0')
        klein = klass [-1] == 'K'
    source = template.render(
#TODO: use code (in compat) rather than mark-up to format school year?
            SCHOOLYEAR = Dates.printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            logopath = Paths.getUserPath ('FILE_TEXT_REPORT_LOGO'),
            fontpath = Paths.getUserPath ('FILE_TEXTFONT'),
            pupils = pupils,
            klass = _klass
        )
    html = HTML (string=source)
    css = CSS (string='', font_config=font_config)

    folder = Paths.getUserFolder ('Vorlagen', 'Textzeugnis', 'weasyprint')
    fpath = os.path.join (folder, 'cover.pdf')
    html.write_pdf (fpath, stylesheets=[css])
    REPORT.Info (_WRITTEN, path=fpath)




_year = 2020
_date = '2020-07-15'
def test_01 ():
    from datetime import date
    #_date = date.today ().strftime ("%d.%m.%Y")
    makeSheets (_year, _date, '12')
