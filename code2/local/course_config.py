### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/course_config.py

Last updated:  2020-10-08

Configuration for course-data handling.
======================================
"""

# Localized field names. This also determines the fields for the
# CLASS_SUBJECT table.
CLASS_SUBJECT_FIELDS = {
    'CLASS'     : 'Klasse',
    'SID'       : 'Kürzel',
    'SUBJECT'   : 'Fach',
    'TIDS'      : 'Lehrkräfte',
    'GRP'       : 'Gruppe',
    'GRADE'     : 'Note'
}

DB_TABLES['CLASS_SUBJECT'] = CLASS_SUBJECT_FIELDS
DB_TABLES['__UNIQUE__']['CLASS_SUBJECT'] = (('CLASS', 'SID'),)
