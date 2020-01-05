# python >= 3.7
# -*- coding: utf-8 -*-

#TODO ...

"""
wz_grades/makereports.py

Last updated:  2020-01-05

Generate the grade reports for a given class/stream.
Fields in template files are replaced by the report information.

In the templates there are grouped and numbered slots for subject names
and the corresponding grades.

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

#TODO: Maybe also "Sozialverhalten" und "Arbeitsverhalten"
#TODO: Praktika? e.g.
#       Vermessungspraktikum:   10 Tage
#       Sozialpraktikum:        3 Wochen
#TODO: Maybe component courses (& eurythmy?) merely as "teilgenommen"?


## Messages
_PUPILS_NOT_IN_CLASS_STREAM = "Schüler {pids} nicht in Klasse/Gruppe {ks}"
#_NOTEMPLATE = "Vorlagedatei (Notenzeugnis) fehlt für Klasse {ks}:\n  {path}"
_MADEKREPORTS = "Notenzeugnisse für Klasse {ks} wurden erstellt"
_NOPUPILS = "Notenzeugnisse: keine Schüler"
_MADEPREPORT = "Notenzeugnis für {pupil} wurde erstellt"


import os
#from types import SimpleNamespace

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths, Dates
from wz_core.pupils import Pupils, KlassData, match_klass_stream
from wz_compat.config import printSchoolYear, printStream
from wz_grades.gradedata import GradeReportData, db2grades


def makeReports(schoolyear, term, klass_stream, date, pids=None):
    """Build a single file containing reports for the given pupils.
    This only works for groups with the same report type and template.
    <term> is the term, used also as report category.
    <date> is the date of issue ('YYYY-MM-DD').
    <pids>: a list of pids (must all be in the given klass), only
        generate reports for pupils in this list.
        If not supplied, generate reports for the whole klass/group.
    """
    # <db2grades> returns a list: [(pid, pname, grade map), ...]
    # <grades>: {pid -> (pname, grade map)}
    grades = {pid: (pname, gmap)
            for pid, pname, gmap in db2grades(schoolyear, term, klass_stream)
    }
    pupils = Pupils(schoolyear)
    pall = pupils.classPupils(klass_stream) # list of data for all pupils
    # If a pupil list is supplied, select the required pupil data.
    # Otherwise use the full list.
    if pids:
        pset = set (pids)
        plist = []
        for pdata in pall:
            try:
                pset.remove(pdata['PID'])
            except KeyError:
                continue
            plist.append(pdata)
        if pset:
            REPORT.Bug(_PUPILS_NOT_IN_CLASS_STREAM, pids=', '.join(pset),
                    ks=klass_stream)
    else:
        plist = pall

    ### Get a tag mapping for the grade data of each pupil
    # Get the name of the relevant configuration file in folder GRADES:
    grademap = match_klass_stream(klass_stream, CONF.MISC.GRADE_SCALE)
    # <GradeReportData> manages the report template, etc.:
    reportData = GradeReportData(schoolyear, term, klass_stream)
    # General info on the klass/stream:
    klassData = KlassData(klass_stream)
    pmaplist = []
    for pdata in plist:
        # The pupil data needs to be a "proper" mapping, not a list,
        # which is the default:
        pmap = pdata.toMapping()
        pname, gmap = grades[pmap['PID']]   # get pupil name and grade map
        # Build a grade mapping for the tags of the template:
        pmap.grades = reportData.getTagmap(gmap, pname, grademap)
        pmaplist.append(pmap)

    ### Generate html for the reports
# Testing:
#    n = 0  # with change below, just generate nth of list
#    print("§§§", pmaplist[n])
    source = reportData.template.render(
            report_type = reportData.report_type,
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = pmaplist,
#            pupils = [pmaplist[n]],
            klass = klassData
        )
    # Convert to pdf
    if plist:
        html = HTML(string=source,
                base_url=os.path.dirname(reportData.template.filename))
        pdfBytes = html.write_pdf(font_config=FontConfiguration())
        REPORT.Info(_MADEKREPORTS, ks=klass_stream)
        return pdfBytes
    else:
        REPORT.Fail(_NOPUPILS)


#TODO ...
def makeOneSheet(schoolyear, date, klass_stream, report_type, pupil):
    """
    <schoolyear>: year in which school-year ends (int)
    <data>: date of issue ('YYYY-MM-DD')
    <klass_stream>: name of the school-class and stream ("klass.stream")
    <report_type>: name-tag for the type of report to be produced
        (see <GRADE_TEMPLATES> in wz_compat/config.py)
    <pupil>: A <SimpleNamespace> with the pupil data (pupil.field = val)
    """
#TODO: abschluss -> corresponding sid (_Q12?)
    pupil.grades = SimpleNamespace(abschluss='RS')

    classdata = klassData(klass_stream, report_type)
    source = classdata.template.render(
            SCHOOLYEAR = printSchoolYear(schoolyear),
            DATE_D = date,
            todate = Dates.dateConv,
            STREAM = printStream,
            pupils = [pupil],
            klass = classdata
        )
    html = HTML (string=source,
            base_url=os.path.dirname (classdata.template.filename))
    pdfBytes = html.write_pdf(font_config=FontConfiguration())
    REPORT.Info(_MADEPREPORT, pupil=pupil.FIRSTNAMES + ' ' + pupil.LASTNAME)
    return pdfBytes



##################### Test functions
_year = 2016
_date = '2016-01-29'
_term = '1'
def test_01():
    from wz_compat.template import openTemplate, getTemplateTags, pupilFields
    from glob import glob
    fbase = Paths.getUserPath('DIR_TEMPLATES')
    fx = 'Notenzeugnis/*.html'
    fmask = os.path.join(fbase, *fx.split('/'))
    for f in glob(fmask):
        fname = os.path.basename(f)
        fpath = fx.rsplit('/', 1)[0] + '/' + os.path.basename(f)
        REPORT.Test("TEMPLATE: %s" % fpath)
        t = openTemplate(fpath)
        tags = getTemplateTags(t)
        REPORT.Test("Pupil fields: %s" % repr(pupilFields(tags)))

def test_02():
    _klass_stream = '13'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_03():
    _klass_stream = '12.RS'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_04():
    _klass_stream = '12.Gym'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)

def test_05():
    _klass_stream = '11'
    pdfBytes = makeReports (_year, _term, _klass_stream, _date)
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test_%s_%s.pdf' % (_klass_stream, _date))
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)


def test_06():
    return

    pupils = Pupils(_year)
    plist = pupils.classPupils(_klass_stream)
    from types import SimpleNamespace
    p = plist[0]
    pmap = {f: p[f] for f in p.fields()}
    pdfBytes = makeOneSheet(_year, _date, _klass_stream, 'Abgang',
            SimpleNamespace(**pmap))
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test1.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test(" --> %s" % fpath)

def test_06():
    return

    _klass_stream = '12.RS'
    pupils = Pupils(_year)
    plist = pupils.classPupils(_klass_stream)
    from types import SimpleNamespace
    p = plist[0]
    pmap = {f: p[f] for f in p.fields()}
    pdfBytes = makeOneSheet(_year, _date, _klass_stream, 'Abschluss',
            SimpleNamespace(**pmap))
    folder = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
    fpath = os.path.join (folder, 'test2.pdf')
    with open(fpath, 'wb') as fh:
        fh.write(pdfBytes)
    REPORT.Test(" --> %s" % fpath)



'''
import os, copy
from glob import glob
from collections import OrderedDict

from .gradeinfo import GradeInfo
from wz_core.courses import CALC, EXTRA
from wz_core.configuration import Paths, Dates, printClass
from wz_textdoc.simpleodt import OdtUserFields
from wz_io.support import toPdf

_PUPIL = "Schüler-Id {pid}"



class GradeReports:
    def __init__ (self, schoolyear, date):
        """Handle generation of grade reports.
        Set up a class instance for this year and date.
        """
        self.schoolyear = schoolyear
        self.date = date

        self.pupils = Pupils (schoolyear)
        self.courses = CourseTables (schoolyear)

        # Get the subject info
        self.gradeInfo = GradeInfo ()
        self.gradeInfo.setDate (schoolyear, date)





    def makeReports (self, reportType, klass_stream, pids=None,
# xfields???
            xfields=None,
            null=False):
        """Build grade reports for the given class and stream.
        If <pids> is specified, it must be a list. Reports will be
        generated only for pupils in this list (who must be in the
        specified class & stream).
        <reportType> should be the name of a file in config folder
        GRADES/REPORT_TYPES.
        If <null> is true, the grade slots in the output document are
        left empty.
