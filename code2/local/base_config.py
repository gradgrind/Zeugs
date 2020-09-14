### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/base_config.py

Last updated:  2020-09-13

General configuration items.
============================
"""

# First month of school year (Jan -> 1, Dec -> 12):
SCHOOLYEAR_MONTH_1 = 8
# Format for printed dates (as used by <datetime.datetime.strftime>):
DATEFORMAT = '%d.%m.%Y'

def print_schoolyear(schoolyear):
    """Convert a school-year (<int>) to the format used for output
    """
    return '%d – %d' % (schoolyear-1, schoolyear)



