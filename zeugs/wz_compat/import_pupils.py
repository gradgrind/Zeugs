### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/import_pupils.py - last updated 2020-05-06

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


#TODO: master db
# The calendar might also be in the db ... (json in INFO table?)

#TODO: Add entry to Qualifikationsphase for new 12.Gym (see readRawPupils)
# It might be more appropriate to change this entry in the PUPILS table
# so that it is more general, e.g. XDATA, which could be json.

def migratePupils(schoolyear):
    """Read the pupil data from the previous year and build a preliminary
    database table for pupils in the current (new) year, migrating the
    class names by incrementing the integer part.
    It assumes all class names start with a 2-digit year (Am.: grade) number.
    Return the path to the (possibly newly created) database file.
    """
    # Get pupil data from previous year
    pdb = Pupils(schoolyear-1)
    rows = []
    for c_old in pdb.classes():
        # Increment the year part of the class name
        try:
            cnum = int(c_old[:2]) + 1
            ctag = c_old[2:]
        except:
            REPORT.Fail(_BADCLASSNAME, klass=c_old)
        c_new = '%02d%s' % (cnum, ctag)
        for pdata in pdb.classPupils(Klass(c_old)):
            left = False
            if pdata['EXIT_D']:
                # If there is an exit date, assume the pupil has left.
                left = True
            else:
                try:
                    mxy = MAXYEAR[pdata['STREAM']]
                except:
                    mxy = MAXYEAR['']
                if cnum > int (mxy):
                    left = True
            if left:
                REPORT.Info(_PUPIL_LEFT, klass=c_old, name=pdata.name())
                continue
            pdata['CLASS'] = c_new
            rows.append(pdata)

    # Create the database table PUPILS from the loaded pupil data.
    db = DBT(schoolyear, mustexist = False)
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

# In Dutch there is a word for those little lastname prefixes like "von",
# "zu", "van" "de": "tussenvoegsel". For sorting purposes these can be a
# bit annoying because they are often ignored, e.g. "van Gogh" would be
# sorted under "G".

####++++++++++++++++++++++++++++++++++++++++++++++++####
#### A surname splitter. This version regards the first capital letter as
#### the start of the name for sorting purposes. Thus o'Brien is seen as
#### ["o'", "Brien"], but O'Brien is seen as ["O'Brien"]!

#### To handle confusing cases, a manual (re)ordering should be possible.

#def usplit (name):
#    i = 0
#    for c in name:
#        if c.isupper():
#            if i == 0: return None, name
#            if name [i-1] == ' ':
#                return name [:i-1], name [i:]
#            else:
#                return name [:i], name [i:]
#        i += 1
#    print ('???', name)
#    return None

#print (' -->', usplit ('de Witt'))
#print (' -->', usplit ('De Witt'))
#print (' -->', usplit ("o'Riordan"))
#print (' -->', usplit ("O'Riordan"))

####------------------------------------------------####

# This is a custom name splitter for raw data which has the lastname
# prefixes at the end of the firstname(s). It uses a look-up table of
# prefix "words".
def tvSplitF (name):
    """Split a "tussenvoegsel" from the end of the first names.
    Return a tuple: (Actual first names, tussenvoegsel or <None>).
    """
    tvlist = list (CONF.MISC.TUSSENVOEGSEL)
    ns = name.split ()
    if len (ns) >= 1:
        tv = []
        i = 0
        for s in reversed (ns):
            if s in tvlist:
                tv.insert (0, s)
                i -= 1
            else:
                break
        if i < 0:
            return (" ".join (ns [:i]), " ".join (tv))
    return (" ".join (ns), None)    # ensure normalized spacing



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



