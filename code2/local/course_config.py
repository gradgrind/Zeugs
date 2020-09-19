### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/course_config.py

Last updated:  2020-09-15

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
    'GRP'       : 'Gruppe',
    'GRADE'     : 'Note'
}

DB_TABLES['SUBJECT'] = SUBJECT_FIELDS
DB_TABLES['__INDEX__']['SUBJECT'] = ('SID',)
DB_TABLES['CLASS_SUBJECT'] = CLASS_SUBJECT_FIELDS
DB_TABLES['__UNIQUE__']['CLASS_SUBJECT'] = (('CLASS', 'SID'),)
