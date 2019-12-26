#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/grades.py

Last updated:  2019-12-24

Functions for grade-report handling for a particular location.


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

#TODO: Perhaps class 13 should be completely separate?
#TODO: Perhaps this data should be in a conf. file?

GRADE_TEMPLATES = {
    '1': [
        ('13.Gym', 'Zeugnis', 'Notenzeugnis-13.html'),
        ('12.Gym', 'Zeugnis', 'Notenzeugnis-12_SII.html'),
        ('12.*', 'Zeugnis', 'Notenzeugnis-SI.html'),
        ('11.*', 'Zeugnis', 'Notenzeugnis-SI.html')
    ],

    '2': [
        ('13.Gym', 'Abschluss', 'Abitur.html'),
        ('12.Gym', 'Zeugnis', 'Notenzeugnis-12_SII.html'),
        ('12.*', 'Abschluss', 'Notenzeugnis-SI.html'),
        ('11.*', 'Zeugnis', 'Notenzeugnis-SI.html'),
        ('10.*', 'Orientierung', 'Orientierung.html')
    ],

    'leaving': [
        ('13.Gym', 'Abgang', 'Abgang-13.html'),
        ('12.Gym', 'Abgang', 'Notenzeugnis-12_SII.html'),
        ('05<*', 'Abgang', 'Notenzeugnis-SI.html')
    ],

    'normal': [
        ('11<*', None, None),
        ('05<*', 'Zwischenzeugnis', 'Notenzeugnis-SI.html')
    ]
}

########################################################################
from fnmatch import fnmatchcase

from wz_core.pupils import Pupils


def findmatching(klass, kmap):
    """Find the first matching entry for the "klass" in the mapping list.
    """
    for k, rtag, template in kmap:
        try:
            kmin, k = k.split('<')
        except:
            kmin = '00'
        if fnmatchcase(klass, k):
            if klass >= kmin:
                return (rtag, template) if rtag else None
    return None


#TODO: superfluous?
def findallmatching(schoolyear, rtype):
    """Find all "klasses" available for this report type.
    """
    try:
        kmap = GRADE_TEMPLATES[rtype]
    except:
        return None
    klist = []
    p = Pupils(schoolyear)
    for c in p.classes():
        for s in p.streams(c):
            if findmatching(c + '.' + s, kmap):
                klist.append(c)
                break
    return klist



##################### Test functions
_testyear = 2020
def test_01 ():
    REPORT.Test("Grade report type -> available classes")
    for rtype in GRADE_TEMPLATES:
        REPORT.Test("  %s -> %s" % (rtype, findallmatching(_testyear, rtype)))
