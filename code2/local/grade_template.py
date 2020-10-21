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

    def __init__(self, grades):
        gclass = grades['CLASS']
        if gclass >= '12' or (gclass >= '11' and grades['TERM'] != '1'):
            raise GradeConfigError(_INVALID_RTYPE.format(rtype = self.TAG))
        super().__init__(TEMPLATE_FILE('grades-Orientierung'))


class Zeugnis(Template):
    NAME = 'Zeugnis'
    TAG = 'Zeugnis'

    def __init__(self, grades):
        gclass = grades['CLASS']
        glevel = grades['LEVEL']
        gquali = grades['QUALI']
        t = 'grades-SekI'
        if glevel == 'Gym':
            if gclass >= '13':
                if grades['TERM'] != '1':
                    t = 'grades-SekII-13_1'
                else:
                    raise GradeConfigError(_BAD_RTYPE.format(
                            rtype = self.TAG, pupil = grades['NAME']))
            elif gclass >= '12':
                if gquali not in ('HS', 'RS', 'Erw'):
                    raise GradeConfigError(_BAD_QUALI.format(tag = gquali))
                t = 'grades-SekII'
        super().__init__(t)


class Abschluss(Template):
    NAME = 'Abschlusszeugnis'
    TAG = 'Abschluss'

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

    def __init__(self, grades):
        t = 'grades-SekI-Abgang'
        gclass = grades['CLASS']
        glevel = grades['LEVEL']
        gquali = grades['QUALI']
        if glevel == 'Gym':
            if gclass >= '13':
                t = 'grades-SekII-13-Abgang'
            elif gclass >= '12':
                # <gquali> can be only 'HS', 'RS' or 'Erw'
                # (the criteria are a bit different to the other streams!)
                if gquali not in ('HS', 'RS', 'Erw'):
                    raise GradeConfigError(_BAD_QUALI.format(tag = gquali))
                if grades['TERM'] != '2':
                    grades['QUALI'] = 'HS'
                t = 'grades-SekII-12-Abgang'
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

    def __init__(self, grades):
        if grades['CLASS'] >= '11':
            raise GradeConfigError(_INVALID_RTYPE.format(rtype = self.TAG))
        super().__init__('grades-SekI')


#Abgang Quali:HS/RS/Erw/-
#Abschluss Quali:HS/RS/Erw (no Quali => no Abschluss!)
#Zeugnis 12G/2: Quali must be Erw for Versetzung
#Zeugnis 11G/2: Average < 3,00 for Versetzung
# Could calculate a suggested Quali value?

# Map report-type tags to management classes
REPORT_TYPES = {rclass.TAG: rclass
        for rclass in (Orientierung, Zeugnis, Abgang, Abschluss, Zwischen)}





