### python >= 3.7
# -*- coding: utf-8 -*-

"""
local/grade_template.py

Last updated:  2020-10-21

Manage templates for grade reports.


=+LICENCE=============================
Copyright 2020 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

=-LICENCE========================================
"""

### Messages
_BAD_QUALI = "Ungültiger Eintrag im Feld 'Qualifikation': '{tag}'"
_BAD_RTYPE = "Ungültiger Zeugnistyp für {name}: '{rtype}'"
_INVALID_RTYPE = "Ungültiger Zeugnistyp: '{rtype}'"


from local.grade_config import GradeConfigError
from template_engine.template_sub import Template


# Could define <TEMPLATE_FILE> elsewhere and "update" it here for grades?
TEMPLATE_FILE = {
    'grades-Orientierung':      'grades/Orientierung.odt',
    'grades-SekII-13_1':        'grades/SekII-13_1.odt',
    'grades-SekII':             'grades/SekII.odt',
    'grades-SekI':              'grades/SekI.odt',
    'grades-SekI-Abschluss':    'grades/SekI-Abschluss.odt',
    'grades-SekII-13-Abgang':   'grades/SekII-13-Abgang.odt',
    'grades-SekII-12-Abgang':   'grades/SekII-12-Abgang.odt',
    'grades-SekI-AbgangHS':     'grades/SekI-Abgang.odt',
    'grades-SekI-Abgang':       'grades/SekI-Abgang.odt',
    'grades-Abitur':            'grades/Abitur.odt',
    'grades-Kein-Abitur':       'grades/Abitur-nicht-bestanden.odt',
    'grades-FHS-Reife':         'grades/Fachhochschulreife.odt'
#
}

class Orientierung(Template):
    NAME = 'Orientierungsnoten'
    TAG = 'Orientierung'
    GROUPS = ('V', 'K')

    def __init__(self, grades):
        gclass = grades['CLASS']
        if gclass >= '12' or (gclass >= '11' and grades['TERM'] != '1'):
            raise GradeConfigError(_INVALID_RTYPE.format(rtype = self.TAG))
        super().__init__(TEMPLATE_FILE('grades-Orientierung'))


class Zeugnis(Template):
    NAME = 'Zeugnis'
    TAG = 'Zeugnis'
    GROUPS_SekI = ('V', 'K')
    GROUPS_SekII_12 = ('A', 'B', 'C', 'D', 'X')
    GROUPS_SekII_13 = ('E', 'G')

    def __init__(self, grades):
        gclass = grades['CLASS']
        glevel = grades['LEVEL']
        gquali = grades['QUALI']
        t = 'grades-SekI'
        self.GROUPS = self.GROUPS_SekI
        if glevel == 'Gym':
            if gclass >= '13':
                if grades['TERM'] != '1':
                    t = 'grades-SekII-13_1'
                    self.GROUPS = self.GROUPS_SekII_13
                else:
                    raise GradeConfigError(_BAD_RTYPE.format(
                            rtype = self.TAG, pupil = grades['NAME']))
            elif gclass >= '12':
                if gquali not in ('HS', 'RS', 'Erw'):
                    raise GradeConfigError(_BAD_QUALI.format(tag = gquali))
                t = 'grades-SekII'
                self.GROUPS = self.GROUPS_SekII_12
        super().__init__(t)


class Abschluss(Template):
    NAME = 'Abschlusszeugnis'
    TAG = 'Abschluss'
    GROUPS = ('V', 'K')

    def __init__(self, grades):
        t = False
        gclass = grades['CLASS']
        glevel = grades['LEVEL']
        gquali = grades['QUALI']
        if gclass in ('12', '11'):
            if glevel == 'HS' and gquali == 'HS':
                t = True
            elif (glevel == 'RS' and
                    (gquali == 'RS'
                     or (gquali == 'Erw' and gclass == '12'))):
                t = True
        if t:
            super().__init__('grades-SekI-Abschluss')
        else:
            raise GradeConfigError(_BAD_RTYPE.format(
                    rtype = self.TAG, pupil = grades['NAME']))


class Abgang(Template):
    NAME = 'Abgangszeugnis'
    TAG = 'Abgang'
    GROUPS_SekI = ('V', 'K')
    GROUPS_SekII_12 = ('A', 'B', 'C', 'D', 'X')
    GROUPS_SekII_13 = ('E', 'G')

    def __init__(self, grades):
        t = 'grades-SekI-Abgang'
        self.GROUPS = self.GROUPS_SekI
        gclass = grades['CLASS']
        glevel = grades['LEVEL']
        gquali = grades['QUALI']
        if glevel == 'Gym':
            if gclass >= '13':
                t = 'grades-SekII-13-Abgang'
                self.GROUPS = self.GROUPS_SekII_13
            elif gclass >= '12':
                # <gquali> can be only 'HS', 'RS' or 'Erw'
                # (the criteria are a bit different to the other streams!)
                if gquali not in ('HS', 'RS', 'Erw'):
                    raise GradeConfigError(_BAD_QUALI.format(tag = gquali))
                if grades['TERM'] != '2':
                    grades['QUALI'] = 'HS'
                t = 'grades-SekII-12-Abgang'
                self.GROUPS = self.GROUPS_SekII_12
            elif gclass >= '11':
                # <gquali> can be only '/', 'HS', 'Erw'
                # (the criteria for 'Erw' is rather special ...)
                 if gquali not in ('/', 'HS', 'Erw'):
                    raise GradeConfigError(_BAD_QUALI.format(tag = gquali))
        elif gclass >= '11' or (gclass >= '10' and grades['TERM'] == '2'):
            if gquali in ('HS', 'RS', 'Erw'):
                t = 'grades-SekI-AbgangHS'
                grades['QUALI'] = 'HS'
            else:
                grades['QUALI'] = None
        super().__init__(t)


