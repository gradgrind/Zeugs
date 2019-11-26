#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_spimport.py

Last updated:  2019-10-23
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_compat import sptable
    runTests (sptable)
