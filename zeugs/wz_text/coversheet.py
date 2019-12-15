#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_text/coversheet.py

Last updated:  2019-12-15

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
#_NOTEMPLATE         = "Vorlagedatei (Mantelbogen) fehlt für Klasse {klass}:\n  {path} "
_MADEKCOVERS        = "Mantelbögen für Klasse {klass} wurden erstellt"
_MADEPCOVER         = "Mantelbogen für {pupil} wurde erstellt"
_BADPID             = "Schüler {pid} nicht in Klasse {klass}"

import os

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils
from wz_compat.config import (printSchoolYear, klassData,
        getTemplateTags, pupilFields)


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
    classdata = klassData(klass)
    source = classdata.template.render(
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            pupils = plist,
            klass = classdata
        )

    if plist:
        html = HTML (string=source,
                base_url=os.path.dirname (classdata.template.filename))
        pdfBytes = html.write_pdf(font_config=FontConfiguration())
        REPORT.Info(_MADEKCOVERS, klass=klass)
        return pdfBytes
    else:
        REPORT.Fail(_NOPUPILS)


def makeOneSheet(schoolyear, date, klass, pupil):
    """
    <schoolyear>: year in which school-year ends (int)
    <data>: date of issue ('YYYY-MM-DD')
    <klass>: name of the school-class
    <pupil>: An object (e.g. <SimpleNamespace>) with the pupil data as
    attributes (pupil.field = val)
    """
    classdata = klassData(klass)
    source = classdata.template.render(
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            pupils = [pupil],
            klass = classdata
        )
    html = HTML (string=source,
            base_url=os.path.dirname (classdata.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEPCOVER, pupil=pupil.FIRSTNAMES + ' ' + pupil.LASTNAME)
    return pdfBytes



_year = 2016
_date = '2016-06-22'
_klass = '10'
def test_01():
    classdata = klassData(_klass, report_type='text')
    tags = getTemplateTags(classdata.template)
    REPORT.Test("Pupil fields: %s" % repr(pupilFields(tags)))

def test_02():
    pdfBytes = makeSheets (_year, _date, _klass)
    folder = Paths.getUserPath ('DIR_TEXT_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test(" --> %s" % fpath)

def test_03():
    pupils = Pupils(_year)
    plist = pupils.classPupils(_klass)
    from types import SimpleNamespace
    p = plist[0]
    pmap = {f: p[f] for f in p.fields()}
    pdfBytes = makeOneSheet(_year, _date, _klass, SimpleNamespace(**pmap))
    folder = Paths.getUserPath ('DIR_TEXT_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test1.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test(" --> %s" % fpath)
