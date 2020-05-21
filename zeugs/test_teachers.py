### python >= 3.7
# -*- coding: utf-8 -*-

"""
test_teachers.py

Last updated:  2020-05-21
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_core import teachers
    runTests (teachers)
