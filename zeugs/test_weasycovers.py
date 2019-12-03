#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_weasycovers.py

Last updated:  2019-12-03
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

#    from wz_text import print_covers
#    runTests (print_covers)
    from wz_text import print_covers_j
    runTests (print_covers_j)
