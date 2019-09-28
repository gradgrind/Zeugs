#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_core.py

Last updated:  2019-09-25

Run some tests on the modules in the wz_core package.


=+LICENCE=============================
Copyright 2019 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

=-LICENCE========================================
"""

import os, builtins

from wz_core.reporting import Report
from wz_core.configuration import init


def testinit ():
    appdir = os.path.dirname (os.path.realpath (__file__))
    userdir = os.path.join (os.path.dirname (appdir), 'DefaultData')
    print ("§§§ userdir:", userdir)
#    sys.path.append (appdir)

    builtins.REPORT = Report () # console output
    try:
        init (userdir)
    except RuntimeError as e:
        REPORT.printMessages ()
        quit (1)


def runTests (module):
    """Run the tests in the given module object.
    These are functions beginning "test_".
    """
    REPORT.Test ("\n <<<<<<<<<<<<<<< TESTING Module '%s' >>>>>>>>>>>>>>>"
            % module.__name__)
    for a in dir (module):
        if a.startswith ('test_'):
            fun = getattr (module, a)
            REPORT.Test ("\n-----> %s" % a)
            try:
                fun ()
            except RuntimeError as e:
                break
            finally:
                REPORT.printMessages ()


if __name__ == '__main__':
    testinit ()

    from wz_core import configuration
    runTests (configuration)

    from wz_core import pupils
    runTests (pupils)

    from wz_core import teachers
    runTests (teachers)

#    from wz_core import courses
#    runTests (courses)
