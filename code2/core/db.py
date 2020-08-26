### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/db.py - last updated 2020-08-25

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


from sqlalchemy import (create_engine, Table, Column, Integer, String,
        MetaData, ForeignKey)
from sqlalchemy.sql import select


class DB:

    def __init__(self, schoolyear):
        self.select2 = select
        ydir = os.path.join(DATA, 'SCHOOLYEARS', str(schoolyear))
        if not os.path.isdir(ydir):
            os.makedirs(ydir)
        dbfile = os.path.join(ydir, 'db_%d.sqlite3' % schoolyear)
        self.engine = create_engine('sqlite:///%s' % dbfile)

        metadata = MetaData()
        self.pupils = Table('PUPILS', metadata,
                Column('PID', String, primary_key=True),
                Column('CLASS', String),
                Column('PSORT', String),
                Column('FIRSTNAME', String),
                Column('LASTNAME', String),
                Column('STREAM', String),
                Column('FIRSTNAMES', String),
                Column('DOB_D', String),
                Column('POB', String),
                Column('SEX', String),
                Column('HOME', String),
                Column('ENTRY_D', String),
                Column('EXIT_D', String),
                Column('XDATA', String),
        )

        self.subjects = Table('SUBJECTS', metadata,
                Column('SID', String, primary_key=True),
                Column('SUBJECT', String),
        )

        self.class_subjects = Table('CLASS_SUBJECTS', metadata,
                Column('id', Integer, primary_key=True),
                Column('CLASS', String),
                Column('SID', String),
                Column('TIDS', String),
                Column('OPTIONS', String),
                Column('FLAGS', String)
        )

        metadata.create_all(self.engine) # Check tables exist, else create


    select = staticmethod(select)



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
