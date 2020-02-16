#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
update_pupils.py

Last updated:  2020-02-16
"""

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

    from wz_compat import import_pupils
    runTests (import_pupils)



    quit(0)
    from wz_compat.import_pupils import importLatestRaw
    rpd = importLatestRaw (2020)
#    for klass in sorted (rpd):
#        REPORT.Test ("\n +++ Class %s" % klass)
#        for row in rpd [klass]:
#            REPORT.Test ("   --- %s" % repr (row))
    REPORT.printMessages ()