#TODO: use <startdate> to initialise QUALI_D field for 12.Gym (if
# no other date is there already).
def readRawPupils(schoolyear, filepath, startdate):
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
    """
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
    fields = []     # The fields supplied in the raw table
    for f, fx in fieldMap.items():
        try:
            colmap.append(h_colix [fx])
            fields.append(f)
            if f.endswith('_D'):
                datefields.append(f)
        except:
            # Field not present in raw data
            colmap.append(None)
            if f == 'PSORT':
                fields.append(f)
            else:
                REPORT.Warn(_FIELDMISSING, field = f, path = filepath)

    ### For sorting: use a translation table for non-ASCII characters
    ttable = str.maketrans(dict(CONF.ASCII_SUB))
    classes = UserDict()   # for the results: {class -> [row item]}
    classes.fields = fields
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
        if pdata['EXIT_D'] and pdata['EXIT_D'] < startdate:
            continue

        ## Name fixing (if the input table doesn't have the PSORT field)
        if not pdata['PSORT']:
            firstnames, tv = tvSplitF(pdata['FIRSTNAMES'])
            lastname = pdata['LASTNAME']
            firstname = tvSplitF(pdata['FIRSTNAME'])[0]
            if tv:
                sortname = lastname + ' ' + tv + ' ' + firstname
                pdata['FIRSTNAMES'] = firstnames
                pdata['FIRSTNAME'] = firstname
                pdata['LASTNAME'] = tv + ' ' + lastname
            else:
                sortname = lastname + ' ' + firstname
            pdata['PSORT'] = sortname.translate(ttable)

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
            classes[k].append(pdata)
        except:
            classes[k] = [pdata]

    for klass in classes:
        # alphabetical sorting
        classes[klass].sort(key=lambda pd: pd['PSORT'])

    return classes


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
class DeltaRaw:
    def __init__(self, schoolyear, rawdata):
        """Compare the existing pupil data with the supplied raw data.
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
        self.fields = rawdata.fields    # fields to compare
        self.delta = []                 # the list of changes
        self.cdelta = {}                # class-indexed lists
        db = DBT(schoolyear, mustexist = False)
        with db:
            rows = db.select('PUPILS')
        oldpdata = {pdata['PID']: pdata for pdata in rows}
        for k, plistR in rawdata.items():
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


    def updateFromClassDelta(self, updates):
        """Update the PUPILS table from the supplied raw pupil data.
        Only the fields in the delta list (<self.fields>) will be affected.
        <updates> is a list of class-index tags for the class-delta
        mapping, <self.cdelta>. Only these ones will be updated.
        Return a mapping (<lines>) {klass -> delta-item}
        """
        lines = {}
        # Sort into deletions, changes and additions
        d, c, a = [], [], []
        for tag in updates:
            try:
                klass, index = tag.rsplit('-', 1)
                line = self.cdelta[klass][int(index)]
            except:
                REPORT.Bug("Bad update tag: %s" % tag)
#            REPORT.Test("UPDATE: %s" % repr(line))
            try:
                lines[klass].append(line)
            except:
                lines[klass] = [line]

            op, pdata = line[0:2]
            if op == PID_REMOVE:
                d.append(pdata['PID'])
            elif op == PID_CHANGE:
                f = line[2]
                c.append((pdata, f))
            elif op == PID_ADD:
                a.append(pdata)
            else:
                REPORT.Bug(_BADOP, op = op)
        db = DBT(self.schoolyear)
        with db:
            for pid in d:
                db.deleteEntry('PUPILS', PID = pid)
        with db:
            for pdata, f in c: # new value = pdata[f]
                # <pupilEdit> returns a mapping of new field/value pairs
                db.updateOrAdd('PUPILS', pupilEdit(pdata, f),
                        update_only = True, PID = pdata['PID'])
        if a:
            with db:
                # <pupilAdd> can modify/complete the <pdata> items
                db.addRows('PUPILS', DBT.pupilFields(),
                        [pupilAdd(pdata) for pdata in a])
        return lines


