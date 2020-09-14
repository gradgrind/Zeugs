### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/grade_config.py

Last updated:  2020-09-13

Configuration for grade handling.
====================================
"""

#from core.base import Dates


class GradeConfigError(Exception):
    pass
#
STREAMS = {
    'Gym': 'Gymnasium',
    'RS': 'Realschule',
    'HS': 'Hauptschule'
}
#
REPORT_TYPES = {
    'Orientierung': 'Orientierungsnoten',
    'Zeugnis':      'Zeugnis',
    'Abgang':       'Abgangszeugnis',
    'Abschluss':    'Abschlusszeugnis',
    'Zwischen':     'Zwischenzeugnis'
}
#
# Localized field names. This also determines the fields for the GRADES
# table.
GRADES_FIELDS = {
    'PID'       : 'ID',
    'CLASS'     : 'Klasse',
    'STREAM'    : 'Maßstab',
    'TERM'      : 'Halbjahr',
    'GRADES'    : 'Noten',
    'REPORT_TYPE': 'Zeugnistyp',
    'ISSUE_D'   : 'Ausstellungsdatum',
    'GRADES_D'  : 'Notenkonferenz',
    'COMMENTS'  : 'Bemerkungen'
}   # Index : ('PID', 'TERM')
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
# The subjects may be collected in groups. These groups may vary from
# class to class – especially in Sek II!
ORDERING_GROUPS = {
    '13':       ['E', 'G'],
    '12.Gym':   ['A', 'B', 'C', 'D', 'X'],
    '*':        ['S', 'K']
}
#
##### Here the subjects are listed in the groups referred to by
##### <ORDERING_GROUPS>:
SUBJECT_GROUPS = {
## Abitur class 12
    'A': ['De', 'En', 'Fr', 'Ku', 'Mu'],
    'B': ['Ges', 'Geo', 'Soz', 'Rel'],
    'C': ['Ma', 'Bio', 'Ch', 'Ph'],
    'D': ['Sp', 'Eu'],
    'X': ['Kge', 'Mal', 'Sth']
## Abitur class 13
# eA
    'E': ['De.e', 'En.e', 'Ges.e', 'Bio.e'],
# gA
    'G': ['Ma.g', 'En.m', 'Fr.m', 'Bio.m', 'Ku.m', 'Mu.m', 'Sp.m']
## Sek-I
# Versetzungsrelevant
    'S': ['De', 'En', 'Fr', 'Ku', 'Mu', 'Ges', 'Soz', 'Geo', 'Rel',
        'Ma', 'Bio', 'Ch', 'Ph', 'AWT', 'Sp']
# Künstlerisch-praktisch
    'K': ['Eu', 'Bb', 'Kge', 'Ktr', 'Mal', 'MZ', 'Pls', 'Snt', 'Sth', 'Web']
}
#
# Additional fields for grade "evaluation". Some are for the grade tables
# for display/inspection purposes, some determine details of the grade
# reports – qualifications, etc.
#TODO: This still needs some work ... e.g. What are the '*'s for?!
EXTRA_FIELDS = {
    '13':     [],
    '12.Gym':   ['V13'],
    '12.RS':     ['*AVE', '*DEM', 'Q12', 'GS'],
    '12.HS':     ['*AVE', '*DEM', 'Q12', 'GS'],
    '11.Gym':   ['*AVE', 'V', 'GS'],
    '11.RS':     ['*AVE', '*DEM', 'GS'],
    '11.HS':     ['*AVE', '*DEM', 'GS'],
    '10':     ['*AVE', '*DEM', 'GS']
}
#
EXTRA_FIELDS_TAGS = {
# Associate the evaluation field tags with full names.
    'AVE':  'Φ Alle Fächer',
    'DEM':  'Φ De-En-Ma',
    'GS':   'Gleichstellungsvermerk',
    'V':    'Versetzung (Quali)',
    'Q12':  'Abschluss 12. Kl',
    'V13':  'Versetzung (13. Kl.)'
}

###

def print_level(report_type, quali, stream):
    """Return the subtitle of the report, the grading level.
    """
#TODO?
    if quali:
        if report_type == 'Abschluss':
            return {
                'Erw': 'Erweiterter Sekundarabschluss I',
                'RS': 'Sekundarabschluss I – Realschulabschluss',
                'HS': 'Sekundarabschluss I – Hauptschulabschluss'
            }[quali]
    return 'Maßstab %s' % STREAMS[stream]
#
def print_title(report_type):
    """Return the title of the report.
    """
    return REPORT_TYPES[report_type]
#
def print_year(class_stream):
    """Return the "year" of the given class/group.
    """
    return int(class_stream[:2])

#TODO: Try to use the table fields in the templates directly!
#def getPupilData(pdata):
#    return {
#            'P.VORNAMEN': pdata['FIRSTNAMES'],
#            'P.NACHNAME': pdata['LASTNAME'],
#            'P.G.DAT': Dates.date_conv(pdata['DOB_D'] or NODATE, trap = False),
#            'P.G.ORT': pdata['POB'],
#            'P.E.DAT': Dates.date_conv(pdata['ENTRY_D'] or NODATE, trap = False),
#            'P.X.DAT': Dates.date_conv(pdata['EXIT_D'] or NODATE, trap = False),
#        # These are for SekII:
#            'P.HOME': pdata['HOME'],
#            'P.Q.DAT': Dates.date_conv(pdata['QUALI_D'] or NODATE, trap = False)
#        }
