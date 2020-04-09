#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_db.py

Last updated:  2020-04-08
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_core import db
    runTests (db)
