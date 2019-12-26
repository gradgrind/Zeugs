#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_spimport.py

Last updated:  2019-12-19
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_text import summary
    runTests (summary)
