#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
simpleodt.py - last updated 2019-06-30

1) OdtReader
=============
Read the text content of odt files ignoring all formatting/style information.

2) OdtTemplate
==============
Write odt files using a VERY simple templating approach.
It has limited capabilities, but should be adequate for the purposes of this
application ...

3) OdtUserFields
===============
(a) Fetch the names (and values) of the user fields from a LibreOfffice Writer file.
(b) Fill the user fields in a LibreOfffice Writer file.

==============================
Copyright 2017-2018 Michael Towers

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

# Messages
_EMPTYFIELD = "Leeres Feld ({name}) in {path}"
_OdtNestedParagraph     = "odt: Unerwarteter Absatzanfang"
_OdtParagraphEnd        = "odt: Unerwartetes Absatzende"
_OdtBadData             = "odt: Unerwartete Inhalte"
_OdtBadTextTemplateFile = "Fehlerhafte Vorlage-Datei: {path}"
_OdtMissingTemplateFile = "Vorlage-Datei existiert nicht: {path}"


import zipfile as zf
import io as si
import os, re
from collections import OrderedDict

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


def substituteZipContent (infile, outfile, process):
    sio = si.BytesIO ()
    with zf.ZipFile (sio, "w", compression=zf.ZIP_DEFLATED) as zio:
        with zf.ZipFile (infile, "r") as za:
            for fin in za.namelist ():
                indata = za.read (fin)
                if fin == _ODT_CONTENT_FILE:
                    indata = process (indata)
                    if not indata:
                        return False
                zio.writestr (fin, indata)

    with open (outfile, "wb") as fout:
        fout.write (sio.getvalue ())
    return True


class OdtTemplate:
    """This uses a very simple content-replacement approach.
    The template file should contain a paragraph with a special key string
    (easiest is probably just a single character, say '*').
    This key string can be replaced by an alternative text (no formatting!)
    and additional paragraphs can be added after this one. These additional
    paragraphs need to be correct XML for the document.
    """
    _paragraph = '<text:p>%s</text:p>'
    _empty = '<text:p/>'

    @classmethod
    def makeFile (cls, filepath, insertList, key=b'*', template=None):
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
        if not filepath.endswith ('.odt'):
            filepath += '.odt'
        return substituteZipContent (template, filepath, _process)


class OdtUserFields:
    """Manage substitution of user-fields in an odt document.

    The declaration of a user-field looks like this:

    <text:user-field-decl office:value-type="string" office:string-value="?SCHULJAHR?" text:name="SCHULJAHR"/>

    That is the bit where the substitution needs to be done ('office:string-value').
    The name is used as key.

    At the places in the document where the user-field is actually used the xml
    looks like this:

    <text:user-field-get text:name="SCHULJAHR">?SCHULJAHR?</text:user-field-get>

    That bit need not be changed – unless the document is to be read by something
    other than libreoffice.
    """
    _ufregex = re.compile (br'<text:user-field-decl'
            br'[^>]*?office:string-value="([^"]+)"'
            br'[^>]*?text:name="([^"]+)"/>')


    @classmethod
    def listUserFields (cls, odtfile):
        tagmap = OrderedDict ()
        def _process (xmldata):
            for val, name in cls._ufregex.findall (xmldata):
                tagmap [name.decode ('utf-8')] = val.decode ('utf-8')
            return None

        substituteZipContent (odtfile, None, _process)
        return tagmap


    @classmethod
    def fillUserFields (cls, odtfile, outfile, itemdict):
        useditems = set ()
        nonitems = set ()
        newdata = []

        def _process (xmldata):
            """Use the regular expression to find all user-field declarations.
            Those for which an entry is provided in <itemdict> will have their
            values substituted.
            """
            pos = 0
            while True:
                rem = cls._ufregex.search (xmldata, pos)
                if not rem:
                    # No further user fields
                    newdata.append (xmldata [pos:])
                    break
                name = rem.group (2).decode ('utf-8')
                p1, p2 = rem.span (1)
                newpos = rem.end()
#                print ("POSITIONS:", name, p1, p2, newpos)
                if name in itemdict:
                    useditems.add (name)
                    newdata.append (xmldata [pos:p1])
                    try:
                        val = xmlescape (itemdict [name])
                    except:
                        REPORT.Warn (_EMPTYFIELD, path=outfile, name=name)
                        val = ''
                    newdata.append (val.encode ('utf-8'))
                    newdata.append (xmldata [p2:newpos])
                else:
                    nonitems.add (name)
                    newdata.append (xmldata [pos:newpos])
                pos = newpos
            return b''.join (newdata)

        if not outfile.endswith ('.odt'):
            outfile += '.odt'
        substituteZipContent (odtfile, outfile, _process)
        return (outfile, useditems, nonitems)
