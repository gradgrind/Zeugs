#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_weasycovers.py

Last updated:  2019-12-04
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_text import coversheet
    runTests (coversheet)
