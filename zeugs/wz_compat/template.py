#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/template.py

Last updated:  2019-12-31

Functions for template handling.


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

import os, re

import jinja2

from wz_core.configuration import Paths, Dates
from wz_core.pupils import fromKlassStream, match_klass_stream


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


def getTemplate(rcat, klass_stream):
#TODO: self.final is deprecated – use self.report_type ('Abgang')
#            self.final = self.klass.startswith('12') # highest class (text reports)
    # Get report templates
    tlist = CONF.REPORT_TEMPLATES[rcat]
    val = match_klass_stream(klass_stream, tlist)
    if val:
        report_type, tfile = val.split('+')
        return (report_type, openTemplate(tfile))
    else:
        REPORT.Bug("Invalid grade report category for class {ks}: {rcat}",
                ks=klass_stream,
                rcat=rcat)



##################### Test functions
def test_01 ():
    return