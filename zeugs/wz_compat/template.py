#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/template.py

Last updated:  2020-01-18

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

import os, re

import jinja2

from wz_core.configuration import Paths, Dates
from wz_core.pupils import match_klass_stream, toKlassStream


def getGradeTemplate(rtype, klass, stream=None):
    """Return the matching template for the given school-class/stream
    and report type.
    """
    tlist = CONF.GRADES.REPORT_TEMPLATES[rtype]
    tfile = match_klass_stream(klass, tlist, stream)
    if tfile:
#        print ("???", tfile)
        return openTemplate(tfile)
    else:
        REPORT.Bug("Invalid report category for class {ks}: {rtype}",
                ks=toKlassStream(klass, stream),
                rtype=rtype)


def getTextTemplate(rtype, klass):
    """Return the matching template for the given school-class and
    report type.
    """
    tlist = CONF.TEXT.REPORT_TEMPLATES[rtype]
    tfile = match_klass_stream(klass, tlist)
    if tfile:
#        print ("???", tfile)
        return openTemplate(tfile)
    else:
        REPORT.Bug("Invalid report category for class {ks}: {rtype}",
                ks=klass,
                rtype=rtype)


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
    return templateEnv.get_template(fname)


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
        if b == 'pupil':
            fields.append((f, name[f]))
    return fields



##################### Test functions
def test_01 ():
    return