#?
        Return a list of the successfully generated files (just the names).
        """
#klass?

#TODO: need the class subjects and those for the pupil
        sid2info = self.courses.filterGrades (klass, realonly)
        subjects = []
        for sid, sinfo in sid2info.items ():
            subjects.append ((sid, sinfo.COURSE_NAME))
        teacherMatrix = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_SUBJECTS', klass)

        grades = FormattedMatrix.readMatrix (self.schoolyear,
                'FILE_CLASS_GRADES', klass)
#TODO: need composite grades, qualifications, etc.


        i = 0
        for pdata in self.pupils.classPupils (klass, self.date):
            i += 1
            pid = pdata ['PID']
            if pids and pid not in pids:
                continue




            if null:
                pgrades = None
            else:
                try:
                    pgrades = grades [pid]
                except:
                    REPORT.Error (_NOGRADES, klass=klass,
                            pname = pdata.name ())
                    pgrades = None

            self._makeReport (i, pid, pdata, pgrades)





        self._null = null
        self.gradeInfo.setClassStream (klass_stream)

        # Get grade groups and subject names for the relevant subjects
        self.sInfo = OrderedDict ()
        for sid in self.gradeInfo.groupInfo ['_SIDS'].split ('&'):
            cdata = self.gradeInfo.courseData [sid]
            self.sInfo [sid] = (cdata.name, cdata.ggroup, cdata.gtype)

        # Number pids for the current class.stream
        # Make mappings for grades and ggroups for each pupil
        pidmap = OrderedDict ()
        i = 0
        for pid, smap in self.gradeInfo.pids.items ():
            i += 1
            sid_grade = {}
            for sid, fields in smap.items ():
                try:
                    grade = fields ['ENTRY']
                except:
                    continue
                sid_grade [sid] = grade

            pidmap [pid] = (i, sid_grade)
        if len (pidmap) == 0:
            return []

        if pids:
            # Only handle the pids in this list.
            _pids = set (pidmap)
            for p in pids:
                try:
                    _pids.remove (p)
                except:
                    REPORT.Bug (_PUPILNOTINCLASSSTREAM, pid=p,
                            ks=klass_stream)
                    assert False
            for p in _pids:
                del (pidmap [p])

        ## Gather info which is particular to the class & stream
        self._klass, stream = klass_stream.split ('.')
        _year = printClass (self._klass, yearOnly=True)
        self._typeInfo = {
                'CLASS_YEAR': _year,
                'CLASS_FULL': printClass (self._klass),
                'STREAM': CONFIG.STREAMS [stream].string ()
            }

        ## Get info for report type
        tpmap = {}      # template files
        self._xinfo = {}
        reportInfo = CONFIG.GRADES.REPORT_TYPES [reportType]
        for k in reportInfo:
            _k0 = k [0]
            if _k0 == '_':
                # Info for "extra" columns
                xitems = []
                for kx in reportInfo [k]:
                    ks = kx.split ('-')
                    if len (ks) == 2:
                        ks.append (ks [1])
                    elif len (ks) != 3:
                        REPORT.Fail (_INVALIDRTYPEXTRA, field=k, val=kx,
                                rtype=self._reportType)
                        assert False
                    xitems.append (ks)
                self._xinfo [k] = xitems
            elif _k0 == '*':
                # Report template info
                tpmap [k [1:]] = reportInfo [k].string ()
            else:
                self._typeInfo [k] = reportInfo [k].string ()
# xfields???
        if xfields:
            self._typeInfo.update (xfields)

        ## Year-related date info
        self._typeInfo ['SCHOOLYEAR'] = Dates.printSchoolYear (self.schoolyear)
        self._typeInfo ['DATE_D'] = self.date   # Date of issue
        calendar = Dates.getCalendar (self.schoolyear)
        self._typeInfo ['START_D'] = calendar.START.string ()
        self._typeInfo ['END_D'] = calendar.END.string ()

        ## Get grade scale info
#        groupInfo = self.gradeData.groups [klass] [stream]
        self._gradeSet = self.gradeInfo.gradeScale (klass_stream)
        # Mapping: {grade -> text}
        self._gradeMap = CONFIG.GRADES [self._gradeSet]

        ## Group info which may be needed in the report form
        for k, v in self.gradeInfo.getInfo (self.schoolyear,
                self.date) [klass_stream].items ():
            if k [0] != '_':
                self._typeInfo [k] = v

        ## Get template path
        tpdir = Paths.getUserPath ('DIR_GRADE_REPORT_TEMPLATES')
        _yearstream = _year + '-' + stream
        try:
            if _yearstream in tpmap:
                tpfile = tpmap [_yearstream]
            elif _year in tpmap:
                tpfile = tpmap [_year]
            else:
                tpfile = tpmap ['']
        except:
            REPORT.Fail (_NOTEMPLATE, rtype=reportType,
                    klass=self._klass, stream=stream)
            assert False
        self._tppath = os.path.join (tpdir, tpfile)
#        print ("\nTEMPLATE:", tppath)
        self._fieldnames = OdtUserFields.listUserFields (self._tppath)
        # Which zgroups should not cause error messages:
        try:
            self._xSuppress = self._fieldnames ['X_SUPPRESS'].split ('_')
        except:
            self._xSuppress = []

        self._ufgroups = {}
        for fname in self._fieldnames:
#            print ("§§§", fname)
            # Seek user fields having the form 'g_ABC_n', where 'ABC' is one or
            # more zgroup letters and 'n' is an integer.
            fnsplit = fname.split ('_')
            if len (fnsplit) != 3:
                continue
            if fnsplit [0] == 'g':
                # Check that there is a matching 'f_ABC_n' user field.
                # It is, however, not compulsory.
                sfield = '_'.join (['f'] + fnsplit[1:])
                if sfield not in self._fieldnames:
                    REPORT.Warn (_NOMATCHINGSUBJECTFIELD,
                            filepath=self._tppath, field=sfield)
            elif fnsplit [0] == 'f':
                # Check that there is a matching 'g_ABC_n' user field.
                # It is, however, not compulsory.
                sfield = '_'.join (['g'] + fnsplit[1:])
                if sfield not in self._fieldnames:
                    REPORT.Warn (_NOMATCHINGGRADEFIELD,
                            filepath=self._tppath, field=sfield)
            else:
                continue
            ztag = fnsplit [1]
            try:
                itag = int (fnsplit [2])
            except:
                REPORT.Error (_INVALIDGRADEFIELDINDEX, filepath=tmpath,
                        field=fname)
                continue
            if ztag in self._ufgroups:
                self._ufgroups [ztag].append (itag)
            else:
                self._ufgroups [ztag] = [itag]
        # Sort each integer list in reverse order, to assist 'popping'.
        for ilist in self._ufgroups.values ():
            # In-place sort
            ilist.sort (reverse=True)
        self._ufglist = sorted (self._ufgroups)
#        print ('\n------------------------')
#        print ("\n++ufglist", self._ufglist)
#        print ("\n++ufgroups", self._ufgroups)
#        print ('\n------------------------\n')

        if _pathoverride != None:
            self._outdir = _pathoverride
        else:
            self._outdir = Paths.getYearPath (self.schoolyear,
                    'DIR_GRADE_REPORTS',
                    date=self.date, klass=self._klass, make=1)

        files = []
        for pid, pmap in pidmap.items ():
            f = self._makeReport (pid, *pmap)
            if f != None:
                files.append (f)

        if files:
            toPdf (self._outdir, *files)
            pdf_files = [f.rsplit ('.', 1) [0] + '.pdf' for f in files]
            REPORT.Info (_MADENREPORTS, n=len (files), folder=self._outdir)
        return files



    def _makeReport (self, pid, pupilNumber, sid_grade):
        """Build a grade report for the given pupil, <pid>.
        <pupilNumber> is the pupil's index within the class.
        <sid_grade> maps sid -> grade.
        """
        NOENTRY = CONFIG.FORMATTING.NOENTRY.string ()
        NOTCHOSEN = CONFIG.FORMATTING.NOTCHOSEN.string ()
        EMPTYITEM = CONFIG.FORMATTING.EMPTY.string ()
        BADGRADE = CONFIG.FORMATTING.BADGRADE.string ()



        pid = pdata ['PID']
        FIELDS = {f: pdata [f] for f in pdata.fields ()}





        ## Fetch the information from the class/pupil table
        FIELDS = dict (self.gradeInfo.classData [pid])

        ## Handle the grades
        grades = OrderedDict ()
        try:
            onlyChosen = self._fieldnames ['X_onlyChosen'].upper () in (
                    '1', 'TRUE', 'YES')
#            print ("§§§", onlyChosen)
        except:
            onlyChosen = False

        # Go through all sids relevant to the group
        ssid_info = {}    # ssid -> (name, ggroup, gtype)
        for sid, sinfo in self.sInfo.items ():
            ggroup, gtype = sinfo [1:]
            ssid = sid.split ('.') [0]
            try:
                g = sid_grade [sid]
#                print ("???", pid, sid, g, self.gGroups [sid])
            except:
                if onlyChosen or ssid in grades:
                    continue
                grades [ssid] = NOTCHOSEN    # not chosen
                ssid_info [ssid] = sinfo
                continue
            ssid_info [ssid] = sinfo
            if self._null:
                grades [ssid] = EMPTYITEM
                continue
            if gtype in (CALC, EXTRA):
                grades [ssid] = g or ''
                continue
            if not g:
                REPORT.Error (_MISSINGGRADEENTRY,
                        klass=self._klass, pid=pid, cid=sid)
                grades [ssid] = BADGRADE
                continue
            else:
                try:
                    if grades [ssid] != NOTCHOSEN:
                        REPORT.Bug ("Class {klass}, pupil {pid}:"
                                " Two grades in subject {ssid}",
                                klass=self._klass, pid=pid, ssid=ssid)
                        assert False
                except:
                    pass
                try:
                    grades [ssid] = self._gradeMap [g] [0]
                except:
                    REPORT.Error (_NOGRADEMAPPING,
                            klass=self._klass, pid=pid, grade=g)
                    grades [ssid] = BADGRADE

        # Look for slots for explicit subjects ('G_' prefix)
        for f in self._fieldnames:
            if f.startswith ('G_'):
                ssid = f.split ('_', 1) [1]
                try:
                    FIELDS [f] = grades [ssid]
                    del (grades [ssid])
                except:
                    if ssid [0] != '_':
                        REPORT.Warn (_NOGRADEINSUBJECT,
                                klass=self._klass, pid=pid, sbj=ssid)
                    FIELDS [f] = NOENTRY

        # Otherwise allocate the subjects & grades to the table slots
        ufgroups = copy.deepcopy (self._ufgroups)
        for ssid, grade in grades.items ():
            sname, ggroup, gtype = ssid_info [ssid]
            if ggroup == '#':
                continue

            for ufg in self._ufglist:
                if ggroup in ufg:
                    try:
                        slot = ufgroups [ufg].pop ()
                    except:
                        continue
                    f = 'f_{}_{}'.format (ufg, slot)
                    g = 'g_{}_{}'.format (ufg, slot)
                    _sname = sname.split ('[', 1)
                    if len (_sname) == 2:
                        sname = _sname [0].rstrip ()
                    FIELDS [f] = sname
                    FIELDS [g] = grades [ssid]
                    break
            else:
                if not ggroup in self._xSuppress:
                    print ("????", ggroup, self._xSuppress)
                    REPORT.Error (_NOSLOTFORGRADE,
                            klass=self._klass, pid=pid, sbj=ssid)
                    assert False

        # Unused fields
        for f in self._fieldnames:
            if not f in FIELDS:
                FIELDS [f] = NOENTRY

        ## Add info from report type config file
        FIELDS.update (self._typeInfo)

        ## When all fields have been defined/entered, convert the dates.
        for f in FIELDS:
            if f.endswith ('_D'):
                d = FIELDS [f]
#                print ("???", f, d)
                if d:
                    FIELDS [f] = Dates.dateConv (d)

        ## Extra items
        for k in self._xinfo:
            # Seek first entry with a value
            for k0, k1, k2 in self._xinfo [k]:
#                print ("§1", k, k0, k1, k2)
                try:
                    g = grades [k0]
                except:
                    continue
                if g == k1:
                    k0 = k0.lstrip ('_')
                    v = CONFIG.GRADES.XCOLUMNS [k0] [k2].string (' ')
                    try:
                        FIELDS [k] = v.format (**FIELDS)
                    except KeyError as e:
                        REPORT.Fail (_MISSINGFIELD, field=e.args [0],
                                fname=k0.upper (), tag=k2)
                        assert False
                    break

#        print ("#####################\n", FIELDS)

        vzv = FIELDS ['VONZUVAN']
        FIELDS ['LASTNAME_FULL'] = (((vzv + ' ') if vzv else '')
                + FIELDS ['LASTNAME'])
        pupilName = FIELDS ['FIRSTNAME'] + '_' + FIELDS ['LASTNAME']
# Tag for type of report?
        outfile = CONFIG.PATHS.REPORT_FILE_TEMPLATE.string ().format (
                number=pupilNumber, pid=str (pid), tag=FIELDS ['tag'],
                name=Paths.asciify (pupilName))
        path = os.path.join (self._outdir, outfile)
#        print ("%%%%%%%", FIELDS)
#        quit (0)
        ofile, used, missing = OdtUserFields.fillUserFields (
                self._tppath, path, FIELDS)
        REPORT.Info (_GRADEREPORTDONE, path=ofile)
        return os.path.basename (ofile)


#?
# I think this WAS a mechanism for setting certain report-relevant data
# items (from the GUI) before building the reports. The tests didn't use
# it, and it is not clear whether it is really necessary/desirable.
# The only file in the folder CONFIG/GRADES/FIELDS is one for 1./2. Halbjahr,
# which is probably incorporated into the report templates where relevant.
# Something like this might allow a reduction in the number of templates,
# but that depends on how different the templates for the terms are.
    @staticmethod
    def getXFields ():
        xfields = {}
        fdir = CONFIG.GRADES.FIELDS
        for f in fdir.list ():
            fmap = fdir [f]
            k = fmap ['K_KEY'].string ()
            xfields [k] = fmap
        return xfields
'''
