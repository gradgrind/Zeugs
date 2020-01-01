#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_compat/config.py

Last updated:  2019-12-31

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

import re


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


class KlassData:
    def __init__(self, klass_stream):
        self.klass_stream = klass_stream
        self.klass, self.stream = fromKlassStream(klass_stream)
        # Leading zero on klass names?
        self.name = (self.klass if CONF.MISC.CLASS_LEADING_ZERO
                else self.klass.lstrip('0'))
#TODO: switch to klasstag (report covers!)
#        self.klein = self.klass[-1] == 'K'      # "Kleinklasse"
        self.klasstag = self.klass[2:]          # assumes 2-digit classes
        self.year = self.klass[:2].lstrip('0')  # assumes 2-digit classes


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
