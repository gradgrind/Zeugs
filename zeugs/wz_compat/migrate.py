#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/migrate.py - last updated 2019-09-28

Use data from the database of a previous year to get a starting point
for a new year.

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

# Messages
_BADCLASSNAME = "Ungültiger Klassenname: {klass}"
_PUPIL_LEFT = "Abgemeldeter Schüler in Klasse {klass}: {name}"


from wz_core.db import DB
from wz_core.pupils import Pupils, PupilData

## First (official) day of school year
#    month1 = CONF.MISC.SCHOOLYEAR_MONTH_1.nat (1, 12)
#    year1 = schoolyear if month1 == 1 else schoolyear - 1
#    date0 = '{:04d}-{:02d}-01'.format (year1, month1)

def migratePupils (schoolyear):
    """Read the pupil data from the previous year and build a preliminary
    database table for the current (new) year, migrating the class
    names according to <CONF.MISC.MIGRATE_CLASS>
    """
    # Get pupil data from previous year
    pdb = Pupils (schoolyear-1)
    # Maximum year number for various streams:
    maxyear = {}
    try:
        for x in CONF.MISC.STREAM_MAX_YEAR:
            k, v = x.split (':')
            maxyear [k] = v
    except:
        REPORT.Fail (_BAD_STREAM_MAX_YEAR, val=x)
    rows = []
    for c_old in pdb.classes ():
        # Increment the year part of the class name
        try:
            cnum = int (c_old [:2]) + 1
            ctag = c_old [2:]
        except:
            REPORT.Fail (_BADCLASSNAME, klass=c_old)
        c_new = '%02d%s' % (cnum, ctag)
        for prow in pdb.classPupils (c_old):
            left = False
            if prow ['EXIT_D']:
                # If there is an exit date, assume the pupil has left.
                left = True

            else:
                try:
                    mxy = maxyear [prow ['STREAM']]
                except:
                    mxy = maxyear ['']
                if cnum > int (mxy):
                    left = True

            if left:
                REPORT.Info (_PUPIL_LEFT, klass=c_old, name=prow.name ())
                continue

            prow ['CLASS'] = c_new
            rows.append (prow)

    # Create the database table PUPILS from the loaded pupil data.
    db = DB (schoolyear, flag='CANCREATE')
    # Use (CLASS, PSORT) as primary key, with additional index on PID.
    # This makes quite a small db (without rowid).
    db.makeTable2 ('PUPILS', PupilData.fields (), data=rows,
            force=True,
            pk=('CLASS', 'PSORT'), index=('PID',))




def test_01 ():
    schoolyear = 2017
    REPORT.PRINT ("Pupil table created:", migratePupils (schoolyear))
