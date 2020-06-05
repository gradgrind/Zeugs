### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/import_pupils.py - last updated 2020-06-05

Convert the pupil data from the form supplied by the school database.
Retain only the relevant fields, add additional fields needed by this
application.

A PUPILS table can be created from scratch, or updated.


==============================
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
"""

## For correct sorting with umlauts etc. – not used here (use ASCII converter)
#import locale
#locale.setlocale (locale.LC_COLLATE, 'de_DE.UTF-8')

# Messages
_FIELDMISSING = "Benötigtes Feld {field} fehlt in Rohdatentabelle:\n  {path}"
_BADCLASSNAME = "Ungültiger Klassenname: {name}"
_BAD_DATE = "Ungültiges Datum: Feld {tag}, Wert {val} in:\n  {path}"
_BADSCHOOLYEAR  = "Falsches Jahr in Tabelle {filepath}: {year} erwartet"
_PUPIL_LEFT = "Abgemeldeter Schüler in Klasse {klass}: {name}"
_NOFIRSTDAY = "Der erste Schultag ist nicht bekannt für Schuljahr {year}"
_CHANGE_STREAM = "Ungültige Schülergruppe: {s0}. -> {s1}"
_NO_QUALI_D = ("Klasse {klass}: Für {name} muss das Datum des Eintritts"
        " in die Qualifikationsphase gesetzt werden")

# Info tag in spreadsheet table
_SCHOOLYEAR = "Schuljahr"
# Spreadsheet configuration
_PUPIL_TABLE_TITLE = "** Schüler **"

# Specify maximum year for each stream (default is stream '')
MAXYEAR = {'': 12, 'Gym': 13}

import os, datetime
from collections import OrderedDict, UserDict
from glob import glob

from wz_core.configuration import Paths
from wz_core.db import DBT
from wz_core.pupils import Pupils, PupilData, Klass
# To read/write spreadsheet tables:
from wz_table.dbtable import readDBTable, makeDBTable
from wz_compat.config import name_filter
from wz_compat.grade_classes import klass2streams


def migratePupils(schoolyear):
    """Read the pupil data from the previous year and build a preliminary
    database table for pupils in the current (new) year, migrating the
    class names by incrementing the integer part.
    It assumes all class names start with a 2-digit year (Am.: grade) number.
    Return the path to the database file.
    """
    db = DBT(schoolyear)
    with db:
        startdate = db.getInfo('CALENDAR_FIRST_DAY')
    # Get pupil data from previous year
    pdb = Pupils(schoolyear-1)
    rows = []
    for c_old in pdb.classes():
        # Increment the year part of the class name
        try:
            cnum = int(c_old[:2]) + 1
            ctag = c_old[2:]
        except:
            REPORT.Fail(_BADCLASSNAME, klass = c_old)
        c_new = '%02d%s' % (cnum, ctag)
        for pdata in pdb.classPupils(Klass(c_old)):
            left = False
            if pdata['EXIT_D']:
                # If there is an exit date, assume the pupil has left.
                left = True
            else:
                pstream = pdata['STREAM']
                try:
                    mxy = MAXYEAR[pstream]
                except:
                    mxy = MAXYEAR['']
                if cnum > int (mxy):
                    left = True
            if left:
                REPORT.Info(_PUPIL_LEFT, klass = c_old, name = pdata.name())
                continue
            pdata['CLASS'] = c_new
            vstreams = klass2streams(c_new)
            if pstream not in vstreams:
                if pstream:
                    REPORT.Warn(_CHANGE_STREAM, s0 = pstream, s1 = vstreams[0])
                pstream = vstreams[0]
                pdata['STREAM'] = pstream
            if c_new == '12' and pstream == 'Gym':
                xdata = pdata.xdata()
                xdata['QUALI_D'] = startdate
                pdata['XDATA'] = pdata.setXdata(xdata)
            rows.append(pdata)

    # Create the database table PUPILS from the loaded pupil data.
    with db:
        db.clearTable('PUPILS')
    db.vacuum()
    with db:
        db.addRows('PUPILS', PupilData.fields(), rows)
    return db.filepath



def _getFieldmap():
    """Return an ordered mapping of pupil db fields to the external
    (translated) tags. The external tags are all converted to upper case
    so that case-insensitive comparisons can be made.
    """
    fmap = OrderedDict()
    for f, val in DBT.pupilFields().items():
        fmap[f] = val.upper()
    return fmap



class MiniPupilData(dict):
    """A subset of a pupil's data, used for pupils who are to be removed
    from the database.
    """
    def __init__(self, pdata):
        self['PID'] = pdata['PID']
        self['CLASS'] = pdata['CLASS']
        self['FIRSTNAME'] = pdata['FIRSTNAME']
        self['LASTNAME'] = pdata['LASTNAME']

    def name(self):
        """Return the (short form of) pupil's name.
        """
        return self['FIRSTNAME'] + ' ' + self['LASTNAME']



# Handling updates to the PUPILS table is a two- or three-stage process.
# First get a list of the changes:
#  - New pid
#  - Removed pid
#  - Field change
# Decide which changes to apply.
# Then (a separate function) apply this subset of the changes.
PID_ADD = "+++"
PID_REMOVE = "---"
PID_CHANGE = ">>>"
_BADOP = "PUPILS operation must be %s, %s or %s: not {op}" % (PID_REMOVE,
        PID_CHANGE, PID_ADD)
class DeltaRaw(dict):
    def __init__(self, schoolyear, filepath):
        """Read in a table containing raw pupil data for the whole school
        from the given file (ods or xlsx, the file ending can be omitted).
        The names of date fields are expected to end with '_D'. Date values
        are accepted in isoformat, YYYY-MM-DD (that is %Y-%m-%d for the
        <datetime> module) or in the format specified for output, config
        value MISC.DATEFORMAT.
        If a pupil left the school before the beginning of the school year
        (<startdate>, in iso-format) (s)he will be excluded from the list
        built here.
        Build a mapping:
            {classname -> ordered list of <PupilData> instances}
        The ordering of the pupil data fields in the <PupilData> instances
        is determined ultimately by the config file TABLES/PUPILS_FIELDNAMES.
        The fields supplied in the raw data are saved as the <fields>
        attribute of the result. Fields which are not included in the raw
        data are excluded, except for the sorting field, PSORT, which is
        added here.

        Compare the existing (in the database) pupil data with the
        raw/new data in <self>.
        Create a list of differences, which can be used to perform an update.
        The differences can be of the following kinds:
            - a new pid
            - a pid has been removed
            - a field value for one pid has changed
        The list is available as attribute <delta>.
        It is also available on a list-per-class basis as a mapping,
        attribute <cdelta>: {class -> list}
                """
        self.schoolyear = schoolyear
        db = DBT(schoolyear)
        with db:
            self.startdate = db.getInfo('CALENDAR_FIRST_DAY')
        if not self.startdate:
            REPORT.Fail(_NOFIRSTDAY, year = schoolyear)
        # An exception is raised if there is no file:
        table = readDBTable(filepath)
        try:
            # If there is a year field, check it against <schoolyear>
            _tyear = table.info[_SCHOOLYEAR]
        except KeyError:
            pass    # No year given in table
        else:
            try:
                if int(_tyear) != schoolyear:
                    raise ValueError
            except:
                REPORT.Fail(_BADSCHOOLYEAR, filepath = table.filepath,
                        year = schoolyear)

        # Get ordered field list for the table.
        # The config file has: internal name -> table name.
        # All names are converted to upper case to enable case-free matching.
        fieldMap = _getFieldmap()

        # Read the (capitalised) column headers from this line
        h_colix = {h.upper (): colix
                for h, colix in table.headers.items ()}
        # Reorder the table columns to suit the database table,
        # collect date fields for format checking / conversion.
        colmap = []
        datefields = []
        self.fields = []    # the fields supplied in the raw table
        for f, fx in fieldMap.items():
            try:
                colmap.append(h_colix [fx])
                self.fields.append(f)
                if f.endswith('_D'):
                    datefields.append(f)
            except:
                # Field not present in raw data
                colmap.append(None)
                if f == 'PSORT':
                    self.fields.append(f)
                else:
                    REPORT.Warn(_FIELDMISSING, field = f, path = filepath)

        ### Read the row data
        ntuples = {}
        dateformat = CONF.MISC.DATEFORMAT
        for row in table:
            rowdata = []
            for col in colmap:
                rowdata.append(None if col == None else row[col])
            pdata = PupilData(rowdata)
            # Check date fields
            for f in datefields:
                val = pdata[f]
                if val:
                    try:
                        datetime.date.fromisoformat(val)
                    except:
                        try:
                            pdata[f] = datetime.datetime.strptime(val,
                                    dateformat).date().isoformat()
                        except:
                            REPORT.Fail(_BAD_DATE, tag = f, val = val,
                                    path = filepath)

            ## Exclude pupils who left before the start of the schoolyear
            if pdata['EXIT_D'] and pdata['EXIT_D'] < self.startdate:
                continue

            ## Name fixing
            pnamefields = name_filter(pdata['FIRSTNAMES'],
                    pdata['LASTNAME'], pdata['FIRSTNAME'])
            pdata['FIRSTNAMES'] = pnamefields[0]
            pdata['FIRSTNAME'] = pnamefields[2]
            pdata['LASTNAME'] = pnamefields[1]
            pdata['PSORT'] = pnamefields[3]

            klass = pdata['CLASS']
            # Normalize class name
            try:
                if not klass[0].isdigit():
                    raise NameError
                if len(klass) == 1:
                    k = '0' + klass
                    pdata['CLASS'] = k
                else:
                    if klass[1].isdigit():
                        k = klass
                    else:
                        k = '0' + klass
                        pdata['CLASS'] = k
                    if not (len(k) == 2 or k[2:].isalpha()):
                        raise NameError
            except:
                REPORT.Fail(_BADCLASSNAME, name=klass)
            try:
                self[k].append(pdata)
            except:
                self[k] = [pdata]

        for klass in self:
            # alphabetical sorting
            self[klass].sort(key=lambda pd: pd['PSORT'])

        ### Compare the new data with the existing data
        self.delta = []                 # the list of changes
        self.cdelta = {}                # class-indexed lists
        with db:
            rows = db.select('PUPILS')
        oldpdata = {pdata['PID']: pdata for pdata in rows}
        for k, plistR in self.items():
            for pdataR in plistR:
                pid = pdataR['PID']
                klass = pdataR['CLASS']
                try:
                    pdata = oldpdata.pop(pid)
                except:
                    # Pupil not in old data: list for addition
                    item = (PID_ADD, pdataR)
                    self.delta.append(item)
                    try:
                        self.cdelta[klass].append(item)
                    except:
                        self.cdelta[klass] = [item]
                    continue
                for f in self.fields:
                    val = pdata[f]
                    if val != pdataR[f]:
                        # Field changed
                        item = (PID_CHANGE, pdataR, f, val)
                        self.delta.append(item)
                        try:
                            self.cdelta[klass].append(item)
                        except:
                            self.cdelta[klass] = [item]

        for pid, pdata in oldpdata.items():
            # Pupil not in new data: list for removal.
            # Just the necessary fields are retained (<MiniPupilData>).
            item = (PID_REMOVE, MiniPupilData(pdata))
            self.delta.append(item)
            klass = pdata['CLASS']
            try:
                self.cdelta[klass].append(item)
            except:
                self.cdelta[klass] = [item]


    def updateFromClassDelta(self, updates = None):
        """Update the PUPILS table from the supplied raw pupil data.
        Only the fields in the delta list (<self.fields>) will be affected.
        <updates> is a list of class-index tags for the class-delta
        mapping, <self.cdelta>. Only these ones will be updated.
        Each entry has the form '<class>-<index>'.
        Return a mapping (<lines>) {klass -> delta-item}.
        """
        if updates != None:
            umap = {}
            for tag in updates:
                try:
                    klass, index = tag.rsplit('-', 1)
                    i = int(index)
                except:
                    REPORT.Bug("Bad update tag: %s" % tag)
                else:
                    try:
                        umap[klass].append(i)
                    except:
                        umap[klass] = [i]

        lines = {}
        # Sort into deletions, changes and additions
        d, c, a = [], {}, []
        for klass, clist in self.cdelta.items():
            if updates != None:
                uk = umap.get(klass)
                if not uk:
                    continue
            klines = []
            i = 0
            for line in clist:
                if (updates == None) or (i in uk):
                    klines.append(line)
                    op, pdata = line[0:2]
                    if op == PID_REMOVE:
                        d.append(pdata['PID'])
                    elif op == PID_CHANGE:
                        pid = pdata['PID']
                        try:
                            c[pid][1].append(line[2])
                        except:
                            c[pid] = (pdata, [line[2]])
                    elif op == PID_ADD:
                        a.append(pdata)
                    else:
                        REPORT.Bug(_BADOP, op = op)
                i += 1
            if klines:
                lines[klass] = klines
        db = DBT(self.schoolyear)
        with db:
            for pid in d:
                db.deleteEntry('PUPILS', PID = pid)
        with db:
            for pid, data in c.items():
                pdata, flist = data
                # <pupilEdit> returns a mapping of new field/value pairs
                changes = self.pupilEdit(pdata, flist)
                db.updateOrAdd('PUPILS', changes,
                        update_only = True, PID = pid)
        if a:
            with db:
                # <pupilAdd> can modify/complete the <pdata> items
                db.addRows('PUPILS', DBT.pupilFields(),
                        [self.pupilAdd(pdata) for pdata in a])
        return lines


    def pupilAdd(self, pdata):
        """Manipulate a <PupilData> instance before saving it to the database.
        """
        # Handle (conditionally) STREAM and XDATA (QUALI_D)
        klass = pdata['CLASS']
        stream = pdata['STREAM']
        vstreams = klass2streams(klass)
        if stream not in vstreams:
            if stream:
                REPORT.Warn(_CHANGE_STREAM, s0 = stream, s1 = vstreams[0])
            stream = vstreams[0]
            pdata['STREAM'] = stream
        xdata = pdata.xdata()
        if not xdata.get('QUALI_D'):
            if klass == '12':
                if stream == 'Gym':
                    xdata['QUALI_D'] = self.startdate
                    pdata['XDATA'] = pdata.setXdata(xdata)
            elif klass == '13':
                REPORT.Warn(_NO_QUALI_D, klass = klass, name = pdata.name())
        return pdata


    def pupilEdit(self, pdata, fieldlist):
        """Tweak a pupil entry modification before saving it to the database.
        Return a mapping: {field -> new value}.
        <fieldlist> is a list of field names to be changed in the db –
        the values are in <pdata>.
        """
        # No manipulation:
        return {field: pdata[field] for field in fieldlist}



def exportPupils (schoolyear, filepath = None):
    """Export the pupil data for the given year to a spreadsheet file,
    (.xlsx) formatted as a 'dbtable'.
    If <filepath> is supplied, it must be the full path, but the
    file-type ending is not required. The full path to the spreadsheet
    file, including the file-type ending, is returned.
    If no filepath is given, return the spreadsheet as a <bytes> object.
    """
    if filepath:
        # Ensure folder exists
        folder = os.path.dirname(filepath)
        if not os.path.isdir(folder):
            os.makedirs(folder)

    db = DBT(schoolyear)
    classes = {}
    with db:
        rows = db.select('PUPILS')
    for row in rows:
        klass = row['CLASS']
        try:
            classes[klass].append(row)
        except:
            classes[klass] = [row]
    # The fields of the pupils table (in the database):
    fields = CONF.TABLES.PUPILS_FIELDNAMES
    rows = []
    for klass in sorted(classes):
        for vrow in classes[klass]:
            values = []
            for f in fields:
                try:
                    values.append(vrow[f])
                except KeyError:
                    values.append(None)

            rows.append(vrow)
        rows.append(None)

    return makeDBTable(filepath, _PUPIL_TABLE_TITLE, fields.values(),
            rows, [(_SCHOOLYEAR, schoolyear)])




##################### Test functions

def test_01():
    REPORT.Test("DB FIELDS: %s" % repr(_getFieldmap ()))

def test_02():
    """Export pupil data to a spreadsheet table.
    """
    _year = 2016
    REPORT.Test ("Exporting pupil data for school-year %d" % _year)
    fpath = os.path.join(Paths.getYearPath(_year), 'tmp',
            'Pupil-Data', 'export_pupils_%d.xlsx' % _year)
    bytefile = exportPupils(_year)
    with open(fpath, 'wb') as fh:
        fh.write(bytefile)
    REPORT.Test ("Exported to %s" % fpath)

def test_03():
    """Create a new year with PUPILS table from raw pupil data.
    """
    import shutil
    year = 2017
    DAY1 = '2016-08-04'
    # Delete the year folder if it exists
    ypath = Paths.getYearPath(year)
    if os.path.exists(ypath):
        shutil.rmtree(ypath)
    REPORT.Test ("Initialise PUPILS from raw data: %d" % year)
    _year0 = 2016
    _ypath0 = Paths.getYearPath(_year0)
    fpath = os.path.join(_ypath0, 'testfiles',
            'Pupil-Data', 'pupil_data_%d_raw' % year)
    REPORT.Test("FROM %s" % fpath)
    db = DBT(year, mustexist = False)
    with db:
        db.setInfo('CALENDAR_FIRST_DAY', DAY1)
    rpd = DeltaRaw(year, fpath)
    REPORT.Test("RAW fields: %s\n" % repr(rpd.fields))
    for klass in sorted(rpd):
        REPORT.Test("\n +++ Class %s" % klass)
        for row in rpd[klass]:
            REPORT.Test("   --- %s" % repr (row))

    REPORT.Test("\n\n *** DELTA ***\n")
    for line in rpd.delta:
        op, pdata = line[0], line[1]
        if op == PID_CHANGE:
            f = line[2]
            x = " || %s (%s -> %s)" % (f, line[3], pdata[f])
        else:
            x = ""
        REPORT.Test("  %s %s: %s%s" % (op, pdata['CLASS'],
                PupilData.name(pdata), x))

    REPORT.Test("\n\n *** saving ***\n")
    rpd.updateFromClassDelta()

    dbpath = DBT(year).filepath
    tmpdir = os.path.join(_ypath0, 'tmp')
    db2 = os.path.join(tmpdir, os.path.basename(dbpath))
    os.replace(dbpath, db2)
    REPORT.Test("Database %d saved as %s" % (year, db2))

def test_04():
    year = 2017
    DAY1 = '2016-08-04'
    REPORT.Test("Migrate pupils from %d to %d" % (year - 1, year))
    db = DBT(year, mustexist = False)
    with db:
        db.setInfo('CALENDAR_FIRST_DAY', DAY1)
    REPORT.Test("Pupil table created in: " + migratePupils(year))

def test_05():
    _year0 = 2016
    year = 2017
    REPORT.Test("Update year %d with raw data" % year)
    fpath = os.path.join(Paths.getYearPath(_year0), 'testfiles',
            'Pupil-Data', 'pupil_data_%d_raw' % year)
    REPORT.Test("FROM %s" % fpath)
    delta = DeltaRaw(year, fpath)
    REPORT.Test("\n\n *** DELTA ***\n")
    for line in delta.delta:
        op, pdata = line[0], line[1]
        if op == PID_CHANGE:
            f = line[2]
            x = " || %s (%s -> %s)" % (f, line[3], pdata[f])
        else:
            x = ""
        REPORT.Test("  %s %s: %s%s" % (op, pdata['CLASS'],
                PupilData.name(pdata), x))

    REPORT.Test("\n\n *** updating ***\n")
    delta.updateFromClassDelta()

def test_06():
    """Export new year's data, delete the PUPILS table and import the
    saved data.
    """
    year = 2017
    _year0 = 2016
    _ypath0 = Paths.getYearPath(_year0)
    REPORT.Test("Save and restore the pupil data for year %d" % year)
    fspath = os.path.join(_ypath0, 'tmp',
            'Pupil-Data', 'export_pupils_%d.xlsx' % year)
    bytefile = exportPupils(year)
    with open(fspath, 'wb') as fh:
        fh.write(bytefile)
    REPORT.Test (" ... exported to %s" % fspath)

    db = DBT(year)
    with db:
        db.clearTable('PUPILS')
    db.vacuum()
    REPORT.Test (" ... initialise PUPILS from saved data")
    delta = DeltaRaw(year, fspath)
    delta.updateFromClassDelta()

def test_07():
    """Move new year to "tmp" folder.
    """
    import shutil
    year = 2017
    _year0 = 2016
    _ypath0 = Paths.getYearPath(_year0)
    ypath = Paths.getYearPath(year)
    tpath = os.path.join(_ypath0, 'tmp', os.path.basename(ypath))
    if os.path.exists(tpath):
        shutil.rmtree(tpath)
    os.rename(ypath, tpath)
    REPORT.Test("Resulting test data moved to %s" % tpath)
