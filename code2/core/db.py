### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/db.py - last updated 2020-09-06

Database access.

==============================
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
"""

import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)


# Messages:
_DBMULTIPLERECORDS  = ("Es wurde mehr als ein passender Datensatz gefunden:\n"
                    " – Datei: {path}\n"
                    " – Tabelle: {table}\n"
                    " – Kriterien: {select}")
_TABLEEXISTS        = ("Datenbanktabelle {name} kann nicht erstellt werden,"
                    " da sie schon existiert")


import sqlite3 #, builtins


class DBerror(Exception):
    pass

#TODO: Don't automatically create a year if there is none(?).
#TODO: When the active year is switched, update builtins.active_year(?).
#TODO: Do I actually need the "master" database?
class DB:
    """Database access with the possibility of some transaction
    management. The instances should be used as context managers, using
    "with".
    """
    def __init__(self, schoolyear = None, exclusive = False):
        """If no school-year is supplied, use the "master" database.
        If <exclusive> is true, "with" opens an "exclusive" transaction.
        If no database exists for the given year, it will be created.
        """
        self.exclusive = exclusive
        if schoolyear:
            self.schoolyear = schoolyear
            ydir = os.path.join(DATA, 'SCHOOLYEARS', str(schoolyear))
            if not os.path.isdir(ydir):
                os.makedirs(ydir)
            self.filepath = os.path.join(ydir, 'db_%d.sqlite3' % schoolyear)
            # Disable the sqlite3 module’s implicit transaction management
            # by setting isolation_level to None. This will leave the
            # underlying sqlite3 library operating in autocommit mode.
            # The transaction state is then controlled by explicitly
            # issuing BEGIN, ROLLBACK, SAVEPOINT, and RELEASE statements.
            self._dbcon = sqlite3.connect(self.filepath,
                    isolation_level = None)
            self._dbcon.row_factory = sqlite3.Row
            # Check tables exist
            with self:
#            if not self.tableExists('INFO'):
#                self.makeTable('INFO', ('K', 'V'), index = ['K'])
#            if not self.tableExists('GRADES_INFO'):
#                self.makeTable('GRADES_INFO', GRADES_INFO_FIELDS,
#                        pk = 'KEYTAG', index = GRADES_INFO_UNIQUE)
#            if not self.tableExists('GRADES_LOG'):
#                self.makeTable('GRADES_LOG', GRADES_LOG_FIELDS,
#                        pk = 'ID', index = GRADES_LOG_UNIQUE)


#            if not self.tableExists('TEACHERS'):
#                self.makeTable('TEACHERS', CONF.TABLES.TEACHER_FIELDNAMES,
#                        index = TEACHERS_UNIQUE)

                if not self.tableExists('PUPIL'):
                    # One might consider using WITHOUT ROWID.
                    from local.pupil_config import PUPIL_FIELDS
                    self.makeTable('PUPIL', PUPIL_FIELDS,
                            index = ('PID', ('CLASS', 'PSORT')))
                if not self.tableExists('SUBJECT'):
                    # One might consider using WITHOUT ROWID.
                    from local.course_config import SUBJECT_FIELDS
                    self.makeTable('SUBJECT', SUBJECT_FIELDS,
                            index = ('SID',))
                if not self.tableExists('CLASS_SUBJECT'):
                    # One might consider using WITHOUT ROWID.
                    from local.course_config import CLASS_SUBJECT_FIELDS
                    self.makeTable('CLASS_SUBJECT', CLASS_SUBJECT_FIELDS,
                            index = ('SID',))

                if not self.tableExists('GRADES'):
                    from local.grade_config import GRADES_FIELDS
                    self.makeTable('GRADES', PUPIL_FIELDS,
                            index = (('PID', 'TERM'),))

#            if not self.tableExists('ABI_SUBJECTS'):
#                self.makeTable('ABI_SUBJECTS', ABI_SUBJECTS_FIELDS,
#                        index = ABI_SUBJECTS_UNIQUE)


        else:
#?
#TODO ...
            raise DBerror("TODO: 'Master' database")
            # The "master" database for the application.
            self.filepath = self.getMasterPath()
            dbexists = os.path.isfile(self.filepath)
            if not dbexists:
                dirpath = os.path.dirname(self.filepath)
                if not os.path.isdir(dirpath):
                    os.makedirs(dirpath)
            self._dbcon = sqlite3.connect(self.filepath,
                    isolation_level = None)
            self._dbcon.row_factory = sqlite3.Row
            if not dbexists:
                with self:
                    self.makeTable('INFO', ('K', 'V'), index=['K'])
                    pwpath = Paths.getUserFolder('PWinit')
                    with open(pwpath, 'r', encoding = 'utf-8') as fhi:
                        while True:
                            line = fhi.readline()
                            if not line:
                                break
                            pwh = line.strip()
                            if pwh and pwh[0] != '#':
                                u, p, h = pwh.split('|', 2)
                                # Save the value for use by teachers::User
                                self.setInfo('PW_' + u, '%s|%s' % (p, h))
            try:
                with self:
                    self.schoolyear = int(self.getInfo('_SCHOOLYEAR'))
            except:
                # Choose the latest year
                try:
                    y = Paths.getYears()[0]
                except:
#                    # Create a database for the current year
#                    y = Dates.getschoolyear()
#                    DBT(y, mustexist = False)
                    y = None
                    with self:
                        self.setInfo('_SCHOOLYEAR', y)
                else:
                    with self:
                        self.setInfo('_SCHOOLYEAR', str(y))
                self.schoolyear = y
            builtins.active_year = self.schoolyear



    ########### Make the objects usable as context managers ###########
    def __enter__(self):
        self._cursor = self._dbcon.cursor()
        cmd = "BEGIN EXCLUSIVE" if self.exclusive else "BEGIN"
        self._cursor.execute(cmd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._dbcon.rollback()
            self._cursor.close()
#?
            raise
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
                if type(ix) == str:
                    ixlist.append((ix,))
                    indexes.append(ix)
                else:
                    ixlist.append(ix)
                    for _ix in ix:
                        indexes.append(_ix)
        cfields = []
        if pk:
            cfields.append("%s INTEGER PRIMARY KEY" % pk)
        fieldList = []
        for key in fields:
            if type(key) == str:
                ctype = 'TEXT'
            else:
                key, ctype = key
            fieldList.append(key)
            if index and (key in indexes):
                cfields.append("{name} {ctype} NOT NULL".format(
                        name=key, ctype=ctype))
            else:
                cfields.append("{name} {ctype}".format(
                        name=key, ctype=ctype))
        if self.tableExists(name):
            raise DBerror(_TABLEEXISTS.format(name=name))
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
                self._cursor.execute(cindex)


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
        raise DBerror(_DBMULTIPLERECORDS.format(path = self.filepath,
                table = table, select = repr (criteria)))


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


    def addRows(self, table, fields, data):
        """Add rows to the given table.
        <data> is a list of rows. Each row is a list of values
        corresponding to the field names provided in the list
        <fields>. Should any table fields not be provided, these
        will take on the default value (normally NULL).
        """
        self._cursor.executemany(
                'INSERT INTO {} ({})\n  VALUES ({})'.format (
                        table,
                        ', '.join (fields),
                        ', '.join (['?']*len (fields))
                ), data
        )


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


    def updateOrAdd (self, table, data, update_only = False, **criteria):
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
        self._cursor.execute('UPDATE {} SET {} WHERE {}'.format(table,
                ', '.join(ufields),
                ' AND '.join(clist)),
                vlist + cvlist)
        if self._cursor.rowcount > 1:
            raise DBerror(
                    "BUG: More than one line updated in db, table {table}:\n"
                    "  {criteria} -> {data}".format(table=table,
                    criteria=repr(criteria),
                    data=repr(data))
            )
        if update_only and self._cursor.rowcount < 1:
            raise UpdateError
        cmd = 'INSERT OR IGNORE INTO {}({}) VALUES({})'.format(table,
                        ','.join(fields),
                        ','.join(['?']*len(fields)))
        self._cursor.execute(cmd, vlist)


    def deleteEntry (self, table, **criteria):
        clist = []
        vlist = []
        for c, v in criteria.items ():
            clist.append (c + '=?')
            vlist.append (v)
        cmd = 'DELETE FROM {} WHERE {}'.format (table,
                ' AND '.join (clist))
        self._cursor.execute (cmd, vlist)


    def clearTable(self, table):
        self._cursor.execute('DELETE FROM {}'.format(table))


    def vacuum(self):
        """This should not be called with a transaction, i.e. not
        within a <with> wrapper.
        """
        self._dbcon.execute('VACUUM')



class UpdateError(IndexError):
    pass


#def namedtuple_factory(cursor, row):
#    """Returns sqlite rows as named tuples."""
#    fields = [col [0] for col in cursor.description]
#    Row = namedtuple ("Row", fields)
#    return Row (*row)











#    @staticmethod
#    def count_entries(conn, table, *where):
#        s = select([func.count()]).select_from(table)
#        for k, v in where:
#            s = s.where(k == v)
#        return conn.execute(s).fetchone()[0]


if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    conn = DATABASE.engine.connect()
    s = select([DATABASE.pupils]).where(DATABASE.pupils.c.CLASS == '11')
    result = conn.execute(s)
    print("\n++++++ ALL PUPILS in class 11 ++++++")
    for row in result:
        print(row)
    conn.execute(DATABASE.subjects.delete())
    conn.execute(DATABASE.subjects.insert(), [
        {'SID': 'Bio', 'SUBJECT': 'Biologie'},
        {'SID': 'De', 'SUBJECT': 'Deutsch'},
        {'SID': 'En', 'SUBJECT': 'Englisch'},
    ])
    print("\n++++++ ALL SUBJECTS ++++++")
    for row in conn.execute(select([DATABASE.subjects])):
        print(row)
    conn.execute(DATABASE.subjects.delete())
    conn.execute(DATABASE.subjects.insert().values(SID='Ges', SUBJECT='Geschichte'))
    print("\n++++++ ALL SUBJECTS (CHANGED) ++++++")
    for row in conn.execute(select([DATABASE.subjects])):
        print(row)

    pid = '200506'
    #s = select([DATABASE.pupils]).where(DATABASE.pupils.c.CLASS == '11')
    s = DATABASE.pupils.select().where(DATABASE.pupils.c.PID == pid)
    result = conn.execute(s)
    pdata = result.fetchone()
    print("\nPID(%s):" % pid, pdata['FIRSTNAME'] + ' ' + pdata['LASTNAME'])
    print("  ...", pdata)
    print("PID(%s):" % pid, result.fetchone())

    s = DATABASE.select(columns=[DATABASE.pupils.c.CLASS]).distinct()
    result = conn.execute(s)
    print("\n???", result.fetchall())


#    r = conn.execute(select([func.count()]).select_from(DATABASE.grades).where(
#            DATABASE.grades.c.PID == '200651').where(DATABASE.grades.c.TERM == '2'))
#    r = conn.execute(select([func.count()]).select_from(DATABASE.pupils).where(
#            DATABASE.pupils.c.CLASS == '11'))
#    print ("\nCOUNT:", r.fetchone())

    r = DATABASE.count_entries(conn, DATABASE.pupils, (DATABASE.pupils.c.CLASS, '11'))
    print("\nCOUNT:", r)
    r = DATABASE.count_entries(conn, DATABASE.grades,
            (DATABASE.grades.c.PID, '200651'),
            (DATABASE.grades.c.TERM, '1'))
    print("\nCOUNT:", r)