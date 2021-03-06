# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/grade_classes.py

Last updated:  2020-01-21

For which school-classes and streams are grade reports possible?


=+LICENCE=============================
Copyright 2020 Michael Towers

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


def gradeGroups(term):
    return g2groups[term]

g2groups = {
## 1. Halbjahr
    "1": ["13", "12.Gym", "12.RS-HS", "11.Gym", "11.RS-HS"],

## 2. Halbjahr
    "2": ["13", "12.Gym", "12.RS-HS", "11.Gym", "11.RS-HS", "10"],

## Einzelzeugnisse: alle Großklassen ab der 5.
    "X": ["%02d" % n for n in range(13, 4, -1)]
}


##################### Test functions
def test_01 ():
    for key in g2groups:
        REPORT.Test("\n Term %s: %s" % (key, repr(gradeGroups(key))))
