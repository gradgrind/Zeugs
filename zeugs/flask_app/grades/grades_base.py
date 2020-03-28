### python >= 3.7
# -*- coding: utf-8 -*-

"""
flask_app/grades/grades_base.py

Last updated:  2020-03-28

Base module for the grades "Blueprint"

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

_HEADING = "Notenzeugnis"   # page heading


import datetime, os

from wz_grades.gradedata import CurrentTerm

from flask import Blueprint, session


# Set up Blueprint
_BPNAME = 'bp_grades'
bp = Blueprint(_BPNAME,             # internal name of the Blueprint
        __name__)                   # allows the current package to be found


#DEPRECATED?
def getCurrentTerm():
    """Return the current term ('1' or '2') if it lies in the session
    year, otherwise <None>.
    """
    schoolyear = session['year']
    try:
        curterm = CurrentTerm(schoolyear)
        return curterm.TERM
    except CurrentTerm.NoTerm:
        # The current term is not in this year
        return None
