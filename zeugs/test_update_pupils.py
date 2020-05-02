#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
update_pupils.py

Last updated:  2020-05-02
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit()

    from wz_compat import import_pupils
    runTests(import_pupils)
