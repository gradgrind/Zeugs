#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_templates.py

Last updated:  2020-03-09
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_compat import template
    runTests (template)
