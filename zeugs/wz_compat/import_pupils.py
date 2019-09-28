#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/import_pupils.py - last updated 2019-09-28

Convert the pupil data from the form supplied by the school database.
Retain only the relevant fields, add additional fields needed by this
application.


==============================
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
"""

## For correct sorting with umlauts etc. – not used here (use ASCII converter)
#import locale
#locale.setlocale (locale.LC_COLLATE, 'de_DE.UTF-8')

# Messages
_BADSCHOOLYEAR  = "Falsches Jahr in Tabelle {filepath}"
_MISSINGDBFIELD = "Feld fehlt in Schüler-Tabelle {filepath}:\n  {field}"
_FIELDMISSING = "Benötigtes Feld {field} fehlt in Rohdatentabelle:\n  {path}"
_WRONGLENGTH = ("Tabellenzeile hat die falsche Länge.\n  Felder: {fields}"
                "\n  Werte: {values}")
_CLASSGONE = "Klasse '{klass}' nicht mehr in der Schuldatenbank"
_NEWCLASS = "Kasse '{klass}' wird hinzugefügt"
_NOUPDATES = "Keine Änderungen in der Schülertabelle für Schuljahr {year}"
_REBUILDPUPILS = "Schülertabelle für Schuljahr {year} wird aktualisiert"
_NEWPUPILS = "Neue Schüler in Klasse {klass}:\n  {pids}"
_PUPILCHANGES = "Änderungen in Klasse {klass}:\n  {data}"
_OLDPUPILS = "Abmeldungen in Klasse {klass}:\n  {pids}"
_DB_FIELD_MISSING = "PUPILS-Tabelle ohne Feld {field}"
_DB_FIELD_LOST = "PUPILS-Tabelle: Feld {field} wird nicht exportiert"
_IMPORT_FROM = "Importiere Schüler von Datei:\n  {path}"
_BADCLASSNAME = "Ungülitige Klassenname: {name}"

# Info tag in spreadsheet table
_SCHOOLYEAR = "Schuljahr"
# Spreadsheet configuration
_PUPIL_TABLE_TITLE = "** Schüler **"


import os
from collections import OrderedDict, UserDict
from glob import glob

from wz_core.configuration import Dates, Paths
from wz_core.db import DB
# To read/write spreadsheet tables:
from wz_table.dbtable import readDBTable, makeDBTable


def _getFieldmap ():
    fmap = OrderedDict ()
    for f, val in CONF.TABLES.PUPILS_FIELDNAMES.items ():
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



class _IndexedDict (list):
    """A list which allows keyed access to its fields.
    As the fields are a class attribute, this class can only be used for
    one type of list. Here it is used for the fields of the raw pupil data.
    Before instantiating, <setup> must be called to set up the field
    names and indexes.
    """
    _fields = None

    @classmethod
    def setup (cls, fields):
        if cls._fields == None:
            cls._fields = {}
            i = 0
            for f in fields:
                cls._fields [f] = i
                i += 1

    #### The main part of the class, dealing with instances:

    def __init__ (self, values):
        if len (values) != len (self._fields):
            REPORT.Fail (_WRONGLENGTH, fields=repr (self._fields),
                    values=repr (values))
        super ().__init__ (values)

    def __getitem__ (self, key):
        if type (key) == str:
            return super (). __getitem__ (self._fields [key])
        else:
            return super (). __getitem__ (key)

    def __setitem__ (self, key, value):
        if type (key) == str:
            return super (). __setitem__ (self._fields [key], value)
        else:
            return super (). __setitem__ (key, value)



def readRawPupils (schoolyear, filepath):
    """Read in a table containing raw pupil data for the whole school
    from the given file (ods or xlsx, the file ending can be omitted).
    If a pupil left the school before the beginning of the school year
    (s)he will be excluded from the list built here.
    Build a mapping:
        {classname -> ordered list of <_IndexedDict> instances}
    The ordering of the pupil data is determined by the config file
    TABLES/PUPILS_FIELDNAMES.
    The fields supplied in the raw data are saved as the <fields>
    attribute of the result.
    """
    startdate = Dates.day1 (schoolyear)
    # An exception is raised if there is no file:
    table = readDBTable (filepath)

    # Get ordered field list for the table.
    # The config file has: internal name -> table name.
    # All names are converted to upper case to enable case-free matching.
    fieldMap = _getFieldmap ()
    # Build a list of the field names which are used
    fields = OrderedDict ()

    colmap = []
    # Read the (capitalised) column headers from this line
    h_colix = {h.upper (): colix
            for h, colix in table.headers.items ()}
    for f, fx in fieldMap.items ():
        try:
            colmap.append (h_colix [fx])
            fields [f] = fx
        except:
            # Field not present in raw data
            if f == 'PSORT':
                fields [f] = fx
                colmap.append (None)
            else:
                REPORT.Warn (_FIELDMISSING, field=f, path=filepath)

    ### For sorting: use a translation table for non-ASCII characters
    ttable = str.maketrans (dict (CONF.ASCII_SUB))
    classes = UserDict ()   # for the results: {class -> [row item]}
    classes.fields = fields
    ### Read the row data
    ntuples = {}
    _IndexedDict.setup (fields)
    for row in table:
        rowdata = []
        for col in colmap:
            rowdata.append (None if col == None else row [col])
        pdata = _IndexedDict (rowdata)

        ## Exclude pupils who left before the start of the schoolyear
        if pdata ['EXIT_D'] and pdata ['EXIT_D'] < startdate:
            continue

        ## Name fixing
        firstnames, tv = tvSplitF (pdata ['FIRSTNAMES'])
        lastname = pdata ['LASTNAME']
        firstname = tvSplitF (pdata ['FIRSTNAME']) [0]
        if tv:
            sortname = lastname + ' ' + tv + ' ' + firstname
            pdata ['FIRSTNAMES'] = firstnames
            pdata ['FIRSTNAME'] = firstname
            pdata ['LASTNAME'] = tv + ' ' + lastname
        else:
            sortname = lastname + ' ' + firstname
        pdata ['PSORT'] = sortname.translate (ttable)

        klass = pdata ['CLASS']
        # Normalize class name
        try:
            if not klass [0].isdigit ():
                raise NameError
            if len (klass) == 1:
                k = '0' + klass
                pdata ['CLASS'] = k
            else:
                if klass [1].isdigit ():
                    k = klass
                else:
                    k = '0' + klass
                    pdata ['CLASS'] = klass
                k = klass if klass [1].isdigit () else '0' + klass
                if not (len (k) == 2 or k [2:].isalpha ()):
                    raise NameError
        except:
            REPORT.Fail (_BADCLASSNAME, name=klass)
        try:
            classes [k].append (pdata)
        except:
            classes [k] = [pdata]

    for klass in classes:
        # alphabetical sorting
        classes [klass].sort (key=lambda pd: pd ['PSORT'])

    return classes



def updateFromRaw (schoolyear, rawdata):
    """Update the PUPILS table from the supplied raw pupil data.
    Only the fields supplied in the raw data will be affected.
    If there is no PUPILS table, create it, leaving fields for which no
    data is supplied empty.
    <rawdata>: {klass -> [<_IndexedData> instance, ...]}
    """
    updated = False
    allfields = list (CONF.TABLES.PUPILS_FIELDNAMES)
    db = DB (schoolyear, flag='CANCREATE')
    # Build a pid-indexed mapping of the existing (old) pupil data.
    # Note that this is read in as <sqlite3.Row> instances!
    oldclasses = {}
    classes = set (rawdata) # collect all classes, old and new
    if db.tableExists ('PUPILS'):
        for pmap in db.getTable ('PUPILS'):
            pid = pmap ['PID']
            klass = pmap ['CLASS']
            classes.add (klass)
            try:
                oldclasses [klass] [pid] = pmap
            except:
                oldclasses [klass] = {pid: pmap}

    # Collect rows for the new PUPILS table:
    newpupils = []
    # Run through the new data, class-by-class
    for klass in sorted (classes):
        changed = OrderedDict ()    # pids with changed fields
        try:
            plist = rawdata [klass]
        except:
            # Class not in new data
            updated = True
#TODO: do I want to record this (with pupil names??)?
            REPORT.Warn (_CLASSGONE, klass=klass)
            continue

        try:
            oldpids = oldclasses [klass]
        except:
            # A new class
            updated = True
            oldpids = {}
#?
            REPORT.Warn (_NEWCLASS, klass=klass)

#TODO: only the PIDs are stored, I would need at least their names, for reporting
        added = []
        for pdata in plist:
            pid = pdata ['PID']
            prow = []
            try:
                pmap0 = oldpids [pid]
            except:
                # A new pupil
                for f in allfields:
                    try:
                        val = pdata [f]
                    except:
                        val = None
                    prow.append (val)
                updated = True
                added.append (pid)

            else:
                del (oldpids [pid])     # remove entry for this pid
                diff = {}
                # Compare fields
                for f in allfields:
                    oldval = pmap0 [f]
                    try: # Allow for this field not being present in the
                        # new data.
                        val = pdata [f]
                        # Record changed fields
                        if val != oldval:
                            diff [f] = val
                    except:
                        val = oldval
                    prow.append (val)
                if diff:
                    updated = True
                    changed [pid] = diff

            newpupils.append (prow)

        if added:
            REPORT.Info (_NEWPUPILS, klass=klass, pids=repr (added))
        if changed:
            REPORT.Info (_PUPILCHANGES, klass=klass, data=repr (changed))
        if oldpids:
            REPORT.Info (_OLDPUPILS, klass=klass, pids=repr (list (oldpids)))

    if updated:
        REPORT.Info (_REBUILDPUPILS, year=schoolyear)
    else:
        REPORT.Warn (_NOUPDATES, year=schoolyear)
        return
    # Build database table NEWPUPILS.
    # Use (CLASS, PSORT) as primary key, with additional index on PID.
    # This makes quite a small db (without rowid).
    indexes = db.makeTable2 ('NEWPUPILS', allfields, data=newpupils,
            force=True,
            pk=('CLASS', 'PSORT'), index=('PID',))

    db.deleteTable ('OLDPUPILS')
    if db.tableExists ('PUPILS'):
        db.renameTable ('PUPILS', 'OLDPUPILS')
    db.renameTable ('NEWPUPILS', 'PUPILS')
    db.deleteIndexes ('PUPILS')
    db.makeIndexes ('PUPILS', indexes)



def importPupils (schoolyear, filepath):
    """Import the pupils data for the given year from the given file.
    The file must be a 'dbtable' spreadsheet with the correct school-year.
    """
    classes = {}
    # Ordered field list for the table
    fields = CONF.TABLES.PUPILS_FIELDNAMES  # internal names
    rfields = fields.values ()      # external names (spreadsheet headers)

    table = readDBTable (filepath)
    try:
        if int (table.info [_SCHOOLYEAR]) != schoolyear:
            raise ValueError
    except:
        REPORT.Fail (_BADSCHOOLYEAR, filepath=filepath)

    colmap = []
    for f in rfields:
        try:
            colmap.append (table.headers [f])
        except:
            # Field not present
            REPORT.Warn (_MISSINGDBFIELD, filepath=filepath,
                    field=f)
            colmap.append (None)

    ### Read the row data
    rows = []
    classcol = table.headers [fields ['CLASS']] # class-name column
    for row in table:
        rowdata = [None if col == None else row [col] for col in colmap]
        rows.append (rowdata)

        # Count pupils in each class
        klass = rowdata [classcol]
        try:
            classes [klass] += 1
        except:
            classes [klass] = 1

    # Create the database table PUPILS from the loaded pupil data.
    db = DB (schoolyear, flag='CANCREATE')
    # Use (CLASS, PSORT) as primary key, with additional index on PID.
    # This makes quite a small db (without rowid).
    db.makeTable2 ('PUPILS', fields, data=rows,
            force=True,
            pk=('CLASS', 'PSORT'), index=('PID',))

    return classes



def exportPupils (schoolyear, filepath):
    """Export the pupil data for the given year to a spreadsheet file,
    formatted as a 'dbtable'.
    """
    # Ensure folder exists
    folder = os.path.dirname (filepath)
    if not os.path.isdir (folder):
        os.makedirs (folder)

    db = DB (schoolyear)
    classes = {}
    for row in db.getTable ('PUPILS'):
        klass = row ['CLASS']
        try:
            classes [klass].append (row)
        except:
            classes [klass] = [row]
    # Check all fields are present
    dbfields = set (db.fields)
    fields = CONF.TABLES.PUPILS_FIELDNAMES
    for f in fields:
        try:
            dbfields.remove (f)
        except:
            REPORT.Error (_DB_FIELD_MISSING, field=f)
    for f in dbfields:
        REPORT.Error (_DB_FIELD_LOST, field=f)

    rows = []
    for klass in sorted (classes):
        for vrow in classes [klass]:
            values = []
            for f in fields:
                try:
                    values.append (vrow [f])
                except KeyError:
                    values.append (None)

            rows.append (vrow)
        rows.append (None)

    makeDBTable (filepath, _PUPIL_TABLE_TITLE, fields.values (), rows,
            [(_SCHOOLYEAR, schoolyear)])



def importLatestRaw (schoolyear):
    fpath = glob (Paths.getYearPath (schoolyear, 'FILE_PUPILS_RAW')) [-1]
    REPORT.Info (_IMPORT_FROM, path=fpath)
    rpd = readRawPupils (schoolyear, fpath)
    updateFromRaw (schoolyear, rpd)




##################### Test functions
_testyear = 2016

def test_01 ():
    REPORT.Test ("DB FIELDS: %s" % repr(_getFieldmap ()))

def test_02 ():
    """
    Initialise PUPILS table from "old" raw data (creation from scratch,
    no pre-existing table).
    """
    db = DB (_testyear, 'RECREATE')
    fpath = os.path.join (Paths.getYearPath (_testyear, 'DIR_SCHOOLDATA'),
            '_test', 'pupil_data_0_raw')
    REPORT.Test ("Initialise with raw pupil data for school-year %d from:\n  %s"
            % (_testyear, fpath))
    rpd = readRawPupils (_testyear, fpath)
    for klass in sorted (rpd):
        REPORT.Test ("\n +++ Class %s" % klass)
        for row in rpd [klass]:
            REPORT.Test ("   --- %s" % repr (row))

    updateFromRaw (_testyear, rpd)
    db.renameTable ('PUPILS', 'PUPILS0')
    db.deleteIndexes ('PUPILS0')
    REPORT.Test ("Saved in table PUPILS0")

def test_03 ():
    """Import pupil data – an old version (to later test updates).
    The data is in a spreadsheet table.
    """
    fpath = os.path.join (Paths.getYearPath (_testyear, 'DIR_SCHOOLDATA'),
            '_test', 'import_pupils_0')
    REPORT.Test ("Importing pupil data for school-year %d from %s" %
            (_testyear, fpath))
    classes = importPupils (_testyear, fpath)
    REPORT.Test ("CLASSES/PUPILS: %s" % repr (classes))

def test_04 ():
    """Export pupil data to a spreadsheet table.
    """
    REPORT.Test ("Exporting pupil data for school-year %d" % _testyear)
    fpath = os.path.join (Paths.getYearPath (_testyear, 'DIR_SCHOOLDATA'),
            '_test', 'export_pupils_0')
    classes = exportPupils (_testyear, fpath)
    REPORT.Test ("Exported to %s" % fpath)

def test_05 ():
    """Update to new raw pupil data.
    """
    REPORT.Test ("\n -------------------\n UPDATES:")
    importLatestRaw (_testyear)

def test_06 ():
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
