# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_core/db.py

Last updated:  2020-03-17

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
        'GRADES', 'REMARKS', 'DATE_D')
GRADE_UNIQUE = [('PID', 'TERM'), ('PID', 'DATE_D')]
ABI_SUBJECTS_FIELDS = ('PID', 'SUBJECTS')
ABI_SUBJECTS_UNIQUE = ['PID']

import os, sqlite3
#from collections import OrderedDict #, namedtuple

from .configuration import Paths


class DB0:
    def __init__ (self, filepath, flag=None):
        if os.path.isfile (filepath):
            if flag == 'RECREATE':
                # An existing file must be removed
                os.remove (filepath)
            elif flag == 'MUSTCREATE':
                raise RuntimeError ("db-file exists already")
        else:
            if flag == None:
                REPORT.Fail (_DBFILENOTFOUND, path=filepath)
            if flag == 'NOREPORT':
                raise RuntimeError ("db-file not found")
            # Otherwise, the file may be created
            dbdir = os.path.dirname (filepath)
            if not os.path.isdir (dbdir):
                os.makedirs (dbdir)

        self.filepath = filepath
        self._dbcon = sqlite3.connect (filepath)
        self._dbcon.row_factory = sqlite3.Row
#        self._dbcon.row_factory = namedtuple_factory
        self._checkDB ()


    def close (self):
        self._dbcon.close ()
        self._dbcon = None


    def _checkDB (self):
        """Check that all necessary tables are present.
        """
        if not self.tableExists('INFO'):
            self.makeTable2('INFO', ('K', 'V'), index=['K'])
        if not self.tableExists('GRADES'):
            self.makeTable2('GRADES', GRADE_FIELDS, index=GRADE_UNIQUE)
        if not self.tableExists('PUPILS'):
            # Use (CLASS, PSORT) as primary key, with additional index
            # on PID. This makes quite a small db (without rowid).
            self.makeTable2('PUPILS', self.pupilFields(),
                    pk = ('CLASS', 'PSORT'), index = ('PID',))
        if not self.tableExists('ABI_SUBJECTS'):
            self.makeTable2('ABI_SUBJECTS', ABI_SUBJECTS_FIELDS,
                    index=ABI_SUBJECTS_UNIQUE)
#TODO ...?


    @staticmethod
    def pupilFields():
        return CONF.TABLES.PUPILS_FIELDNAMES


    def makeTable (self, name, fields, data=None):
        """Create the named table with the given fields and data.
        All fields are text (strings).
        <fields> is a list of field names.
        <data> is a list of rows. Each row is a list of values (strings)
        corresponding to the field names.
        """
        ccreate = 'CREATE TABLE {} ({})'
        cfields = ['{} TEXT'.format (key) for key in fields]

        with self._dbcon as con:
            cmd = ccreate.format (name, ",".join (cfields))
            cur = con.execute (cmd)
            if data:
                cur.executemany ('INSERT INTO {} ({})\n  VALUES ({})'.format (
                            name,
                            ', '.join (fields),
                            ', '.join (['?']*len (fields))),
                        data)


    def makeTable2 (self, name, fields, data=None, pk=None, index=None, force=False):
        """Create the named table with the given fields and data.
        <fields> is a list of field names or (name, type) pairs. The
        default type is TEXT.
        <data> is a list of rows. Each row is a list of values
        corresponding to the field names.
        <pk> is the optional primary key. If none is provided, the hidden
        'rowid' field will be generated. If there is a primary key, the
        table will be created 'WITHOUT ROWID'.
        <index> is a list of columns – or a list of lists of columns – for
        which unique indexes are to be built.
        If <force> is true, an existing table will be overwritten and its
        indexes will be dropped.
        The indexes are return as a list (one for each index) of lists
        (one entry for each field).
        """
        ccreate = "CREATE TABLE {name} ({fields}{pk}){withoutrowid}"
        cfields = []

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
        fieldList = []
        for key in fields:
            if type (key) == str:
                ctype = 'TEXT'
            else:
                key, ctype = key
            fieldList.append (key)
            if index and key in indexes:
                cfields.append ("{name} {ctype} NOT NULL".format (
                        name=key, ctype=ctype))
            else:
                cfields.append ("{name} {ctype}".format (
                        name=key, ctype=ctype))

        if self.tableExists (name):
            if force:
                self.deleteTable (name)
            else:
                REPORT.Fail (_TABLEEXISTS, name=name)

        if pk:
            primarykey = ', PRIMARY KEY ({})'.format (
                    pk if type (pk) == str
                    else ','.join (pk))
            norowid = ' WITHOUT ROWID'
        else:
            primarykey = ''
            norowid = ''
        with self._dbcon as con:
            cmd = ccreate.format (name=name, fields=','.join (cfields),
                    pk=primarykey, withoutrowid=norowid)
