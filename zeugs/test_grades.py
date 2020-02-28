# python >= 3.7
# -*- coding: utf-8 -*-
"""
test_grades.py

Last updated:  2020-01-07

Run some tests on the modules in the wz_grades package.
The final Abitur grade handling is tested separately (test_abitur).


=+LICENCE=============================
Copyright 2019-2020 Michael Towers

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

from wz_core.reporting import Report
from test_core import testinit, runTests


if __name__ == '__main__':
    testinit ()

#    from wz_compat import grade_classes
#    runTests(grade_classes)

#    from wz_grades import gradedata
#    runTests (gradedata)

#    from wz_grades import makereports
#    runTests (makereports)

    from wz_grades import gradetable
    runTests (gradetable)
