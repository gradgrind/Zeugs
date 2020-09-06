### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/course_config.py

Last updated:  2020-09-05

Configuration for course-data handling.
======================================
"""

# Localized field names. This also determines the fields for the SUBJECT
# table.
SUBJECT_FIELDS = {
    'SID'       : 'Kürzel',
    'SUBJECT'   : 'Fach'
}   # Index : SID

# Localized field names. This also determines the fields for the
# CLASS_SUBJECT table.
CLASS_SUBJECT_FIELDS = {
    'CLASS'     : 'Klasse',
    'SID'       : 'Kürzel',
    'TIDS'      : 'Lehrkräfte',
    'GROUP'     : 'Gruppe',
    'GRADE'     : 'Note'
}

