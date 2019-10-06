#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_xsubjects.py

Last updated:  2019-10-05
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_grades import gradeprocessing
    runTests (gradeprocessing)
