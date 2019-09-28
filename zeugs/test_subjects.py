#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_subjects.py

Last updated:  2019-09-28
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_core import courses
    runTests (courses)
