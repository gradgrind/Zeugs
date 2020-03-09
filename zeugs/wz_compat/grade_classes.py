# python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/grade_classes.py

Last updated:  2020-03-08

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

_INVALID_GROUP = "Ungültige Zeugnis-Gruppe für das {term}. Halbjahr: {group}"


from wz_core.db import DB
from wz_core.pupils import Klass


def gradeGroups(term):
    return g2groups[term]

g2groups = {
# Use <Klass> to normalise multi-stream groups
## 1. Halbjahr
    "1": [str(Klass(k)) for k in
            ("13", "12.Gym", "12.RS-HS", "11.Gym", "11.RS-HS")],

## 2. Halbjahr
    "2": [str(Klass(k)) for k in
            ("13", "12.Gym", "12.RS-HS", "11.Gym", "11.RS-HS", "10")],

## Einzelzeugnisse: alle Großklassen ab der 5.
    "X": ["%02d" % n for n in range(13, 4, -1)]
}


def setDateOfIssue(schoolyear, term, klass, date):
    if str(klass) not in gradeGroups(term):
        REPORT.Fail(_INVALID_GROUP, term = term, group = klass)
    streams = klass.streams or klass.klassStreams(schoolyear)
    for s in streams:
        g = klass.klass + '.' + s
        DB(schoolyear).setInfo('GRADE_DATE_%s_%s' % (term, g), date)


def getDateOfIssue(schoolyear, term, klass):
    db = DB(schoolyear)
    if klass.stream:
        return db.getInfo('GRADE_DATE_%s_%s' % (term, klass))
    group = str(klass)
    if group in gradeGroups(term):
        if klass.streams:
            return db.getInfo('GRADE_DATE_%s_%s' % (term,
                    klass.klass + '.' + klass.streams[0]))
        return db.getInfo('GRADE_DATE_%s_%s' % (term,
                    klass.klass + '.' + klass.klassStreams(schoolyear)[0]))
    REPORT.Fail(_INVALID_GROUP, term = term, group = group)



##################### Test functions
def test_01 ():
    for key in g2groups:
        REPORT.Test("\n Term %s: %s" % (key, repr(gradeGroups(key))))
