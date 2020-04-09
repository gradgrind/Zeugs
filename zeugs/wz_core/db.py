### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_core/db.py

Last updated:  2020-04-08

This module handles access to an sqlite database.

=+LICENCE=============================
Copyright 2017-2020 Michael Towers

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

_DBFILENOTFOUND     = "Datenbank-Datei nicht gefunden: {path}"
_DBMULTIPLERECORDS  = ("Es wurde mehr als ein passender Datensatz gefunden:\n"
                    " – Datei: {path}\n"
                    " – Tabelle: {table}\n"
                    " – Kriterien: {select}")
_TABLEEXISTS        = ("Datenbanktabelle {name} kann nicht erstellt werden,"
                    " da sie schon existiert")
_NODB = "Keine Daten für Schuljahr {year}"

### Field names for the grade table.
# Note that the stream should be recorded as this can change in the
# course of a year.
# Before a report has been generated, the field REPORT_TYPE is empty.
# For each term, only the data for the last report generated will be
# remembered. For extra reports, there should be a special TERM
# entry (date of issue) to identify the report.
#TODO: perhaps it should be possible to delete entries, or at least mark
# them as superseded.

GRADE_FIELDS = ('CLASS', 'STREAM', 'PID', 'TERM', 'REPORT_TYPE',
        'REMARKS', 'DATE_D', 'GDATE_D')
GRADE_UNIQUE = [('PID', 'TERM'), ('PID', 'DATE_D')]

GRADE_LOG_FIELDS = (('KEYTAG', 'INTEGER'), 'SID', 'GRADE',
        'USER', 'TIMESTAMP')

ABI_SUBJECTS_FIELDS = ('PID', 'SUBJECTS')
ABI_SUBJECTS_UNIQUE = ['PID']

import os, sqlite3

from .configuration import Paths, Dates


