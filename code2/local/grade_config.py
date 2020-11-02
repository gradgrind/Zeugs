### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/grade_config.py

Last updated:  2020-11-02

Configuration for grade handling.
====================================
"""

### Messages
_BAD_GRADE = "Ungültige \"Note\" im Fach {sid}: {g}"

_INVALID_GRADE = "Ungültige \"Note\": {grade}"
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

# Streams/levels
STREAMS = {
    'Gym': 'Gymnasium',
    'RS': 'Realschule',
    'HS': 'Hauptschule',
#TODO:
#    'FS': 'Förderschule',
#    'GS': 'Grundschule'
}


# Localized field names.
# This also determines the fields for the GRADES table.
GRADES_FIELDS = {
    'PID'       : 'ID',
    'CLASS'     : 'Klasse',
    'STREAM'    : 'Maßstab',    # Grading level, etc.
    'TERM'      : 'Anlass',     # Term/Category
    'GRADES'    : 'Noten',
    'REPORT_TYPE': 'Zeugnistyp',
    'ISSUE_D'   : 'Ausstellungsdatum',
    'GRADES_D'  : 'Notenkonferenz',
    'QUALI'     : 'Qualifikation',
    'COMMENT'   : 'Bemerkungen'
}
#
DB_TABLES['GRADES'] = GRADES_FIELDS
DB_TABLES['__INDEX__']['GRADES'] = (('PID', 'TERM'),)


class GradeConfigError(Exception):
    pass

class GradeError(Exception):
    pass

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


### Grade handling
class GradeBase:
    """The base class for grade handling. It provides information
    specific to the locality. A subclass handles the set of
    grades for a particular report for a pupil in a more general way.
    """
    _CATEGORIES = (
        # term/category-tag, text version, relative path to files
        ('1', '1. Halbjahr', 'NOTEN/HJ1'),
        ('2', '2. Halbjahr', 'NOTEN/HJ2'),
        ('A', 'Abitur', 'NOTEN/Abitur'),
        ('S', 'Einzelzeugnisse', 'NOTEN/Einzel')
    )
    _GROUP_STREAMS = { # The classes which are divided into groups for
        # grade reports. This maps the groups to the pupils' streams.
        # { class -> { group -> (stream, ...)}}
        '12': {'G': ('Gym',), 'R': ('RS', 'HS')},
        '11': {'G': ('Gym',), 'R': ('RS', 'HS')}
    }
    _REPORT_GROUPS = { # Groups for which scheduled reports are to be
        # prepared. Mapped from school term. Also the default report type
        # is given.
        '1': (
            ('13', 'Zeugnis'),
            ('12.G', 'Zeugnis'),
            ('12.R', 'Zeugnis'),
            ('11.G', 'Orientierung'),
            ('11.R', 'Orientierung')
        ),
        '2': (
            ('12.G', 'Zeugnis'),
            ('12.R', 'Abschluss'),
            ('11.G', 'Zeugnis'),
            ('11.R', 'Zeugnis'),
            ('10', 'Orientierung')
        )
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
#
    @classmethod
    def group2klass_streams(cls, group):
        """Return the class and a list (tuple) of streams for the given
        pupil group. Only those groups relevant for grade reports are
        acceptable.
        """
        try:
            klass, g = group.split('.', 1)
        except ValueError:
            # Whole class
            return (group, ())
        try:
            return (klass, cls._GROUP_STREAMS[klass][g])
        except KeyError as e:
            raise GradeConfigError(_BAD_GROUP.format(group = group)) from e
#
    @classmethod
    def stream_in_group(cls, klass, stream, grouptag):
        """Return <True> if the stream is in the group. <grouptag> is
        just the group part of a group name (e.g. R for 12.R).
        <grouptag> may also be '*', indicating the whole class (i.e.
        all streams).
        """
        if grouptag == '*':
            return True
        try:
            return stream in cls._GROUP_STREAMS[klass][grouptag]
        except KeyError as e:
            raise GradeConfigError(_BAD_GROUP.format(
                    group = klass + '.' + grouptag)) from e
#
    @classmethod
    def grade_group(cls, klass, stream):
        """This is needed because the grades in general, and in particular
        the templates, are dependant on the grade groups.
        Return the group containing the given stream.
        """
        try:
            for g, streams in cls._GROUP_STREAMS[klass].items():
                if s in streams:
                    return klass + '.' + g
        except KeyError:
            return klass
#
    def __init__(self, grade_row):
        klass, stream = grade_row['CLASS'], grade_row['STREAM']
        self.i_grade = {}
        if klass >= '12' and stream == 'Gym':
            self.valid_grades = self._ABITUR_GRADES
            self.isAbitur = True
        else:
            self.valid_grades = self._NORMAL_GRADES
            self.isAbitur = False
#
    def filter_grade(self, sid, g):
        """Return the possibly filtered grade <g> for the subject <sid>.
        Integer values are stored additionally in the mapping
        <self.i_grade> (only for subjects with numerical grades).
        """
        # There can be normal, empty, non-numeric and badly-formed grades
        if g:
            if g not in self.valid_grades:
                raise GradeError(_BAD_GRADE.format(sid = sid, g = g))
            # Separate out numeric grades, ignoring '+' and '-'.
            # This can also be used for the Abitur scale, though the
            # stripping is superfluous.
            try:
                self.i_grade[sid] = int(g.rstrip('+-'))
            except ValueError:
                pass
        else:
            g = ''  # ensure that the grade is a <str>
        self._grades[sid] = g

#?
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
        """Return list of tuples: (term tag, term name).
        """
        return [(cat[0], cat[1]) for cat in cls._CATEGORIES]

    @classmethod
    def grade_path(cls, term):
        for cat in cls._CATEGORIES:
            if cat[0] == term:
                return cat[2]
        raise Bug("Bad category/type: %s" % term)

################################################################

#NODATE = "00.00.0000"

#
# The subjects may be collected in groups. These groups may vary from
# class to class – especially in Sek II!
#ORDERING_GROUPS = {
#    '13':       ['E', 'G'],
#    '12.Gym':   ['A', 'B', 'C', 'D', 'X'],
#    '*':        ['S', 'K']
#}
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
#EXTRA_FIELDS = {
#    '13':     [],
#    '12.Gym':   ['V13'],
#    '12.RS':     ['*AVE', '*DEM', 'Q12', 'GS'],
#    '12.HS':     ['*AVE', '*DEM', 'Q12', 'GS'],
#    '11.Gym':   ['*AVE', 'V', 'GS'],
#    '11.RS':     ['*AVE', '*DEM', 'GS'],
#    '11.HS':     ['*AVE', '*DEM', 'GS'],
#    '10':     ['*AVE', '*DEM', 'GS']
#}
#
#EXTRA_FIELDS_TAGS = {
## Associate the evaluation field tags with full names.
#    'AVE':  'Φ Alle Fächer',
#    'DEM':  'Φ De-En-Ma',
#    'GS':   'Gleichstellungsvermerk',
#    'V':    'Versetzung (Quali)',
#    'Q12':  'Abschluss 12. Kl',
#    'V13':  'Versetzung (13. Kl.)'
#}

###

# -> method of grade manager?
#def print_level(report_type, quali, klass, stream):
#    """Return the subtitle of the report, the grading level.
#    """
#    if report_type == 'Abschluss':
#        if not quali:
#            raise GradeConfigError(_NO_QUALIFICATION)
#        if quali == 'Erw' and klass[:2] != '12':
#            # 'Erw' is only available in class 12
#            quali = 'RS'
#        return {
#            'Erw': 'Erweiterter Sekundarabschluss I',
#            'RS': 'Sekundarabschluss I – Realschulabschluss',
#            'HS': 'Sekundarabschluss I – Hauptschulabschluss'
#        }[quali]
#    return 'Maßstab %s' % STREAMS[stream]
#
#def print_title(report_type):
#    """Return the title of the report.
#    """
#    return REPORT_TYPES[report_type]
#
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
#def cs_split(class_stream):
#    c_s = class_stream.split(':')
#    if len(c_s) == 1:
#        return (class_stream, None)
#    elif len(c_s) == 2:
#        return c_s
#    raise Bug("BUG: Bad class_stream: %s" % class_stream)
##
#def cs_join(klass, stream = None):
#    if stream:
#        return klass + ':' + stream
#    return klass
########

