#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/template.py

Last updated:  2020-01-25

Functions for template handling.


=+LICENCE=============================
Copyright 2019-2020 Michael Towers

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

# Messages
_NO_TEMPLATE = "Vorlage nicht gefunden: {fname}"


import os, re

import jinja2

from wz_core.configuration import Paths, Dates


def getGradeTemplate(rtype, klass):
    """Return the matching template for the given school-class/groups
    and report type.
    <klass> is a <Klass> instance.
    """
    tlist = CONF.GRADES.REPORT_TEMPLATES[rtype]
    tfile = klass.match_map(tlist)
    if tfile:
        return openTemplate(tfile)
    else:
        REPORT.Bug("Invalid report category for class {ks}: {rtype}",
                ks=klass, rtype=rtype)


def getTextTemplate(rtype, klass):
    """Return the matching template for the given school-class and
    report type.
    <klass> is a <Klass> instance.
    """
    tlist = CONF.TEXT.REPORT_TEMPLATES[rtype]
    tfile = klass.match_map(tlist)
    if tfile:
#        print ("???", tfile)
        return openTemplate(tfile)
    else:
        REPORT.Bug("Invalid report category for class {ks}: {rtype}",
                ks=klass, rtype=rtype)


##### Jinja template handling #####

def openTemplate(tpath):
    """Return a jinja2 <Template> instance.
    <tpath> is the path (folder separator '/') to the template file,
    relative to the main templates folder.
    The filepath is available as attribute <filename>.
    """
    tpsplit = tpath.split('/')
    fname = tpsplit.pop()
    tpdir = Paths.getUserPath('DIR_TEMPLATES')
    if tpsplit:
        tpdir = os.path.join(tpdir, *tpsplit)
    templateLoader = jinja2.FileSystemLoader(searchpath=tpdir)
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
    try:
        return templateEnv.get_template(fname)
    except:
        REPORT.Fail(_NO_TEMPLATE, fname=os.path.join(tpdir, fname))


def getTemplateTags(template):
    """Find all substrings containing only letters, digits, underscore
    and dot which are surrounded by '{{ ... }}' or '{% ... %}'.
    Each item must start with a letter or underscore. More than one such
    substring may occur in each block.
    Return a <set>.
    """
    _match = r'([a-zA-Z_][a-zA-Z0-9_.]*)'
    with open(template.filename, 'r', encoding='utf-8') as fh:
        text = fh.read()
    tags = set()
    for item in re.findall(r'\{\{(.*?)\}\}', text):
        tags.update(re.findall(_match, item))
    for item in re.findall(r'\{\%(.*?)\%\}', text):
        tags.update(re.findall(_match, item))
    return tags


def pupilFields(tags):
    """Find the pupil data fields needed for a report by inspecting the
    template.
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
        if b == 'pupil' and f[0].isupper():
# Note that all pupil data fields must start with a capital letter.
# This allows other pupil-related info to be passed into the template.
# One example (at present the only one?) is <pupil.grades>.
            fields.append((f, name[f]))
    return fields



##################### Test functions
def test_01 ():
    return
