#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/config.py

Last updated:  2019-12-15

Functions for handling configuration for a particular location.


=+LICENCE=============================
Copyright 2019 Michael Towers

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

#TODO: Perhaps class 13 should be completely separate?
#TODO: Perhaps this data should be in a conf. file?
GRADE_TEMPLATES = {
    '13': {
            'Abgang': 'Abgang-13.html',
            'Zeugnis': 'Notenzeugnis-13.html'
        },
    '12.Gym': {
            'Abgang': 'Notenzeugnis-12_SII.html',
            'Zeugnis': 'Notenzeugnis-12_SII.html'
        },
    '12': {
            'Abgang': 'Notenzeugnis-SI.html',
            'Zeugnis': 'Notenzeugnis-SI.html',
            'Abschluss': 'Notenzeugnis-SI.html'
        },
    '*': {
            'Abgang': 'Notenzeugnis-SI.html',
            'Orientierung': 'Orientierung.html',
            'Zeugnis': 'Notenzeugnis-SI.html',
            'Zwischen': 'Notenzeugnis-SI.html'
        },
}


import re
from types import SimpleNamespace

import jinja2

from wz_core.configuration import Paths


def printSchoolYear(year1):
    """Return a print version of the given school year.
    """
    if year1:
        return "%d–%d" % (year1 - 1, year1)


def printStream(stream):
    return {
        'Gym': 'Gymnasium',
        'HS': 'Hauptschule',
        'RS': 'Realschule'
    }.get(stream, '–––––')


##### Jinja template handling #####

def getTemplate(foldertag, filename):
    """Return a jinja2 <Template> instance.
    <foldertag> is the <Paths> tag for the template folder,
    <fielname> is the name of the file within the template folder.
    The filepath is available as attribute <filename>.
    """
    tpdir = Paths.getUserPath(foldertag)
    templateLoader = jinja2.FileSystemLoader(searchpath=tpdir)
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
    return templateEnv.get_template(filename)


def getTemplateTags(template):
    """Find all substrings containing only letters, digits, underscore
    and dot which are surrounded by '{{ ... }}'. Each item must start
    with a letter or underscore. More than one such substring may occur
    in each block.
    Return a <set>.
    """
    with open(template.filename, 'r', encoding='utf-8') as fh:
        text = fh.read()
    tags = set()
    for item in re.findall(r'\{\{(.*?)\}\}', text):
        tags.update(re.findall(r'.*?([a-zA-Z_][a-zA-Z0-9_.]*)', item))
    return tags


def pupilFields(tags):
    """Find the pupil data fields needed for a grade report.
    <tags> is a set of possible elements from '{{ ... }}' blocks.
    Return a list of pairs: [(internal tag, display name), ...].
    """
    name = CONF.TABLES.PUPILS_FIELDNAMES
    fields = []
    for tag in tags:
        try:
            b, f = tag.split('.')
        except:
            continue
        if b == 'pupil':
            fields.append((f, name[f]))
    return fields


def getReportTypes(klass_stream):
    try:
        return GRADE_TEMPLATES[klass_stream]
    except:
        pass
    k, s = fromKlassStream(klass_stream)
    if s:
        try:
            return GRADE_TEMPLATES[k]
        except:
            pass
    return GRADE_TEMPLATES['*']


def klassData(klass_stream, report_type='text', term=None):
    """Return a class instance with info required for printing reports
    for the given klass (and stream).
    """
    klass, stream = fromKlassStream(klass_stream)
    data = SimpleNamespace (
        name = klass.lstrip('0'),       # no leading zero on klass names
        klein = klass[-1] == 'K',       # "Kleinklasse"
        stream = stream,
        year = klass[:2].lstrip('0')    # assumes 2-digit classes
    )
    if report_type == 'text':
        data.template = getTemplate('DIR_TEXT_REPORT_TEMPLATES',
                'CoverSheet.html')
        data.final = klass.startswith('12') # highest class (text reports)
        return data

    # Get report templates
    rtypes = getReportTypes(klass_stream)
    try:
        data.template = getTemplate('DIR_GRADE_REPORT_TEMPLATES',
                rtypes[report_type])
    except:
        REPORT.Bug("Invalid grade report type for class {ks}: {rtype}",
                ks=klass_stream, rtype=report_type)
    data.report_type = report_type
    return data


def fromKlassStream (klass_stream):
    """Split a klass_stream item into klass and stream.
    If there is no stream, set this part to <None>.
    Return a tuple: (klass, stream).
    """
    try:
        klass, stream = klass_stream.split ('.')
        return (klass, stream)
    except:
        return (klass_stream, None)


def toKlassStream (klass, stream):
    """Build a klass_stream name from klass and stream.
    Stream may be <None> or other "false" value, in which case
    just the klass is returned.
    Return klass_stream as <str>.
    """
    return klass + '.' + stream if stream else klass


####### Name Sorting #######
def sortingName(firstname, lastname):
    """Given first and last names, produce an ascii string which can be
    used for sorting the people alphabetically. It uses <tvSplit> (below)
    for handling last-name prefixes.
    """
    tv, lastname = tvSplit (lastname)
    if tv:
        sortname = lastname + ' ' + tv + ' ' + firstname
    else:
        sortname = lastname + ' ' + firstname
    return asciify(sortname)

# In dutch there is a word for those little lastname prefixes like "von",
# "zu", "van" "de": "tussenvoegsel". For sorting purposes these can be a
# bit annoying because they are often ignored, e.g. "van Gogh" would be
# sorted under "G".
def tvSplit (lastname):
    """Split a "tussenvoegsel" from the beginning of the last name.
    Return a tuple: (tussenvoegsel or <None>, "main" part of last name).
    """
    tvlist = list (CONF.MISC.TUSSENVOEGSEL)
    ns = lastname.split ()
    if len (ns) >= 1:
        tv = []
        i = 0
        for s in ns:
            if s in tvlist:
                tv.append (s)
                i += 1
            else:
                break
        if i > 0:
            return (" ".join (tv), " ".join (ns [i:]))
    return (None, " ".join (ns))    # ensure normalized spacing


def asciify(string):
    """This converts a utf-8 string to ASCII, e.g. to ensure portable
    filenames are used when creating files.
    Also spaces are replaced by underlines.
    Of course that means that the result might look quite different from
    the input string!
    A few explicit character conversions are given in the config file
    'ASCII_SUB'.
    """
    # regex for characters which should be substituted:
    _invalid_re = r'[^A-Za-z0-9_.~-]'
    def rsub (m):
        c = m.group (0)
        if c == ' ':
            return '_'
        try:
            return lookup [c]
        except:
            return '^'

    lookup = CONF.ASCII_SUB
    return re.sub (_invalid_re, rsub, string)


##################### Test functions
def test_01 ():
    REPORT.Test ('de Witt --> <%s> <%s>' % tvSplit ('de Witt'))
    REPORT.Test ('De Witt --> <%s> <%s>' % tvSplit ('De Witt'))
    REPORT.Test ("o'Riordan --> <%s> <%s>" % tvSplit ("o'Riordan"))
    REPORT.Test ("O'Riordan --> <%s> <%s>" % tvSplit ("O'Riordan"))
