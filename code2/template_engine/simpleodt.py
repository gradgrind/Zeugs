#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
simpleodt.py - last updated 2020-10-14

1) OdtReader
=============
Read the text content of odt files ignoring all formatting/style information.

2) OdtTemplate
==============
Write odt files using a VERY simple templating approach.
It has limited capabilities, but should be adequate for the purposes of this
application ...

3) OdtFields
===============
(a) Fetch the names of the "fields" from a LibreOfffice Writer file.
(b) Fill the "fields" in a LibreOfffice Writer file.

==============================
Copyright 2017-2020 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import sys, os
if __name__ == '__main__':
    # Enable package import if running as module for testing
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

import zipfile as zf
import io, re

"""
    odt-format
    ===========

    The content is found in the file "content.xml".
    The following seems to be the simplest possible structure for paragraphs:

    1) An empty paragraph:
        <text:p text:style-name="Standard"/>

    2) With text:
        <text:p text:style-name="P1">[[geo AB 10_G]] Geographie; Arthur Benommen.
        </text:p>

        It looks like the text:style-name="P1" bit is not compulsory, but libreoffice
        seems to add it if it is not there.

    However, formatting information is embedded ...
        <text:p text:style-name="Standard">Mit etwas Text und – um die Sache
            <text:span text:style-name="T1">interessant</text:span>
            zu machen – etwas
            <text:span text:style-name="T2">Formatierung</text:span>
            !
        </text:p>

    As the zip file is unpacked to a byte array, all 'strings' used here
    must also be byte arrays.
    As far as I can tell, the encoding should always be utf-8 ...
"""

_ODT_CONTENT_FILE = 'content.xml'
_TEMPLATE_FILE = 'textTemplate.odt'

from xml.parsers.expat import ParserCreate
from xml.sax.saxutils import escape

def xmlescape (text):
    return escape (text, entities={
        "'": "&apos;",
        "\"": "&quot;"
    })


#TODO: Old code, if needed this will need modifications (e.g. to error
# reporting)
class OdtReader:
    """Uses the expat parser to get at the paragraphs and their contained data.
    All formatting information is ignored.
    An xml string is parse to a list of paragraphs (without '\n').

    Note that the expat parser converts all items to unicode.

    An instance of the expat parser can only handle a single file, so
    a new instance must be created for each file to be parsed.
    """

    _lines = None
    _text = None

    @classmethod
    def parseXML (cls, xmldata):
        parser = ParserCreate ()

        parser.StartElementHandler = cls._start_element
        parser.EndElementHandler = cls._end_element
        parser.CharacterDataHandler = cls._char_data

        cls._lines = []
        parser.Parse (xmldata)
        return cls._lines


    ############ 3 handler functions ############

    @classmethod
    def _start_element(cls, name, attrs):
#        print('>>> Start element:', name, attrs)
        if name == 'text:p':
            if cls._text != None:
                REPORT.Error ('OdtNestedParagraph')
            cls._text = ""

    @classmethod
    def _end_element(cls, name):
#        print('>>> End element:', name)
        if name == 'text:p':
            if cls._text == None:
                REPORT.Error ('OdtParagraphEnd')
            cls._lines.append (cls._text)
            cls._text = None

    @classmethod
    def _char_data(cls, data):
#        print('>>> Character data:', type (data), repr(data))
        if cls._text == None:
            REPORT.Error ('OdtBadData')
        else:
            cls._text += data

    ############ end handler functions ############


    @classmethod
    def readOdtFile (cls, filepath):
        xmldata = cls._getOdtContent (filepath)
        return cls.parseXML (xmldata)


    @staticmethod
    def _getOdtContent (filepath):
        """Returns the content xml file – I assume always bytes encoded as utf-8.
        """
        with zf.ZipFile (filepath) as zipfile:
            xmlbytes = zipfile.read (_ODT_CONTENT_FILE)
        return xmlbytes


    @classmethod
    def readFile (cls, xmlfile):
        with open (xmlfile, "rb") as fi:
            xmldata = fi.read ()
        return cls.parseXML (xmldata)


def substituteZipContent(infile, process):
    """Process the contents of an odt file using the function <process>.
    Return the resulting odt file as a <bytes> array.
    """
    sio = io.BytesIO()
    with zf.ZipFile(sio, "w", compression=zf.ZIP_DEFLATED) as zio:
        with zf.ZipFile(infile, "r") as za:
            for fin in za.namelist():
                indata = za.read(fin)
                if fin == _ODT_CONTENT_FILE:
                    indata = process(indata)
                    if not indata:
                        return None
                zio.writestr(fin, indata)
    return sio.getvalue()