#            print ("CREATE:", cmd)
            cur = con.execute (cmd)
            if data:
                cur.executemany ('INSERT INTO {} ({})\n  VALUES ({})'.format (
                            name,
                            ', '.join (fieldList),
                            ', '.join (['?']*len (fieldList))),
                        data)
        if ixlist:
            self.makeIndexes (name, ixlist)
        return ixlist


    def makeIndexes (self, table, ixlist):
        """Create one or more unique indexes on the given table.
        <ixlist> is a list of lists. Each unique index has a list of fields.
        """
        with self._dbcon as con:
            n = 0
            for ix in ixlist:
                n += 1
                cindex = ('CREATE UNIQUE INDEX idx_{name}_{n}'
                        ' ON {name} ({x})').format (
                                n = n,
                                name = table,
                                x = ','.join (ix))
#                print ("INDEX:", cindex)
                con.execute (cindex)


    def getTable (self, table):
        with self._dbcon as con:
            cur = con.cursor ()
            cur.execute ('SELECT * FROM {}'.format (table))
            # Remember fields of last table read:
            self.fields = [description [0] for description in cur.description]
            return cur.fetchall ()


    def selectDistinct (self, table, column, **criteria):
        """Select distinct values from a single column.
        The <criteria> may be of the form FIELDNAME=value.
        """
        with self._dbcon as con:
            cur = con.cursor ()
            clist = []
            vlist = []
            for c, v in criteria.items ():
                clist.append (c + '=?')
                vlist.append (v)
            if clist:
                cmd = 'SELECT DISTINCT {} FROM {} WHERE {}'.format (
                        column, table, ' AND '.join (clist))
                cur.execute (cmd, vlist)
            else:
                cmd = "SELECT DISTINCT {} FROM {}".format (column, table)
                cur.execute (cmd)
            return [row [column] for row in cur.fetchall ()]


    def select (self, table, order=None, reverse=False, **criteria):
        """Select all fields of the given table.
        The results may may ordered by specifying a field or list of
        fields to <order>. Set <reverse> to true to order descending.
        The <criteria> are by default of the form FIELDNAME=value.
        However passing a tuple/list of the form (operator, value)
        for the value parameter is also possible.
        """
        with self._dbcon as con:
            cur = con.cursor ()
            clist = []
            vlist = []
            for c, v in criteria.items ():
                if isinstance(v, (list, tuple)):
                    op, v = v
                else:
                    op = '='
                clist.append ('%s %s ?' % (c, op))
                vlist.append (v)
            cmd = 'SELECT * FROM {} WHERE {}'.format (table,
                    ' AND '.join (clist))
            if order:
                if isinstance(order, str):
                    cmd += ' ORDER BY ' + order
                else:
                    cmd += ' ORDER BY ' + (', '.join (order))
                if reverse:
                    cmd += ' DESC'
            cur.execute (cmd, vlist)
            return cur.fetchall ()


    def select1 (self, table, **criteria):
        """Special select function for cases where at most 1 matching
        record is permitted.
        Return the record if found, else <None>.
        """
        records = self.select (table, **criteria)
        if len (records) == 1:
            return records [0]
        elif len (records) == 0:
            return None
        REPORT.Fail (_DBMULTIPLERECORDS, path=self.filepath,
                table=table, select=repr (criteria))


    def update (self, table, key, val, **criteria):
        with self._dbcon as con:
            cur = con.cursor ()
            clist = []
            vlist = [val]
            for c, v in criteria.items ():
                clist.append (c + '=?')
                vlist.append (v)
            cur.execute ('UPDATE {} SET {} = ? WHERE {}'.format (table, key,
                    ' AND '.join (clist)), vlist)


    def updateOrAdd (self, table, data, update_only=False, **criteria):
        """If an entry matching the criteria exists, update it with the
        given data (ignoring unsupplied fields).
        If there is no matching entry, add it, leaving unsupplied fields
        empty.
        <data> is a mapping {field name -> new value}.
        If <update_only> is true, check that an update occurred.
        In order for this to work as desired, there must be at least one
        constraint (e.g. UNIQUE) to ensure that the INSERT fails if the
        UPDATE has succeeded.
        """
        with self._dbcon as con:
            cur = con.cursor()
            fields = []     # for INSERT
            ufields = []    # for UPDATE
            vlist = []
            for f, v in data.items():
                ufields.append(f + '=?')
                fields.append(f)
                vlist.append(v)
            # For UPDATE: criteria
            clist = []
            cvlist = []
            for c, v in criteria.items():
                clist.append(c + '=?')
                cvlist.append(v)
            cur.execute('UPDATE {} SET {} WHERE {}'.format(table,
                    ', '.join(ufields),
                    ' AND '.join(clist)),
                    vlist + cvlist)
            if cur.rowcount > 1:
                REPORT.Bug("More than one line updated in db, table {table}:\n"
                        "  {criteria} -> {data}", table=table,
                        criteria=repr(criteria),
                        data=repr(data)
                )
            if update_only and cur.rowcount < 1:
                raise UpdateError
            cmd = 'INSERT OR IGNORE INTO {}({}) VALUES({})'.format(table,
                            ','.join(fields),
                            ','.join(['?']*len(fields)))
            cur.execute(cmd, vlist)


    def updateN (self, table, key, criteria, vals):
        """Perform a set of updates on a table.
        <table> is the name of the table.
        <key> is the field to update.
        <criteria> is a list of field names providing the indexing.
        <vals> is a list of tuples/lists: (value, criterion1, criterion2, ...)
        """
        with self._dbcon as con:
            cur = con.cursor ()
            clist = ' AND '.join ([c + '=?' for c in criteria])
            cmd = 'UPDATE {} SET {} = ? WHERE {}'.format (table, key, clist)
            for rowvals in vals:
                cur.execute (cmd, rowvals)


    def renameTable (self, table, newName):
        with self._dbcon as con:
            cmd = 'ALTER TABLE {} RENAME TO {}'.format (table, newName)
            con.execute (cmd)


    def deleteTable (self, table):
        with self._dbcon as con:
            cur = con.cursor ()
            cmd = 'DROP TABLE IF EXISTS {}'.format (table)
            cur.execute (cmd)


    def deleteIndexes (self, table):
        """Delete all indexes on the given table.
        Return a list of deleted index names.
        """
        indexes = []
        with self._dbcon as con:
            cur = con.cursor ()
            cmd = "SELECT name FROM sqlite_master WHERE type == 'index'"
            cur.execute (cmd)
            for i in cur.fetchall ():
                indexes.append (i [0])
                cmd = 'DROP INDEX {}'.format (i [0])
                cur.execute (cmd)
        return indexes


    def tableNames (self):
        with self._dbcon as con:
            cur = con.cursor ()
            cmd = "SELECT name FROM sqlite_master WHERE type='table'"
            cur.execute (cmd)
