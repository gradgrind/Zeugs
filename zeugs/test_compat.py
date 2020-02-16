#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_compat.py

Last updated:  2020-02-16
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_compat import migrate
    runTests (migrate)

    from wz_compat import config
    runTests (config)

    from wz_compat import grade_classes
    runTests (grade_classes)

    from wz_compat import gradefunctions
    runTests (gradefunctions)