class Zwischen(Template):
    NAME = 'Zwischenzeugnis'
    TAG = 'Zwischen'
    GROUPS = ('V', 'K')

    def __init__(self, grades):
        if grades['CLASS'] >= '11':
            raise GradeConfigError(_INVALID_RTYPE.format(rtype = self.TAG))
        super().__init__('grades-SekI')


# Map report-type tags to management classes
REPORT_TYPES = {rclass.TAG: rclass
        for rclass in (Orientierung, Zeugnis, Abgang, Abschluss, Zwischen)}


#Abgang Quali:HS/RS/Erw/-
#Abschluss Quali:HS/RS/Erw (no Quali => no Abschluss!)
#Zeugnis 12G/2: Quali must be Erw for Versetzung
#Zeugnis 11G/2: Average < 3,00 for Versetzung
# Could calculate a suggested Quali value?

"""
SCHOOLBIG
SCHOOL
SCHOOLYEAR
ISSUE_D
COMMENT = ""
NOCOMMENT = "––––––––––"

SekI:
    ZEUGNIS
    Zeugnis
    LEVEL
    CLASS
    +SekI-Abgang:
        CYEAR (class number)
        GSVERMERK: "Gleichstellungsvermerk" or ""
        GS: Gleichstellungsvermerk (HS) or ""
        +SekI-Abschluss:
            SEKI: e.g. Erweiterter Sekundarabschluss I
    COMMENT: Versetzung? (11:Gym/2 only) ... with GRADES_D
    NOCOMMENT: "" if COMMENT set
SekII-12:
    HJ: "1." or "1. und 2."
    QP12: "hat den 12. Jahrgang der Qualifikationsphase vom 15.08.2019"
        " bis zum 15.07.2020 besucht." (needs QUALI_D, last-school-day)
    COMMENT: Versetzung? ... with GRADES_D
    NOCOMMENT: "" if COMMENT set

SekII-12-Abgang:
    QP12: see above, but with EXIT_D instead of last-school-day
    GS: Gleichstellungsvermerk
SekII-13_1:
    QUALI_D
SekII-13-Abgang:
    QUALI_D
    EXIT_D
    all Abitur grades from 12 and 13

Abitur (etc):
    HOME
    FrHr
    calculated abi grades, etc.
"""

from local.base_config import print_schoolyear, class_year

LEVEL_TEXT = {
    'HS': 'Hauptschule',
    'RS': 'Realschule',
    'Gym': 'Gymnasium'
}
GS_TEXT = {
    'HS': "Dieses Zeugnis ist dem Sekundarabschluss I – Hauptschulabschluss" \
            " gleichgestellt. Es vermittelt die gleiche Berechtigung wie" \
            " das Zeugnis über den Sekundarabschluss I – Hauptschulabschluss.",
    'RS': "Dieses Zeugnis ist dem Sekundarabschluss I – Realschulabschluss" \
            " gleichgestellt. Es vermittelt die gleiche Berechtigung wie" \
            " das Zeugnis über den Sekundarabschluss I – Realschulabschluss.",
    'Erw': "Dieses Zeugnis ist dem Erweiterten Sekundarabschluss I" \
            " gleichgestellt. Es vermittelt die gleiche Berechtigung wie" \
            " das Zeugnis über den Erweiterten Sekundarabschluss I."
}
SEKI_TEXT = {
    'HS': "Sekundarabschluss I – Hauptschulabschluss",
    'RS': "Sekundarabschluss I – Realschulabschluss",
    'Erw': "Erweiterter Sekundarabschluss I"
}


# Here I am accessing the group data of the grade table as attributes of
# <grades>, rather than as dict-items (as in the above code). If <grades>
# is a GradeManager, the dict-items should probably just be the grades.
def xxx():
    school_name = "Freie Michaelschule"
    data['SCHOOLBIG'] = school_name.upper()
    data['SCHOOL'] = school_name
    data['SCHOOLYEAR'] = print_schoolyear(self.schoolyear)
    data['ISSUE_D'] = Dates.print_date(grades.ISSUE_D)
    data['ZEUGNIS'] = self.NAME.upper()
    data['Zeugnis'] = self.NAME
    data['LEVEL'] = LEVEL_TEXT[grades.LEVEL] # or grades['LEVEL']?
    data['CLASS'] = grades.CLASS
    data['COMMENT'] = ""
    data['NOCOMMENT'] = "––––––––––"
    data['CYEAR'] = class_year(grades.CLASS)
    data['GSVERMERK'] = ""      # can be "Gleichstellungsvermerk"
    data['GS'] = ""             # from GS_TEXT, if appropriate

    if grades.TERM == '1': data['HJ'] = "1."
    elif grades.TERM == '2': data['HJ'] = "1. und 2."
    else: data['HJ'] = ""

# add the pupil data ...
#? ... this one is only for Abitur:
    data['FrHr'] = 'Herr' if grades.pdata['SEX'] == 'm' else 'Frau'
# then allocate the subjects/grades to the slots ...