class DBT:
    """Database access with the possibility of some transaction
    management. The instances should be used as context managers, using
    "with".
    """
    @staticmethod
    def getMasterPath():
        return Paths.getUserFolder('ZEUGS.sqlite')

    @staticmethod
    def getYearPath(schoolyear):
        return Paths.getYearPath(schoolyear, 'FILE_SQLITE')

    @staticmethod
    def pupilFields():
        return CONF.TABLES.PUPILS_FIELDNAMES


    def __init__(self, schoolyear = None, mustexist = True,
            exclusive = False):
        """If no school-year is supplied, use the "master" database.
        For year-databases only: if <mustexist> is true (default),
        a critical error will be reported if the database doesn't exist.
        Otherwise it will be created.
        If <exclusive> is true, "with" opens an "exclusive" transaction.
        """
        self.exclusive = exclusive
        if schoolyear:
            # The database for a school-year
            self.filepath = self.getYearPath(schoolyear)
            self.schoolyear = schoolyear
            dbexists = os.path.isfile(self.filepath)
            self._dbcon = sqlite3.connect(self.filepath,
                    isolation_level = None)
            self._dbcon.row_factory = sqlite3.Row
            if not dbexists:
                if mustexist:
                    REPORT.Fail (_DBFILENOTFOUND, path=filepath)
                self._init()

        else:
            # The "master" database for the application.
            self.filepath = self.getMasterPath()
            dbexists = os.path.isfile(self.filepath)
            self._dbcon = sqlite3.connect (self.filepath)
            self._dbcon.row_factory = sqlite3.Row
            if not dbexists:
                with self:
                    self.makeTable('INFO', ('K', 'V'), index=['K'])
            try:
                with self:
                    self.schoolyear = int(self.getInfo('_SCHOOLYEAR'))
            except:
                # Choose the latest year
                try:
                    y = Paths.getYears()[0]
                except:
                    # Create a database for the current year
                    y = Dates.getschoolyear()
                    DBT(y, mustexist = False)
                with self:
                    self.setInfo('_SCHOOLYEAR', str(y))
                self.schoolyear = y


    ########### Make the objects usable as context managers ###########
    def __enter__(self):
        self._cursor = self._dbcon.cursor()
        cmd = "BEGIN EXCLUSIVE" if self.exclusive else "BEGIN"
        self._cursor.execute(cmd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._dbcon.rollback()
        else:
            self._dbcon.commit()
        self._cursor.close()
    ###################################################################


    def tableExists (self, table):
        cmd = 'PRAGMA table_info({})'.format(table)
        self._cursor.execute(cmd)
        return self._cursor.fetchone() != None


    def _init(self):
        """Initialise a new database. Using the existence tests allows
        for reinitialising individual tables.
        """
        with self:
            if not self.tableExists('INFO'):
                self.makeTable('INFO', ('K', 'V'), index = ['K'])
            if not self.tableExists('GRADES'):
                self.makeTable('GRADES', GRADE_FIELDS, pk = 'KEYTAG',
                        index = GRADE_UNIQUE)
            if not self.tableExists('GRADE_LOG'):
                self.makeTable('GRADE_LOG', GRADE_LOG_FIELDS)
            # Make indexes for (CLASS, PSORT) and PID. One might
            # consider using WITHOUT ROWID.
            if not self.tableExists('PUPILS'):
                self.makeTable('PUPILS', self.pupilFields(),
                        index = ('PID', ('CLASS', 'PSORT')))
            if not self.tableExists('ABI_SUBJECTS'):
                self.makeTable('ABI_SUBJECTS', ABI_SUBJECTS_FIELDS,
                        index = ABI_SUBJECTS_UNIQUE)


    def makeTable(self, name, fields, pk = None, index = None):
        """Create the named table with the given fields.
        <fields> is a list of field names or (name, type) pairs. The
        default type is TEXT.
        <pk> is the optional primary key name (alias for 'rowid').
        Insertions will not include this field.
        <index> is a list of columns – or a list of lists of columns – for
        which unique indexes are to be built.
        """
        ccreate = "CREATE TABLE {name} ({fields})"
        indexes = []
        ixlist = []
        if index:
            for ix in index:
                if type (ix) == str:
                    ixlist.append ((ix,))
                    indexes.append (ix)
                else:
                    ixlist.append (ix)
                    for _ix in ix:
                        indexes.append (_ix)
        cfields = []
        if pk:
            cfields.append("%s INTEGER PRIMARY KEY" % pk)
        fieldList = []
        for key in fields:
            if type (key) == str:
                ctype = 'TEXT'
            else:
                key, ctype = key
            fieldList.append (key)
            if index and (key in indexes):
                cfields.append ("{name} {ctype} NOT NULL".format (
                        name=key, ctype=ctype))
            else:
                cfields.append ("{name} {ctype}".format (
                        name=key, ctype=ctype))
        if self.tableExists (name):
            REPORT.Fail (_TABLEEXISTS, name=name)
        cmd = ccreate.format(name=name, fields=','.join (cfields))
        self._cursor.execute(cmd)
        if ixlist:
            # Create one or more unique indexes on the given table.
            # <ixlist> is a list of lists. Each unique index has a
            # list of fields.
            n = 0
            for ix in ixlist:
                n += 1
                cindex = ('CREATE UNIQUE INDEX idx_{name}_{n}'
                        ' ON {name} ({x})').format (
                                n = n,
                                name = name,
                                x = ','.join (ix))
                self._cursor.execute (cindex)


    def select(self, table,
            order = None, reverse = False, limit = None, **criteria):
        """Select all fields of the given table.
        The results may may ordered by specifying a field or list of
        fields to <order>. Set <reverse> to true to order descending.
        The <criteria> are by default of the form FIELDNAME=value.
        However passing a tuple/list of the form (operator, value)
        for the value parameter is also possible.
        """
        clist = []
        vlist = []
        for c, v in criteria.items():
            if isinstance(v, (list, tuple)):
                op, v = v
            else:
                op = '='
            clist.append('%s %s ?' % (c, op))
            vlist.append(v)
        if clist:
            cmd = 'SELECT * FROM {} WHERE {}'.format(table,
                    ' AND '.join(clist))
        else:
            cmd = 'SELECT * FROM {}'.format(table)
        if order:
            if isinstance(order, str):
                cmd += ' ORDER BY ' + order
            else:
                cmd += ' ORDER BY ' + (', '.join (order))
            if reverse:
                cmd += ' DESC'
            if limit:
                cmd += ' LIMIT %d' % limit
        self._cursor.execute(cmd, vlist)
        return self._cursor.fetchall()


    def select1(self, table, **criteria):
        """Special select function for cases where at most 1 matching
        record is permitted. No fancy parameters.
        Return the record if found, else <None>.
        """
        records = self.select (table, **criteria)
        if len(records) == 1:
            return records[0]
        elif len(records) == 0:
            return None
        REPORT.Fail(_DBMULTIPLERECORDS, path = self.filepath,
                table = table, select = repr (criteria))


    def selectDistinct (self, table, column, **criteria):
        """Select distinct values from a single column.
        The <criteria> may be of the form FIELDNAME=value.
        """
        clist = []
        vlist = []
        for c, v in criteria.items ():
            clist.append (c + '=?')
            vlist.append (v)
        if clist:
            cmd = 'SELECT DISTINCT {} FROM {} WHERE {}'.format (
                    column, table, ' AND '.join (clist))
            self._cursor.execute (cmd, vlist)
        else:
            cmd = "SELECT DISTINCT {} FROM {}".format (column, table)
            self._cursor.execute (cmd)
        return [row [column] for row in self._cursor.fetchall ()]


    def addEntry (self, table, data):
        """Add a row to the given table. <data> is a <dict> containing
        entries for the fields of the table. Fields for which <data> has
        no entry take on the default value (normally NULL).
        Return the "rowid" (integer primary key) of the added row,
        if this is available.
        """
        fields = []
        vlist = []
        for f, v in data.items ():
            fields.append (f)
            vlist.append (v)
        cmd = 'INSERT INTO {}({}) VALUES({})'.format (
                        table,
                        ','.join (fields),
                        ','.join (['?']*len (fields)))
        self._cursor.execute (cmd, vlist)
        return self._cursor.lastrowid


    def getInfo(self, key):
        """Return a value from the INFO table (key -> value).
        """
        row = self.select1('INFO', K=key)
        return row['V'] if row else None


    def setInfo(self, key, value):
        """Update (or add) an entry in the INFO table (key -> value).
        The INFO table must have 'UNIQUE' K field.
        """
        self._cursor.execute('UPDATE INFO SET V=? WHERE K=?', [value, key])
        self._cursor.execute('INSERT OR IGNORE INTO INFO(K, V) VALUES(?, ?)',
                [key, value])



#def namedtuple_factory(cursor, row):
#    """Returns sqlite rows as named tuples."""
#    fields = [col [0] for col in cursor.description]
#    Row = namedtuple ("Row", fields)
#    return Row (*row)



def test_01():
    DBT()
    DBT(2016, mustexist = False)
