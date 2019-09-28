#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_db.py

Last updated:  2019-07-13
"""

from wz_core.reporting import Report
from test_core import testinit, runTests

#TODO: Problem with namedtuple for rows – the fields may not start with '_'!

if __name__ == '__main__':
    testinit ()
    from wz_core.db import DB0

    db = DB0 ('test.sqlite3')

    print ("$TABLES:", db.tableNames ())

    with db._dbcon as con:
        cur = con.cursor ()
        cur.execute ('SELECT PID, STREAM FROM {}'.format ('PUPILS'))
        # Get (selected) field names:
        fields = [description [0] for description in cur.description]
        print ("$1", fields)
        print ("\n$2:", cur.fetchall ())

    print ("  ------------------------------")
    for row in db.getTable ('PUPILS'):
        print (" ---", row)
    print ("  ------------------------------")
    for row in db.select ('REPORTS', PID='200604'):
        print (" ---", row)
    print ("  ------------------------------")
    print (" ---", dict (db.select1 ('REPORTS', PID='200601', SID='de')))


    print ("\n  ================================")
