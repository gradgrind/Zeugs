### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/grade_config.py

Last updated:  2020-11-11

Configuration for grade handling.
====================================
"""

### Messages
_BAD_GRADE = "ERROR: Ungültige \"Note\" im Fach {sid}: {g}"
_BAD_TERM = "Ungültiger \"Anlass\" (Halbjahr): {term}"
_INVALID_GRADE = "Ungültige \"Note\": {grade}"
_BAD_GROUP = "Ungültige Schülergruppe: {group}"

# Special "grades"
UNCHOSEN = '/'
NO_GRADE = '*'
MISSING_GRADE = '?'
NO_SUBJECT = '––––––––––'   # entry in grade report for excess subject slot
UNGRADED = "––––––"         # entry in grade report, where there is no grade

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
#TODO: There is a problem with the unique index – category 'S*'! There
# can be multiple unscheduled reports ...
DB_TABLES['__INDEX__']['GRADES'] = (('PID', 'TERM'),)
# Add 'id' integer-primary-key, can aid updates
DB_TABLES['__PK__'].add('GRADES')


class GradeConfigError(Exception):
    pass

#class GradeError(Exception):
#    pass

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
        ('S*', 'Einzelzeugnisse', 'NOTEN/Einzel')
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
            ('13', None),      # Only for the grade table
            ('12.G', 'Zeugnis'),
            ('12.R', 'Abschluss'),
            ('11.G', 'Zeugnis'),
            ('11.R', 'Zeugnis'),
            ('10', 'Orientierung')
        ),
        'A': (
            ('13', 'Abitur'),
        )
    }
    GRADE_TABLES = { # without .xlsx suffix
        '*':        'grades/Noteneingabe',      # default
        '12.G':     'grades/Noteneingabe-SII',
        '13':       'grades/Noteneingabe-Abitur'
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
        '*': UNGRADED,
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
    def klass_stream2group(cls, klass, stream):
        """This is needed because the grades in general, and in particular
        the templates, are dependant on the grade groups.
        Return the group containing the given stream.
        """
        try:
            for g, streams in cls._GROUP_STREAMS[klass].items():
                if stream in streams:
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
            if g in self.valid_grades:
                # Separate out numeric grades, ignoring '+' and '-'.
                # This can also be used for the Abitur scale, though the
                # stripping is superfluous.
                try:
                    self.i_grade[sid] = int(g.rstrip('+-'))
                except ValueError:
                    pass
            else:
                REPORT(_BAD_GRADE.format(sid = sid, g = g))
                g = ''
        else:
            g = ''  # ensure that the grade is a <str>
        return g
#
    def grade_format(self, g):
        """Format the grade corresponding to the given numeric string.
        """
        return g.zfill(2) if self.isAbitur else g.zfill(1)
#
    def print_grade(self, grade):
        """Return the string representation of the grade which should
        appear in the report.
        If the grade is UNCHOSEN, return <None>.
        The SekII forms have no space for longer remarks, but the
        special "grades" are retained for "Notenkonferenzen".
        """
        if grade:
            if grade == UNCHOSEN:
                return None
        else:
            return MISSING_GRADE
        try:
            if self.isAbitur:
                if grade in self.valid_grades:
                    try:
                        int(grade)
                        return grade
                    except:
                        return UNGRADED
            else:
                return self._PRINT_GRADE[grade.rstrip('+-')]
        except:
            pass
        raise GradeConfigError(_INVALID_GRADE.format(grade = repr(grade)))
#
    @classmethod
    def categories(cls):
        """Return list of tuples: (term tag, term name).
        """
        return [(cat[0], cat[1]) for cat in cls._CATEGORIES]
#
    @classmethod
    def term2group_rtype_list(cls, term):
        """Return list of (group, default-report-type) pairs for valid
        groups in the given term.
        """
        try:
            return cls._REPORT_GROUPS[term]
        except KeyError as e:
            raise GradeConfigError(_BAD_TERM.format(term = term))
#
    @classmethod
    def grade_path(cls, term):
        for cat in cls._CATEGORIES:
            if cat[0] == term:
                return cat[2]
        raise Bug("Bad category/type: %s" % term)
#
    @staticmethod
    def special_term(termGrade):
        if termGrade.term != 'A':
            raise GradeConfigError(_BAD_TERM.format(term = term))
        # Add additional oral exam grades
        slist = []
        termGrade.sdata_list
        for sdata in termGrade.sdata_list:
            slist.append(sdata)
            if sdata.sid.endswith('.e') or sdata.sid.endswith('.g'):
                slist.append(sdata._replace(
                        sid = sdata.sid[:-1] + 'x',
# <tids> must have a value, otherwise it will not be passed by the
# composites filter, but is this alright? (rather ['X']?)
                        tids = 'X',
                        composite = None,
                        report_groups = None,
                        name = sdata.name.split('|', 1)[0] + '| nach'
                    )
                )
        termGrade.sdata_list = slist
#
    @staticmethod
    def category2text(term):
        """For grade tables, produce readable "term" entries.
        """
        if term in ('1', '2'):
            return '%s. Halbjahr' % term
        if term == 'A':
            return 'Abitur'
        if term[0] == 'S':
            return term
        raise Bug("INVALID term: %s" % term)
#
    @staticmethod
    def text2category(text):
        """For grade tables, convert the readable "term" entries to
        the corresponding tag.
        """
        t0 = text[0]
        if t0 in ('1', '2', 'A'):
            return t0
        if text[0] == 'S':
            return text
        raise Bug("INVALID term text: %s" % text)

