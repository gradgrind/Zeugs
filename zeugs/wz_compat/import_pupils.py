### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/import_pupils.py - last updated 2020-04-25

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
_WRONGLENGTH = ("Tabellenzeile hat die falsche Länge.\n  Felder: {fields}"
                "\n  Werte: {values}")
_BADCLASSNAME = "Ungülitige Klassenname: {name}"
_BAD_DATE = "Ungültiges Datum: Feld {tag}, Wert {val} in:\n  {path}"
_BADSCHOOLYEAR  = "Falsches Jahr in Tabelle {filepath}: {year} erwartet"
#?:
_IMPORT_FROM = "Importiere Schüler von Datei:\n  {path}"

# Info tag in spreadsheet table
_SCHOOLYEAR = "Schuljahr"
# Spreadsheet configuration
_PUPIL_TABLE_TITLE = "** Schüler **"


import os, datetime
from collections import OrderedDict, UserDict
from glob import glob

from wz_core.configuration import Paths
from wz_core.db import DBT
# To read/write spreadsheet tables:
from wz_table.dbtable import readDBTable, makeDBTable


def _getFieldmap():
    """Return an ordered mapping of pupil db fields to the external
    (translated) tags. The external tags are all converted to upper case
    so that case insensitive comparisons can be made.
    """
    fmap = OrderedDict ()
    for f, val in DBT.pupilFields().items ():
        fmap [f] = val.upper ()
    return fmap

# In dutch there is a word for those little lastname prefixes like "von",
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



class RawPupilData(list):
    """A list which allows keyed access to its fields.
    Here it is used for the fields of the raw pupil data.
    Before instantiating, <setup> must be called to set up the field
    names and indexes.
    """
    _fields = None

    @classmethod
    def setup(cls, fields):
        if cls._fields == None:
            cls._fields = {}
            i = 0
            for f in fields:
                cls._fields[f] = i
                i += 1

    #### The main part of the class, dealing with instances:

    def __init__(self, values):
        if len(values) != len (self._fields):
            REPORT.Fail(_WRONGLENGTH, fields = repr(self._fields),
                    values = repr(values))
        super().__init__(values)

    def __getitem__(self, key):
        if type(key) == str:
            return super().__getitem__(self._fields[key])
        else:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        if type(key) == str:
            return super().__setitem__(self._fields[key], value)
        else:
            return super().__setitem__(key, value)

    def name(self):
        """Return the (short form of) pupil's name.
        """
        return self['FIRSTNAME'] + ' ' + self['LASTNAME']



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
        return self.shortname



def readRawPupils(schoolyear, filepath, startdate):
    """Read in a table containing raw pupil data for the whole school
    from the given file (ods or xlsx, the file ending can be omitted).
    The names of date fields are expected to end with '_D'. Values are
    accepted in isoformat (YYYY-MM-DD, or %Y-%m-%d for <datetime>) or
    in the format specified for output, config value MISC.DATEFORMAT.
    If a pupil left the school before the beginning of the school year
    (<startdate>, in iso-format) (s)he will be excluded from the list
    built here.
    Build a mapping:
        {classname -> ordered list of <RawPupilData> instances}
    The ordering of the pupil data fields in the <RawPupilData> instances
    is determined ultimately by the config file TABLES/PUPILS_FIELDNAMES.
    The fields supplied in the raw data are saved as the <fields>
    attribute of the result. Fields which are not included in the raw
    data are excluded, except for the sorting field, which is added here.
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
    # Build a list of the field names which are used
    fields = OrderedDict()

    colmap = []
    # Read the (capitalised) column headers from this line
    h_colix = {h.upper (): colix
            for h, colix in table.headers.items ()}
    datefields = []
    for f, fx in fieldMap.items():
        try:
            colmap.append(h_colix [fx])
            fields[f] = fx
            if f.endswith('_D'):
                datefields.append(f)
        except:
            # Field not present in raw data
            if f == 'PSORT':
                fields[f] = fx
                colmap.append(None)
            else:
                REPORT.Warn(_FIELDMISSING, field = f, path = filepath)

    ### For sorting: use a translation table for non-ASCII characters
    ttable = str.maketrans(dict(CONF.ASCII_SUB))
    classes = UserDict()   # for the results: {class -> [row item]}
    classes.fields = fields
    ### Read the row data
    ntuples = {}
    RawPupilData.setup(fields)
    dateformat = CONF.MISC.DATEFORMAT
    for row in table:
        rowdata = []
        for col in colmap:
            rowdata.append(None if col == None else row[col])
        pdata = RawPupilData(rowdata)
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
_ADD = "+++"
_REMOVE = "---"
_CHANGE = ">>>"
_BADOP = "PUPILS operation must be %s, %s or %s: not {op}" % (_REMOVE,
        _CHANGE, _ADD)
class DeltaRaw:
    def __init__(self, schoolyear, rawdata):
        """Compare the existing pupil data with the supplied raw data.
        Create a list of differences, which can be used to perform an update.
        The differences can be of the following kinds:
            - a new pid
            - a pid has been removed
            - a field value for one pid has changed
        The list is available as attribute <delta>.
        """
        self.schoolyear = schoolyear
        self.fields = rawdata.fields    # fields to compare
        self.delta = []                 # the list of changes
        db = DBT(schoolyear, mustexist = False)
        with db:
            rows = db.select('PUPILS')
        oldpdata = {pdata['PID']: pdata for pdata in rows}
        for k, plistR in rawdata.items():
            for pdataR in plistR:
                pid = pdataR['PID']
                try:
                    pdata = oldpdata.pop(pid)
                except:
                    # Pupil not in old data: list for addition
                    self.delta.append((_ADD, pdataR))
                    continue
                for f in self.fields:
                    val = pdata[f]
                    if val != pdataR[f]:
                        # Field changed
                        self.delta.append((_CHANGE, pdataR, f, val))
        for pid, pdata in oldpdata.items():
            # Pupil not in new data: list for removal.
            # Just the necessary fields are retained (<MiniPupilData>).
            self.delta.append((_REMOVE, MiniPupilData(pdata)))


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
            if op == _REMOVE:
                d.append(pid)
            elif op == _CHANGE:
                f = line[2]
                c.append((pid, f, pdata[f]))
            elif op == _ADD:
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
                db.addRows('PUPILS', self.fields, a)
        return lines



def exportPupils (schoolyear, filepath = None):
    """Export the pupil data for the given year to a spreadsheet file,
    formatted as a 'dbtable'.
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


