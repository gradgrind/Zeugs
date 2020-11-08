### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/base_config.py

Last updated:  2020-11-08

General configuration items.
============================
"""

SCHOOL_NAME = 'Freie Michaelschule'

DECIMAL_SEP = ','

# First month of school year (Jan -> 1, Dec -> 12):
SCHOOLYEAR_MONTH_1 = 8
# Format for printed dates (as used by <datetime.datetime.strftime>):
DATEFORMAT = '%d.%m.%Y'

#TODO: Maybe rather in db? Both?
CALENDAR_FILE = 'Kalender'

# Localized field names.
# This also determines the fields for the INFO table.
INFO_FIELDS = {
    'K'         : 'Element',
    'V'         : 'Wert'
}
#
DB_TABLES['INFO'] = INFO_FIELDS
DB_TABLES['__INDEX__']['INFO'] = ('K',)

def print_schoolyear(schoolyear):
    """Convert a school-year (<int>) to the format used for output
    """
    return '%d – %d' % (schoolyear-1, schoolyear)

def class_year(klass):
    """Get just the year part of a class name.
    """
    try:
        return int(klass[:2])
    except:
        return int(klass[0])
