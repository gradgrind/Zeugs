### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_grades/maketables.py

Last updated:  2020-04-17

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
_WRONG_CLASS = "{pname} hat die Klasse gewechselt"
_WRONG_GROUP = "{pname} hat die Gruppe gewechselt"
_NO_GRADES = "Keine Noten für {pname}"
_NOPUPILS = "Ergebnistabelle: keine Schüler"


import os, datetime

from weasyprint import HTML
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths
from wz_core.pupils import Pupils, Klass
from wz_core.template import openTemplate
from wz_compat.config import printSchoolYear
from wz_grades.gradedata import GradeReportData, GradeData


def trimName(name):
    """Truncate excessively long (subject) names.
    """
    return name[:21] + '...' if len(name) > 25 else name


def makeTable(schoolyear, term, ggroup):
    """Build a result table for the given year, term and grade group.
    <ggroup> is a <Klass> instance.
    """
    pupils = Pupils(schoolyear)
    # <GradeReportData> manages the report template, etc.:
    reportData = GradeReportData(schoolyear, ggroup)
    plist = []
    for pdata in pupils.classPupils(ggroup):
        # Get grade map for pupil
        gradedata = GradeData(schoolyear, term, pdata)
        # Check for mismatches with pupil and term info
        if not gradedata.KEYTAG:
            REPORT.Warn(_NO_GRADES, pname = pdata.name())
            continue
        if gradedata.gclass != ggroup.klass:
            REPORT.Warn(_WRONG_CLASS, pname = pdata.name())
            continue
        gstream = gradedata.gstream
        if gstream != pdata['STREAM']:
            REPORT.Warn(_WRONG_GROUP, pname = pdata.name())
            if ggroup.containsStream(gstream):
                pdata['STREAM'] = gstream
            else:
                continue
        # Add the grades, etc., to the pupil data
        gmanager = gradedata.getAllGrades()


#        REPORT.Test("??? %s: %s" % (pdata.name(), repr(gmanagerp)))
        gmanager.addDerivedEntries()    # add "composite" subjects
        # Handle "extra" fields
        for x in reportData.xfields:
            if x[0] == '*':
                x = x[1:]
            try:
                method = getattr(gmanager, 'X_' + x)
            except:
                REPORT.Bug("No xfield-handler for %s" % x)
            method(pdata)
#        REPORT.Test("\n  XINFO: %s" % repr(gmanager.XINFO))
        pdata.grades = gmanager
        plist.append(pdata)

#Test with more lines:
#    plist = plist + plist + plist + plist

    # Calculate width of table
    sizes = {
            'marginwidth': 28,  # pt
            'borderwidth': 0.1, # em
            'spacerwidth': 0.5, # em
            'namewidth': 10,    # em
            'cellwidth': 2.4,   # em
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

    xnames = CONF.GRADES.ORDERING
    if reportData.xfields:
        slist.append((None, None, None))
        width += spacerw
        for x in reportData.xfields:
            if x[0] == '*':
                x = x[1:]
            slist.append((x, trimName(xnames['X_' + x]), 'extra'))
            width += cellw

    # Scaling (via table font) based on estimated width
    pagewidthL = 842 - 2*sizes['marginwidth']   # landscape
    pagewidthP = 595 - 2*sizes['marginwidth']   # portrait
    BODGE = 0.95    # this factor is an experimental value
    fontsize = pagewidthP / width * BODGE
    if fontsize < 10:
        # Use "landscape"
        fontsize = pagewidthL / width * BODGE
        sizes['orientation'] = 'landscape'
    else:
        sizes['orientation'] = 'portrait'
    if fontsize > 12:
        fontsize = '12'
    else:
        fontsize = str(fontsize)[:5]
    sizes['fontsize'] = fontsize
#    REPORT.Test("$ SIZES: %s" % sizes)

    # Get table template
    template = openTemplate('GRADES/GRADETABLE.html')
    now = datetime.datetime.now()
    ### Generate html for the table
    source = template.render(
            SCHOOLYEAR = printSchoolYear(schoolyear),
            term = term,
            date = now.isoformat(timespec = 'minutes', sep = ' '),
            subjects = slist,
            pupils = plist,
            klass = ggroup,
            sizes = sizes
        )

#    Source as html string
#    fpath = os.path.join(Paths.getYearPath(schoolyear), 'tmp', 'GRADES.html')
#    with open(fpath, 'w', encoding='utf-8') as fh:
#        fh.write(source)

    # Convert to pdf
    if not plist:
        REPORT.Fail(_NOPUPILS)
    html = HTML(string=source,
            base_url=os.path.dirname(template.filename))
    pdfBytes = html.write_pdf(font_config = FontConfiguration())
    return pdfBytes



##################### Test functions
_year = 2016

def test_01():
    _term = '1'
    for _ks0 in '11.RS-HS-_', '11.Gym', '12.RS-HS-_', '12.Gym', '13':
        _ks = Klass(_ks0)
        pdfBytes = makeTable(_year, _term, _ks)
        fpath = Paths.getYearPath(_year, 'FILE_GRADE_RESULTS',
                make = -1, term = _term).replace('*', '%s_%s' % (
                        _term, _ks0.replace('.', '-'))) + '.pdf'
        with open(fpath, 'wb') as fh:
            fh.write(pdfBytes)
        REPORT.Info("Generated result table for %s" % _ks0)


def test_02():
    _term = '2'
    for _ks0 in '10', '11.Gym', '11.RS-HS-_', '12.RS-HS-_', '12.Gym', '13':
        _ks = Klass(_ks0)
        pdfBytes = makeTable(_year, _term, _ks)
        fpath = Paths.getYearPath(_year, 'FILE_GRADE_RESULTS',
                make = -1, term = _term).replace('*', '%s_%s' % (
                        _term, _ks0.replace('.', '-'))) + '.pdf'
        with open(fpath, 'wb') as fh:
            fh.write(pdfBytes)
        REPORT.Info("Generated result table for %s" % _ks0)