# Only for testing?
def getLatestRaw(schoolyear):
    allfiles = glob(Paths.getYearPath(schoolyear, 'FILE_PUPILS_RAW'))
    fpath = sorted(allfiles)[-1]
    REPORT.Info(_IMPORT_FROM, path=fpath)
    return readRawPupils(schoolyear, fpath)




##################### Test functions
_testyear = 2016
_DAY1 = '2015-09-03'

def test_01 ():
    REPORT.Test ("DB FIELDS: %s" % repr(_getFieldmap ()))
#    deltaRaw(2018, None)

def test_02 ():
    """Export pupil data to a spreadsheet table.
    """
    REPORT.Test ("Exporting pupil data for school-year %d" % _testyear)
    fpath = os.path.join(Paths.getYearPath(_testyear), 'tmp',
            'Pupil-Data', 'export_pupils_0.xlsx')
    bytefile = exportPupils(_testyear)
    with open(fpath, 'wb') as fh:
        fh.write(bytefile)
    REPORT.Test ("Exported to %s" % fpath)

def test_03 ():
    """
    Initialise PUPILS table from "old" raw data (creation from scratch,
    no pre-existing table).
    """
#    fpath = os.path.join(Paths.getYearPath(_testyear), 'testfiles',
#            'Pupil-Data', 'pupil_data_0_raw')
    fpath = os.path.join(Paths.getYearPath(_testyear), 'testfiles',
            'Pupil-Data', 'Schuelerdaten_1')
    REPORT.Test ("Initialise with raw pupil data for school-year %d from:\n  %s"
            % (_testyear, fpath))
    rpd = readRawPupils(_testyear, fpath, _DAY1)
    REPORT.Test("RAW fields: %s\n" % repr(rpd.fields))
    for klass in sorted (rpd):
        REPORT.Test ("\n +++ Class %s" % klass)
        for row in rpd [klass]:
            REPORT.Test ("   --- %s" % repr (row))
#    updateFromRaw (_testyear, rpd)
#    db.renameTable ('PUPILS', 'PUPILS0')
#    db.deleteIndexes ('PUPILS0')
#    REPORT.Test ("Saved in table PUPILS0")
    REPORT.Test("\n\n *** DELTA ***\n")
    delta = DeltaRaw(_testyear, rpd)
    for line in delta.delta:
        op, pdata = line[0], line[1]
        if op == _CHANGE:
            f = line[2]
            x = " || %s (%s -> %s)" % (f, line[3], pdata[f])
        else:
            x = ""
        REPORT.Test("  %s %s: %s%s" % (op, pdata['CLASS'],
                RawPupilData.name(pdata), x))

#    REPORT.Test("\n\n *** updating ***\n")
#    delta.updateFromDelta()


def test_04 ():
    return
    """Import pupil data – an old version (to later test updates).
    The data is in a spreadsheet table.
    """
    fpath = os.path.join (Paths.getYearPath (_testyear, 'DIR_SCHOOLDATA'),
            '_test', 'import_pupils_0')
    REPORT.Test ("Importing pupil data for school-year %d from %s" %
            (_testyear, fpath))
#    classes = importPupils (_testyear, fpath)
#    REPORT.Test ("CLASSES/PUPILS: %s" % repr (classes))

def test_05 ():
    return
    """Update to new raw pupil data.
    """
    REPORT.Test ("\n -------------------\n UPDATES:")
    importLatestRaw (_testyear)

def test_06 ():
    return
    """Compare new raw data with saved complete version:
    Import complete version, then perform update from raw data.
    """
    REPORT.Test ("\n --1-----------------\n RESET PUPILS TABLE")
    fpath = os.path.join (Paths.getYearPath (_testyear, 'DIR_SCHOOLDATA'),
            '_test', 'Schuelerdaten_1')
    REPORT.Test ("Importing pupil data for school-year %d from %s" %
            (_testyear, fpath))

    REPORT.Test ("\n --2-----------------\n COMPARE UPDATES:")
    importLatestRaw (_testyear)
