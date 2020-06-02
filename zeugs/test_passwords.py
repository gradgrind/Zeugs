### python >= 3.7
# -*- coding: utf-8 -*-

"""
test_passwords.py

Last updated:  2020-06-02
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit()

    from wz_compat import passwords
    runTests(passwords)
