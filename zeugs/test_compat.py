#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_compat.py

Last updated:  2019-09-27
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

#    from wz_compat import migrate
#    runTests (migrate)

#    from wz_compat import import_pupils
#    runTests (import_pupils)

    from wz_compat import config
    runTests (config)

    from wz_compat import grades
    runTests (grades)