#DEPRECATED? Would need to adapt tests (below)
    def updateFromDelta(self, updates = None):
        """Update the PUPILS table from the supplied raw pupil data.
        Only the fields in the delta list (<self.fields>) will be affected.
        <updates> is a list of indexes into the delta list – the
        updates to be applied (the others are ignored).
        If <updates> is not supplied, all updates are applied.
        """
        if updates == None:
            lines = self.delta
        else:
            lines = [self.delta[int(i)] for i in updates]
        # Sort into deletions, changes and additions
        d, c, a = [], [], []
        for line in lines:
            op, pdata = line[0:2]
            pid = pdata['PID']
            if op == PID_REMOVE:
                d.append(pid)
            elif op == PID_CHANGE:
                f = line[2]
                c.append((pid, f, pdata[f]))
            elif op == PID_ADD:
                a.append(pdata)
            else:
                REPORT.Bug(_BADOP, op = op)
        db = DBT(self.schoolyear)
        with db:
            for pid in d:
                db.deleteEntry('PUPILS', PID = pid)
        with db:
            for pid, f, val in c:
                db.updateOrAdd('PUPILS', {f: val},
                        update_only = True, PID = pid)
        if a:
            with db:
                db.addRows('PUPILS', DBT.pupilFields(), a)
        return lines



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




def pupilAdd(pdata):
    """Manipulate a <PupilData> instance before saving it to the database.
    """
# Handle (conditionally) STREAM and XDATA (QUALI_D)
    return pdata    # No manipulation


def pupilEdit(pdata, field):
    """Tweak a pupil entry modification before saving it to the database.
    Return a mapping: {field -> new value}.
    <field> is the name of the field which specifies the desired change
    (the value being in <pdata>.
    """
# Handle (conditionally) STREAM and XDATA (QUALI_D) ... PSORT if name changed
    return {field: pdata[field]}    # No manipulation



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
    # Delete the year folder if it exists
    ypath = Paths.getYearPath(year)
    if os.path.exists(ypath):
        shutil.rmtree(ypath)
    DAY1 = '2016-08-04'
    REPORT.Test ("Initialise PUPILS from raw data: %d" % year)
    _year0 = 2016
    _ypath0 = Paths.getYearPath(_year0)
    fpath = os.path.join(_ypath0, 'testfiles',
            'Pupil-Data', 'pupil_data_%d_raw' % year)
    REPORT.Test("FROM %s" % fpath)
    rpd = readRawPupils(year, fpath, DAY1)
    REPORT.Test("RAW fields: %s\n" % repr(rpd.fields))
    for klass in sorted (rpd):
        REPORT.Test ("\n +++ Class %s" % klass)
        for row in rpd [klass]:
            REPORT.Test ("   --- %s" % repr (row))

    REPORT.Test("\n\n *** DELTA ***\n")
    delta = DeltaRaw(year, rpd)
    for line in delta.delta:
        op, pdata = line[0], line[1]
        if op == PID_CHANGE:
            f = line[2]
            x = " || %s (%s -> %s)" % (f, line[3], pdata[f])
        else:
            x = ""
        REPORT.Test("  %s %s: %s%s" % (op, pdata['CLASS'],
                PupilData.name(pdata), x))

    REPORT.Test("\n\n *** saving ***\n")
#TODO?
    delta.updateFromDelta()

    dbpath = DBT(year).filepath
    tmpdir = os.path.join(_ypath0, 'tmp')
    db2 = os.path.join(tmpdir, os.path.basename(dbpath))
    os.replace(dbpath, db2)
    REPORT.Test("Database %d saved as %s" % (year, db2))

def test_04():
    year = 2017
    REPORT.Test("Migrate pupils from %d to %d" % (year - 1, year))
    REPORT.Test("Pupil table created in: " + migratePupils(year))

def test_05():
    _year0 = 2016
    year = 2017
    DAY1 = '2016-08-04'
    REPORT.Test("Update year %d with raw data" % year)
    fpath = os.path.join(Paths.getYearPath(_year0), 'testfiles',
            'Pupil-Data', 'pupil_data_%d_raw' % year)
    REPORT.Test("FROM %s" % fpath)
    rpd = readRawPupils(year, fpath, DAY1)
    REPORT.Test("\n\n *** DELTA ***\n")
    delta = DeltaRaw(year, rpd)
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
#TODO?
    delta.updateFromDelta()

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
    DAY1 = '2016-08-04'
    REPORT.Test (" ... initialise PUPILS from saved data")
    rpd = readRawPupils(year, fspath, DAY1)
    delta = DeltaRaw(year, rpd)
#TODO?
    delta.updateFromDelta()

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