#            return [row ['name'] for row in cur.fetchall ()]
            return [row [0] for row in cur.fetchall ()]


    def tableExists (self, table):
        with self._dbcon as con:
            cur = con.cursor ()
            cmd = 'PRAGMA table_info({})'.format (table)
            cur.execute (cmd)
            return cur.fetchone () != None


    def tableFields (self, table):
        with self._dbcon as con:
            cur = con.cursor ()
            cmd = 'PRAGMA table_info({})'.format (table)
            cur.execute (cmd)
            cols = cur.fetchall ()
        fields = []
        for c in cols:
#            if c ['pk'] == 0:
#                fields.append (c ['name'])
            n = c ['name']
            if n [0] != '_':
                fields.append (n)
        return fields


    def addEntry (self, table, data):
        """Add a row to the given table. <data> is a <dict> containing
        entries for the fields of the table. Fields for which <data> has
        no entry take on the default value (normally NULL).
        """
        with self._dbcon as con:
            cur = con.cursor ()
            fields = []
            vlist = []
            for f, v in data.items ():
                fields.append (f)
                vlist.append (v)
            cmd = 'INSERT INTO {}({}) VALUES({})'.format (
                            table,
                            ','.join (fields),
                            ','.join (['?']*len (fields)))
            cur.execute (cmd, vlist)


    def addRows(self, table, fields, data, clear=False):
        """Add rows to the given table.
        <data> is a list of rows. Each row is a list of values
        corresponding to the field names provided in the list
        <fields>. Should any table fields not be provided, these
        will take on the default value (normally NULL).
        If <clear> is true, all entries will be removed before adding
        the new rows.
        """
        if clear:
            with self._dbcon as con:
                con.execute('DELETE FROM {}'.format(table))
            with self._dbcon as con:
                con.execute('VACUUM')
        with self._dbcon as con:
            cur = con.cursor ()
            cur.executemany ('INSERT INTO {} ({})\n  VALUES ({})'.format (
                        table,
                        ', '.join (fields),
                        ', '.join (['?']*len (fields))),
                    data)


    def deleteEntry (self, table, **criteria):
        with self._dbcon as con:
            cur = con.cursor ()
            clist = []
            vlist = []
            for c, v in criteria.items ():
                clist.append (c + '=?')
                vlist.append (v)
            cmd = 'DELETE FROM {} WHERE {}'.format (table,
                    ' AND '.join (clist))
            cur.execute (cmd, vlist)


    def getInfo(self, key):
        """Return a value from the INFO table (key -> value).
        """
        row = self.select1('INFO', K=key)
        return row['V'] if row else None


    def setInfo(self, key, value):
        """Update (or add) an entry in the INFO table (key -> value).
        The INFO table must have 'UNIQUE' K field.
        """
        with self._dbcon as con:
            cur = con.cursor()
            cur.execute('UPDATE INFO SET V=? WHERE K=?', [value, key])
            cur.execute('INSERT OR IGNORE INTO INFO(K, V) VALUES(?, ?)',
                    [key, value])



#TODO: Should the database contain the school year?
class DB (DB0):
    @staticmethod
    def getPath (schoolyear):
        return Paths.getYearPath (schoolyear, 'FILE_SQLITE')

    def __init__ (self, schoolyear, flag=None):
        super ().__init__ (self.getPath (schoolyear), flag)



class UpdateError(IndexError):
    pass



#def namedtuple_factory(cursor, row):
#    """Returns sqlite rows as named tuples."""
#    fields = [col [0] for col in cursor.description]
#    Row = namedtuple ("Row", fields)
#    return Row (*row)