#TODO: Old code, if needed this will need modifications (e.g. to error
# reporting and template handling)
class OdtTemplate:
    """This uses a very simple content-replacement approach.
    The template file should contain a paragraph with a special key string
    (easiest is probably just a single character, say '*').
    This key string can be replaced by an alternative text (no formatting!)
    and additional paragraphs can be added after this one. These additional
    paragraphs need to be correct XML for the document.
    Return the odt file as a <bytes> array.
    """
    _paragraph = '<text:p>%s</text:p>'
    _empty = '<text:p/>'

    @classmethod
    def makeFile (cls, insertList, key=b'*', template=None):
        def _process (xmldata):
            rem = regex.search (xmldata)
            if not rem:
                REPORT.ERROR ('OdtBadTextTemplateFile', path=template)
                return None
            spos = rem.start ()
            epos = rem.end ()
            s1 = xmldata [:spos]
            s2 = xmldata [spos:epos]
            s3 = xmldata [epos:]

            replaceText = xmlescape (ilist.pop (0))
            insertText = ''.join ([(cls._paragraph % xmlescape (para))
                    if para else cls._empty
                    for para in ilist])
            return (s1 + s2.replace (key, replaceText.encode ('utf-8'))
                + insertText.encode ('utf-8') + s3)

        if not template:
            template = os.path.join (os.path.dirname (__file__),
                    'resources', _TEMPLATE_FILE)
            if not os.path.isfile (template):
                try:
                    template = os.path.join (RESOURCE_DIR, _TEMPLATE_FILE)
                except:
                    pass
        if not os.path.isfile (template):
            REPORT.Error ('OdtMissingTemplateFile', path=template)
            return False
        # Set up the regular expression for finding the correct place in
        # the data file.
        regex = re.compile (br'<text:p.*?[%s].*?</text:p>' % key, flags=re.DOTALL)

        ilist = [] if insertList == None else insertList.copy ()
        return substituteZipContent (template, _process)


class OdtFields:
    """Manage substitution of "fields" in an odt document.
    A field is a text snippet like "[[key]]". The key may contain ASCII
    letters, digits, '.' and '_', but must start with a letter.

    During editing these can get split up by intervening XML tags, etc.
    In order to avoid this they should have all formatting removed and
    then reapplied when editing is complete.
    """
    _ufregex = re.compile(br'\[\[([a-zA-Z][a-zA-Z._0-9]*)\]\]')
#
    @classmethod
    def listUserFields(cls, odtfile):
        tagmap = []
        def _process(xmldata):
            for tag in cls._ufregex.findall(xmldata):
                tagmap.append(tag.decode('utf-8'))
            return None

        substituteZipContent(odtfile, _process)
        return tagmap
#
    @classmethod
    def fillUserFields(cls, odtfile, itemdict):
        useditems = set()
        nonitems = set()

        def _sub(rem):
            tag = rem.group(1).decode('utf-8')
            try:
                s = xmlescape(itemdict[tag]).encode('utf-8')
                useditems.add(tag)
                return s
            except KeyError:
                nonitems.add(tag)
                if itemdict:
                    return rem.group(0)
                else:
                    return b'{' + rem.group(1) + b'}'

        def _process(xmldata):
            """Use the regular expression to find all field declarations.
            Those for which an entry is provided in <itemdict> will have
            their values substituted.
            """
            return cls._ufregex.sub(_sub, xmldata)

        odtBytes = substituteZipContent(odtfile, _process)
        return (odtBytes, useditems, nonitems)

#Setting a variable (which is already defined in the file) in an odt:
#<text:variable-set text:name="hide1" office:value-type="float" office:value="0" style:data-style-name="N0">0</text:variable-set>


if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    _dirpath = os.path.join(RESOURCES, 'templates', 'grades')
    _itemdict = {}  # Just test that fields are ok
    _odir = os.path.join(DATA, 'testing', 'template-out')
    os.makedirs(_odir, exist_ok = True)
    for f in os.listdir(_dirpath):
        print("\nINPUT:", f)
        _odtfile = os.path.join(_dirpath, f)
        _outfile = os.path.join(_odir, 'test-' + f)
        odtBytes, used, notsub = OdtFields.fillUserFields(_odtfile, _itemdict)
        with open(_outfile, 'bw') as fout:
            fout.write(odtBytes)
        print("\nSUBSTITUTE to %s" % _outfile)
        print("  ... used:", sorted(used))
        print("\n  ... not supplied:", sorted(notsub))



    _odtfile = os.path.join(RESOURCES, 'templates', 'grades', 'Abitur.odt')
#    print("TAGS in %s:\n" % _odtfile, OdtFields.listUserFields(_odtfile))
    _school = 'Freie Michaelschule'
    _itemdict = {
        'SCHOOL': _school,
        'SCHOOLBIG': _school.upper(),
        'CLASS': '11',
        'SCHOOLYEAR': '2015 – 2016',
        'FIRSTNAMES': 'Hans Hermann',
        'LASTNAME': 'Höllermaß',
        'S.V.01': 'Arbeit-Wirtschaft-Technik',
        'G.V.01': 'kann nicht beurteilt werden',
        'S.V.02': 'Medienkunde',
        'G.V.02': 'befriedigend',
        'COMMENT': '',
        'NOCOMMENT': '––––––––––'
    }
    _out = os.path.join(DATA, 'testing', 'template-out', 'test-out1.odt')
    odtBytes, used, notsub = OdtFields.fillUserFields(_odtfile, _itemdict)
    with open(_out, 'bw') as fout:
        fout.write(odtBytes)
    print("\nSUBSTITUTE from %s to %s" % (_odtfile, _out))
    print("  ... used:", sorted(used))
    print("\n  ... not supplied:", sorted(notsub))
