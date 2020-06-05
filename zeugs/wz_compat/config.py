### python >= 3.7
# -*- coding: utf-8 -*-

"""
wz_compat/config.py

Last updated:  2020-06-05

Functions for handling configuration for a particular location.


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
_BADNAME = "Ungültiger Schülername: {name}"


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


def pupil_xfields(class_):
    """Return details of XDATA fields for the pupils. This can depend on
    the school-class, so this must be provided.
    The result is a mapping: {field-name -> (title, description OR <None>,
            list of possible values OR <None>)}
    """
    if class_ in ('12', '13'):
        return {
            'QUALI_D': ("Eintritt in die Qualifikationsphase",
                    ("Dieses Feld wird für manche Notenzeugnisse benötigt,"
                    " aber nur für Schüler in der Qualifikationsphase"
                    " (also die Abitur-Gruppe)."),
                    None)
        }
    return {}


####### Name Sorting #######
def name_filter(firstnames, lastname, firstname):
    """Given raw firstnames, lastname and short firstname.
    Ensure that any "tussenvoegsel" is at the beginning of the lastname
    (and not at the end of the first name) and that spaces are normalized.
    Also generate a "sorting" name, a field which combines name components
    to sort the entries alphabetically in a fairly consistent way,
    considering "tussenvoegsel".
    """
    firstnames1, tv, lastname1 = tvSplit(firstnames, lastname)
    firstname1 = tvSplit(firstname, 'X')[0]
    sortname = sortingName(firstname1, tv, lastname1)
    if tv:
        lastname1 = tv + ' ' + lastname1
    return (firstnames1, lastname1, firstname1, sortname)


def sortingName(firstname, tv, lastname):
    """Given first name, "tussenvoegsel" and last name, produce an ascii
    string which can be used for sorting the people alphabetically.
    """
    if tv:
        sortname = lastname + ' ' + tv + ' ' + firstname
    else:
        sortname = lastname + ' ' + firstname
    return asciify(sortname)


# In Dutch there is a word for those little lastname prefixes like "von",
# "zu", "van" "de": "tussenvoegsel". For sorting purposes these can be a
# bit annoying because they are often ignored, e.g. "van Gogh" would be
# sorted under "G".
def tvSplit(fnames, lname):
    """Split off a "tussenvoegsel" from the end of the first-names,
    <fnames>, or the start of the surname, <lname>.
    Also ensure normalized spacing between names.
    Return a tuple: (
            first names without tussenvoegsel,
            tussenvoegsel or <None>,
            lastname without tussenvoegsel
        ).
    """
    fn = []
    tv = fnames.split()
    while tv[0][0].isupper():
        fn.append(tv.pop(0))
        if not len(tv):
            break
    if not fn:
        REPORT.Fail(_BADNAME, name = fnames + ' / ' + lname)
    ln = lname.split()
    while ln[0].islower():
        if len(ln) == 1:
            break
        tv.append(ln.pop(0))
    return (' '.join(fn), ' '.join(tv) or None, ' '.join(ln))


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
    return
