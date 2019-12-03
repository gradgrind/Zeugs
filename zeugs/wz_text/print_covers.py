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

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths
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
def makeSheets (schoolyear, manager, date):
    folder = Paths.getUserFolder ('Vorlagen', 'Textzeugnis', 'weasyprint')
    font_config = FontConfiguration()
#    pages = []
#    for p in 1,2,3:
#        pages.append (_TEXT)
#    html = HTML (string="\n\n".join (pages))
    html = HTML (os.path.join (folder, 'cover1.html'))
#    css = CSS (string=_css.replace ('{fontpath}', os.path.join (folder, 'fonts')),
#            font_config=font_config)
    css = CSS (string='', font_config=font_config)

#    fpath = Paths.getYearPath (schoolyear, 'FILE_CLASS_REPORT_LISTS')
#    fpath = "Test.pdf"
#    html.write_pdf (fpath, stylesheets=[CSS (string=_css.replace ('{{year}}',
#            str (schoolyear)))])
    fpath = os.path.join (folder, 'cover1.pdf')
    html.write_pdf (fpath, stylesheets=[css])
    REPORT.Info (_WRITTEN, path=fpath)



_year = 2020
_manager = "Michael Towers"
def test_01 ():
    from datetime import date
    _date = date.today ().strftime ("%d.%m.%Y")
    makeSheets (_year, _manager, _date)
