# python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_grades/makeabi.py

Last updated:  2020-02-07

Generate final grade reports for the Abitur.

Fields in the template file are replaced by the report information.

The template has grouped and numbered slots for subject names
and the corresponding grades.

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

#TODO: Where this differs from other grade reports:
# - special calculations
# - must determine which subjects are relevant for each pupil
# - not really term-based? Maybe a special entry in the term field ("ABI")
# - "Datum der Feststellung des Prüfungsergebnisses", so maybe rather individually
# ...

_INVALID_YEAR = "Ungültiges Schuljahr in Tabelle: '{val}'"
_WRONG_YEAR = "Falsches Schuljahr in Tabelle: '{year}'"
_INVALID_KLASS = "Ungültige Klasse in Tabelle: {klass}"
_MISSING_PUPIL = "In Kurswahltabelle: keine Zeile für {pname}"
_UNKNOWN_PUPIL = "In Notentabelle: unbekannte Schüler-ID – {pid}"


import os

from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

from wz_core.configuration import Paths#, Dates
from wz_core.pupils import Pupils, Klass
#from wz_core.db import DB
#?
from wz_grades.gradedata import (GradeReportData,
        db2grades, getGradeData, updateGradeReport)







############### TEST functions ###############
_testyear = 2016
def test_01():
