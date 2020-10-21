### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/grade_config.py

Last updated:  2020-10-21

Configuration for grade handling.
====================================
"""

### Messages
_INVALID_GRADE = "Ungültige Note: {grade}"
_BAD_GROUP = "Ungültige Schülergruppe: {group}"
_NO_QUALIFICATION = "Kein Abschluss erreicht"

# Special "grades"
UNCHOSEN = '/'
NO_GRADE = '*'
MISSING_GRADE = '?'
NO_SUBJECT = '––––––––––'   # entry in grade report for excess subject slot

# GRADE field in CLASS_SUBJECTS table
NULL_COMPOSITE = '/'
NOT_GRADED = '-'

# Streams for higher classes
ALL_STREAMS = '*'
STREAMS = {
    'Gym': 'Gymnasium',
    'RS': 'Realschule',
    'HS': 'Hauptschule',
#TODO:
    'FS': 'Förderschule',
    'GS': 'Grundschule'
}
#


def all_streams(klass):
    """Return a list of streams available in the given class.
    """
#TODO: Only some of the classes have been properly considered here ...
    try:
        c = int(klass)
        if c == 13:
            return ['Gym']
        if c >= 10:
            return ['Gym', 'RS', 'HS']  # 'HS' only for "Abgänger"
        elif c >= 5:
            return ['Gym', 'RS']
        else:
            return ['GS']
    except:
#TODO ...
        # Förderklasse?
        c = int(klass[:2])
        if c >= 5:
            return ['HS', 'FS']
        return ['GS']
#

### Grade handling
class GradeValues:
    _CATEGORIES = (
        ('1', '1. Halbjahr'),
        ('2', '2.Halbjahr'),
        ('A', 'Abitur'),
        ('S', 'Sonderzeugnisse')
    )
    _GROUPS = { # Classes which are split for grade reports.
        # The internal mappings give the streams covered by the groups.
        # { class -> { group -> (stream, ...)}}
        '12': {'G': ('Gym',), 'R': ('RS', 'HS')}
    }
    _NORMAL_GRADES = (
        '1+', '1', '1-',
        '2+', '2', '2-',
        '3+', '3', '3-',
        '4+', '4', '4-',
        '5+', '5', '5-',
        '6',
        '*',    # ("no grade" ->) "––––––"
        'nt',   # "nicht teilgenommen"
        't',    # "teilgenommen"
        'nb',   # "kann nich beurteilt werden"
        #'ne',   # "nicht erteilt"
        UNCHOSEN # Subject not included in report
    )
    _ABITUR_GRADES = ( # class 12 and 13, 'Gym'
        '15', '14', '13',
        '12', '11', '10',
        '09', '08', '07',
        '06', '05', '04',
        '03', '02', '01',
        '00',
        '*', 'nt', 't', 'nb', #'ne',
        UNCHOSEN
    )
    _PRINT_GRADE = {
        '1': "sehr gut",
        '2': "gut",
        '3': "befriedigend",
        '4': "ausreichend",
        '5': "mangelhaft",
        '6': "ungenügend",
        '*': "––––––",
        'nt': "nicht teilgenommen",
        't': "teilgenommen",
#            'ne': "nicht erteilt",
        'nb': "kann nicht beurteilt werden",
    }
    def setGroup(self, group):
        self.group = group
        self.streams = None
        try:
            self.klass, g = group.split('.', 1)
        except ValueError:
            self.klass, g = group, None
        else:
            try:
                gmap = self._GROUPS[self.klass]
            except KeyError:
                pass
            else:
                try:
                    self.streams = gmap[g]
                except KeyError as e:
                    raise GradeConfigError(_BAD_GROUP.format(group = group))
        if group in ('13', '12.G'):
            self.valid_grades = self._ABITUR_GRADES
            self.isAbitur = True
        else:
            self.valid_grades = self._NORMAL_GRADES
            self.isAbitur = False

    def printGrade(self, grade):
        """Fetch the grade for the given subject id and return the
        string representation required for the reports.
        The SekII forms have no space for longer remarks, but the
        special "grades" are retained for "Notenkonferenzen".
        """
        try:
            if self.isAbitur:
                if grade in self.valid_grades:
                    try:
                        int(grade)
                        return grade
                    except:
                        if grade == UNCHOSEN:
                            raise
                        return "––––––"
            else:
                return self._PRINT_GRADE[grade.rstrip('+-')]
        except:
            pass
        if grade:
            raise GradeConfigError(_INVALID_GRADE.format(
                    grade = repr(grade)))
        # No grade
        return '?'

    @classmethod
    def categories(cls):
        return cls._CATEGORIES

#
# Localized field names.
# This also determines the fields for the GRADES table.
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
}
#
DB_TABLES['GRADES'] = GRADES_FIELDS
DB_TABLES['__INDEX__']['GRADES'] = (('PID', 'TERM'),)

###

#TODO: change this so that only the default report type is given – the
# code for fetching the template checks other types against pupil groups,
# etc.
# Move the actual referencing of the templates to the template manager
# module – here just deal in types.
GRADE_REPORT_CATEGORY = {
    # Valid types for term/category and class/group.
#TODO: What about the template's parameter list (with descriptions?)
    '1': {
        '11': 'Orientierung',           #('Orientierung', 'Abgang'),
        '12.G': 'Zeugnis',              #('Zeugnis', 'Abgang'),
        '12.R': 'Zeugnis',              #('Zeugnis', 'Abgang'),
        '13': 'Zeugnis'                 #('Zeugnis', 'Abgang')
# "Abgang" in class 13 probably needs to be done manually because of
# the complexity of the form ...
        },
#
    '2': {
        '10': 'Orientierung',           #('Orientierung', 'Abgang'),
        '11': 'Zeugnis',                #('Zeugnis', 'Abgang'),
        '12.G': 'Zeugnis',              #('Zeugnis', 'Abgang'),
        '12.R': 'Abschluss'             #('Abschluss', 'Zeugnis', 'Abgang')
        },
#
    'A': 'Abitur',                      #('Abitur', 'Kein-Abitur', 'FHS-Reife'),
#
    'S': 'Abgang'                       #('Abgang', 'Zwischen')
# Types 'A' and 'S' should present not classes but a list of pupils.?
    }

# An exit from 12.G before the report for the first half year
# can be a problem if there are no grades yet. Perhaps those from
# class 11 could be converted (manually)?
#?
#    '10/Orientierung': ...
#    'date/Abgang/pid'
#    'date/Zwischen/pid'
#######
#TEMPLATES (*.odt):
#SekI:
# grades-Orientierung
# grades-SekI               // Zeugnis & Zwischen
# grades-SekI-Abgang      grades-SekI-AbgangHS
# grades-SekI-Abschluss     // HS & RS & Erw
#SekII:
# grades-SekII-12           grades-SekII-12-Abgang
# grades-SekII-13_1         abitur              grades-SekII-13-Abgang





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
# ALTERNATIVE:
# If term is not considered
GRADE_REPORT_TEMPLATE = {
    '13': [
        ('Zeugnis', 'Notenzeugnis-13'), # ?
        ('Abitur', 'Abitur'),           # ? Separate template for fail?
# FHS-Reife?
        ('Abgang', 'Abgang-13')         # ?
    ],
    '12:Gym': [
        ('Zeugnis', 'Notenzeugnis-SII'),
        ('Abgang', 'Notenzeugnis-SII')
    ],
    '12:RS': [
        ('Abschluss', 'Notenzeugnis-SI'),
        ('Zeugnis', 'Notenzeugnis-SI'),
        ('Abgang', 'Notenzeugnis-SI')
    ],
    '12:HS': [
        ('Abschluss', 'Notenzeugnis-SI'),
        ('Zeugnis', 'Notenzeugnis-SI'),
        ('Abgang', 'Notenzeugnis-SI')
    ],
    '*': [
        ('Zeugnis', 'Notenzeugnis-SI'),
        ('Orientierung', 'Orientierungsnoten'),
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
#SUBJECT_GROUPS = {
### Abitur class 12
#    'A': ['De', 'En', 'Fr', 'Ku', 'Mu'],
#    'B': ['Ges', 'Geo', 'Soz', 'Rel'],
#    'C': ['Ma', 'Bio', 'Ch', 'Ph'],
#    'D': ['Sp', 'Eu'],
#    'X': ['Kge', 'Mal', 'Sth'],
### Abitur class 13
## eA
#    'E': ['De.e', 'En.e', 'Ges.e', 'Bio.e'],
## gA
#    'G': ['Ma.g', 'En.m', 'Fr.m', 'Bio.m', 'Ku.m', 'Mu.m', 'Sp.m'],
### Sek-I
## Versetzungsrelevant
#    'S': ['De', 'En', 'Fr', 'Ku', 'Mu', 'Ges', 'Soz', 'Geo', 'Rel',
#        'Ma', 'Bio', 'Ch', 'Ph', 'AWT', 'Sp'],
## Künstlerisch-praktisch
#    'K': ['Eu', 'Bb', 'Kge', 'Ktr', 'Mal', 'MZ', 'Pls', 'Snt', 'Sth', 'Web']
#}
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

# -> method of grade manager?
def print_level(report_type, quali, klass, stream):
    """Return the subtitle of the report, the grading level.
    """
    if report_type == 'Abschluss':
        if not quali:
            raise GradeConfigError(_NO_QUALIFICATION)
        if quali == 'Erw' and klass[:2] != '12':
            # 'Erw' is only available in class 12
            quali = 'RS'
        return {
            'Erw': 'Erweiterter Sekundarabschluss I',
            'RS': 'Sekundarabschluss I – Realschulabschluss',
            'HS': 'Sekundarabschluss I – Hauptschulabschluss'
        }[quali]
    return 'Maßstab %s' % STREAMS[stream]
#
#def print_title(report_type):
#    """Return the title of the report.
#    """
#    return REPORT_TYPES[report_type]
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


######## Convert between class_stream and class + stream
def cs_split(class_stream):
    c_s = class_stream.split(':')
    if len(c_s) == 1:
        return (class_stream, None)
    elif len(c_s) == 2:
        return c_s
    raise Bug("BUG: Bad class_stream: %s" % class_stream)
#
def cs_join(klass, stream = None):
    if stream:
        return klass + ':' + stream
    return klass
########

class GradeConfigError(Exception):
    pass
