#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_text/coversheet.py

Last updated:  2019-12-04

Build the outer sheets (cover sheets) for the text reports.
User fields in template files are replaced by the report information.

=+LICENCE=============================
Copyright 2017-2019 Michael Towers

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

_PUPILSNOTINCLASS   = "Schüler {pids} nicht in Klasse {klass}"
_NOPUPILS           = "Mantelbogen: keine Schüler"
_NOTEMPLATE         = "Vorlagedatei (Mantelbogen) fehlt für Klasse {klass}:\n  {path} "
_MADEKCOVERS        = "Mantelbögen für Klasse {klass} wurden erstellt"
_BADPID             = "Schüler {pid} nicht in Klasse {klass}"

import os, re

import jinja2

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils
from wz_compat.config import printSchoolYear, klassData, textCoverTemplate


def makeSheets (schoolyear, date, klass, pids=None):
    """
    <schoolyear>: year in which school-year ends (int)
    <data>: date of issue ('YYYY-MM-DD')
    <klass>: name of the school-class
    <pids>: a list of pids (must all be in the given klass), only
        generate reports for pupils in this list.
        If not supplied, generate reports for the whole klass.
    """
    pupils = Pupils(schoolyear)
    plist = pupils.classPupils(klass)
    if pids:
        pall = plist
        pset = set (pids)
        plist = []
        for pdata in pall:
            try:
                pset.remove(pdata['PID'])
            except KeyError:
                continue
            plist.append(pdata)
        if pset:
            REPORT.Bug(_PUPILSNOTINCLASS, pids=', '.join(pset), klass=klass)
    font_config = FontConfiguration()
    tpdir = Paths.getUserPath('DIR_TEXT_REPORT_TEMPLATES')
    templateLoader = jinja2.FileSystemLoader(searchpath=tpdir)
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
    tpfile = '???'
    try:
        tpfile = textCoverTemplate(klass)
        template = templateEnv.get_template(tpfile)
    except:
        REPORT.Fail(_NOTEMPLATE, klass=klass, path=os.path.join(tpdir, tpfile))
    source = template.render(
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            logopath = Paths.getUserPath('FILE_TEXT_REPORT_LOGO'),
            fontdir = Paths.getUserPath('DIR_FONTS'),
            pupils = plist,
            klass = klassData(klass)
        )

    if plist:
        html = HTML (string=source)
        pdfBytes = html.write_pdf(font_config=font_config)
        REPORT.Info(_MADEKCOVERS, klass=klass)
        return pdfBytes
    else:
        REPORT.Fail(_NOPUPILS)



def pupilFields(klass):
    """Return a list of the pupil data fields needed for a cover sheet.
    The items are returned as pairs: (internal tag, display name).
    """
    tpdir = Paths.getUserPath('DIR_TEXT_REPORT_TEMPLATES')
    tpfile = textCoverTemplate(klass)
    path=os.path.join(tpdir, tpfile)
    with open(path, 'r', encoding='utf-8') as fh:
        text = fh.read()
    tags = re.findall(r'pupil\.(\w+)', text)
    name = CONF.TABLES.PUPILS_FIELDNAMES
    return [(tag, name[tag]) for tag in tags]



#TODO
def makeOneSheet(schoolyear, date, klass, pupil):
    """
    <schoolyear>: year in which school-year ends (int)
    <data>: date of issue ('YYYY-MM-DD')
    <klass>: name of the school-class
    <pupil>: A <SimpleNamespace> with the pupil data (pupil.field = val)
    """




    font_config = FontConfiguration()
    tpdir = Paths.getUserPath('DIR_TEXT_REPORT_TEMPLATES')
    templateLoader = jinja2.FileSystemLoader(searchpath=tpdir)
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
    template = templateEnv.get_template(textCoverTemplate(klass))
    source = template.render(
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            logopath = Paths.getUserPath('FILE_TEXT_REPORT_LOGO'),
            fontdir = Paths.getUserPath('DIR_FONTS'),
            pupils = plist,
            klass = klassData(klass)
        )

    if plist:
        html = HTML (string=source)
        pdfBytes = html.write_pdf(font_config=font_config)
        REPORT.Info(_MADEKCOVERS, klass=klass)
        return pdfBytes
    else:
        REPORT.Fail(_NOPUPILS)




_year = 2020
_date = '2020-07-15'
def test_01 ():
    pdfBytes = makeSheets (_year, _date, '11K')
    folder = Paths.getUserPath ('DIR_TEXT_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
