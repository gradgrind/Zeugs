### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/grade_config.py

Last updated:  2020-09-05

Configuration for grade handling.
====================================
"""

from core.base import Dates


# Localized field names. This also determines the fields for the GRADES
# table.
GRADES_FIELDS = {
    'PID'       : 'ID',
    'CLASS'     : 'Klasse',
    'STREAM'    : 'Maßstab',
    'TERM'      : 'Halbjahr',
    'GRADES'    : 'Noten'
}   # Index : ('PID', 'TERM')


class GradeConfigError(Exception):
    pass
#
GRADE_REPORT_TERM = {
    # Valid types for term and class.
    # The first entry in each list is the default.
    '1': {
        '11': [
                ('Orientierung', 'Orientierungsnoten'),
                ('Abgang', 'Notenzeugnis-SI')
            ],
        '12.Gym': [
                ('Zeugnis', 'Notenzeugnis-SII'),
                ('Abgang', 'Notenzeugnis-SII')
# An exit from class 12.Gym before the report for the first half year
# can be a problem if there are no grades yet. Perhaps those from
# class 11 could be converted (manually)?
            ],
        '12.RS': [
                ('Zeugnis', 'Notenzeugnis-SI'),
                ('Abgang', 'Notenzeugnis-SI')
            ],
        '12.HS': [
                ('Zeugnis', 'Notenzeugnis-SI'),
                ('Abgang', 'Notenzeugnis-SI')
            ]
        },
#
    '2': {
        '10': [
                ('Orientierung', 'Orientierungsnoten'),
                ('Abgang', 'Notenzeugnis-SI')
            ],
        '11': [
                ('Zeugnis', 'Notenzeugnis-SI'),
                ('Abgang', 'Notenzeugnis-SI')
            ],
        '12.Gym': [
                ('Zeugnis', 'Notenzeugnis-SII'),
                ('Abgang', 'Notenzeugnis-SII')
            ],
        '12.RS': [
                ('Abschluss', 'Notenzeugnis-SI'),
                ('Zeugnis', 'Notenzeugnis-SI'),
                ('Abgang', 'Notenzeugnis-SI')
            ],
        '12.HS': [
                ('Abschluss', 'Notenzeugnis-SI'),
                ('Zeugnis', 'Notenzeugnis-SI'),
                ('Abgang', 'Notenzeugnis-SI')
            ]
        }
    }
#
GRADE_REPORT_ANYTIME = {
    # ... any class, any time
    '12.Gym': [
            ('Abgang', 'Notenzeugnis-SII'),
            ('Zwischen', 'Notenzeugnis-SII')
        ],
    '*': [
            ('Abgang', 'Notenzeugnis-SI'),
            ('Zwischen', 'Notenzeugnis-SI')
        ]
    }
#
NODATE = "00.00.0000"
#
def getPupilData(pdata):
    return {
            'P.VORNAMEN': pdata['FIRSTNAMES'],
            'P.NACHNAME': pdata['LASTNAME'],
            'P.G.DAT': Dates.date_conv(pdata['DOB_D'] or NODATE, trap = False),
            'P.G.ORT': pdata['POB'],
            'P.E.DAT': Dates.date_conv(pdata['ENTRY_D'] or NODATE, trap = False),
            'P.X.DAT': Dates.date_conv(pdata['EXIT_D'] or NODATE, trap = False),
        # These are for SekII:
            'P.HOME': pdata['HOME'],
            'P.Q.DAT': Dates.date_conv(pdata['QUALI_D'] or NODATE, trap = False)
        }
