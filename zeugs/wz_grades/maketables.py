### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/maketables.py

Last updated:  2020-04-05

Build result tables for the grade groups, including evaluation, etc.

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

## Messages
_MADEKTABLE = "Ergebnistabelle für {ks} erstellt"
_WRONG_CLASS = "{pname} hat die Klasse gewechselt"
_WRONG_GROUP = "{pname} hat die Gruppe gewechselt"
_NO_GRADES = "Keine Noten für {pname}"
_NOPUPILS = "Ergebnistabelle: keine Schüler"


import os

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils, Klass
from wz_core.db import DB
from wz_compat.config import printSchoolYear
from wz_compat.template import openTemplate
from wz_grades.gradedata import GradeReportData, getGradeData


def trimName(name):
    """Truncate excessively long (subject) names.
    """
    return name[:16] + '...' if len(name) > 20 else name


def makeTable(schoolyear, term, ggroup):
    """Build a result table for the given year, term and grade group.
    <ggroup> is a <Klass> instance.
    """
    pupils = Pupils(schoolyear)
    # <GradeReportData> manages the report template, etc.:
    reportData = GradeReportData(schoolyear, ggroup)
    plist = []
    db = DB(schoolyear)
    for pdata in pupils.classPupils(ggroup):
        pid = pdata['PID']
        # Get grade map for pupil
        gradedata = getGradeData(schoolyear, pid, term)
        # Check for mismatches with pupil and term info
        gmap = None
        if gradedata:
            if gradedata['CLASS'] != ggroup.klass:
                REPORT.Warn(_WRONG_CLASS, pname = pdata.name())
                continue
            gstream = gradedata['STREAM']
            if gstream != pdata['STREAM']:
                REPORT.Warn(_WRONG_GROUP, pname = pdata.name())
                if ggroup.containsStream(gstream):
                    pdata['STREAM'] = gstream
                else:
                    continue
            # Add the grades, etc., to the pupil data
            gmap = gradedata['GRADES']

        if not gmap:
            REPORT.Warn(_NO_GRADES, pname = pdata.name())
            continue

#        REPORT.Test("??? %s: %s" % (pdata.name(), repr(gmap)))
        gmanager = reportData.gradeManager(gmap)
        gmanager.addDerivedEntries()    # add "composite" subjects
        # Handle "extra" fields
        for x in reportData.xfields:
            if x[0] == '*':
                continue
            try:
                method = getattr(gmanager, 'X_' + x)
            except:
                REPORT.Bug("No xfield-handler for %s" % x)
            method(pdata)
#        REPORT.Test("\n  XINFO: %s" % repr(gmanager.XINFO))
        pdata.grades = gmanager
        plist.append(pdata)

    # Calculate width of table
    sizes = {
#            'fontsize': 12,     # pt
            'borderwidth': 0.1, # em
            'spacerwidth': 0.5, # em
            'namewidth': 10,    # em
            'cellwidth': 2.4,   # em
            'scale': 80         # %
    }
    cellw = sizes['cellwidth'] + sizes['borderwidth']
    spacerw = sizes['spacerwidth'] + sizes['borderwidth']
    width = sizes['namewidth'] + sizes['borderwidth']*2 + cellw

    slist = []
    components = reportData.sid2tlist.component
    for g, sids in reportData.sgroup2sids.items():
        if sids:
            slist.append((None, None, None))
            width += spacerw
            for sid in sids:
                # Filter out columns with all '/'
                for pdata in plist:
                    if pdata.grades[sid] != '/':
                        break
                else:
                    continue
                tlist = reportData.sid2tlist[sid]
                sname = tlist.subject
                ckey = tlist.COMPOSITE
                ckcss = None
                # It should (!) be impossible for a subject to be both
                # composite and component.
                if ckey:
                    ckcss = 'composite_' + ckey
                else:
                    ckey = components[sid]
                    if ckey:
                        ckcss = 'component_' + ckey
                slist.append((sid, trimName(sname), ckcss))
                width += cellw

    xnames = reportData.XNAMES()
    if reportData.xfields:
        slist.append((None, None, None))
        width += spacerw
    for x in reportData.xfields:
        if x[0] == '*':
            x = x[1:]
        slist.append((x, trimName(xnames[x]), 'extra'))
        width += cellw

    # Scaling (via table font) based on estimated width?
    pagewidth = 842 - 2*28.35 # landscape - margins (height = 595)
    # BODGE: the factor 0.95 is an experimental value
    sizes['fontsize'] = str(pagewidth / width * 0.95)[:5]
    REPORT.Test("$ SIZES: %s" % sizes)

    # Get table template
    template = openTemplate('GRADES/GRADETABLE.html')
    ### Generate html for the table
    source = template.render(
            SCHOOLYEAR = printSchoolYear(schoolyear),
            term = term,
#time with hms?
            date = Dates.today(iso = False),
            subjects = slist,
            pupils = plist,
            klass = ggroup,
            sizes = sizes
        )

#    Return source as html string
#    fpath = os.path.join(Paths.getYearPath(schoolyear), 'tmp', 'GRADES.html')
#    with open(fpath, 'w', encoding='utf-8') as fh:
#        fh.write(source)

    # Convert to pdf
    if not plist:
        REPORT.Fail(_NOPUPILS)
    html = HTML(string=source,
            base_url=os.path.dirname(template.filename))
    pdfBytes = html.write_pdf(font_config = FontConfiguration())
    REPORT.Info(_MADEKTABLE, ks = ggroup)
    return pdfBytes



##################### Test functions
_year = 2016
_term = '2'
def test_01():
    _ks = Klass('11.Gym')
    pdfBytes = makeTable(_year, _term, _ks)
    fpath = Paths.getYearPath(_year, 'FILE_GRADE_RESULTS',
            make = -1, term = _term).replace('*', '%s_%s' % (
                    _term, str(_ks).replace('.', '-'))) + '.pdf'
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_02():
    return
    _term = '2'
    for _ks0 in '11', '12.RS-HS-_', '12.Gym':
        _ks = Klass(_ks0)
        pdfBytes = makeTable(_year, _term, _ks)
        folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
        fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_ks, _term))
        with open(fpath, 'wb') as fh:
            fh.write(pdfBytes)
