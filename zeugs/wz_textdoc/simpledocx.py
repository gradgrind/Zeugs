#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
simpledocx.py - last updated 2018-01-31

1) DocxReader
=============
Read the text content of docx files ignoring all formatting/style information.

2) DocxTemplate
==============
Write docx files using a VERY simple templating approach.
It has limited capabilities, but should be adequate for the purposes of this
application ...

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

#I18N+
#DocxNestedParagraph:       docx: Unerwarteter Absatzanfang.
#DocxParagraphEnd:          docx: Unerwartetes Absatzende.
#DocxBadData:               docx: Unerwartete Inhalte.
#DocxBadTextTemplateFile:   Fehlerhafte Vorlage-Datei: %(path)s
#DocxMissingTemplateFile:   Vorlage-Datei existiert nicht: %(path)s
#I18N-

import zipfile as zf
import io as si
import os, re

"""
    docx-format
    ===========

    The content is found in the file "word/document.xml".
    The following seems to be the simplest possible structure for paragraphs:

    1) An empty paragraph:
        <w:p/>

    2) With text:
        <w:p>
          <w:r>
            <w:t>This is a paragraph.</w:t>
          </w:r>
        </w:p>

    As the zip file is unpacked to a byte array, all 'strings' used here
    must also be byte arrays.
    As far as I can tell, the encoding should always be utf-8 ...
"""

_DOCX_CONTENT_FILE = 'word/document.xml'
_TEMPLATE_FILE = 'textTemplate.docx'

from xml.parsers.expat import ParserCreate
from xml.sax.saxutils import escape

def xmlescape (text):
    return escape (text, entities={
        "'": "&apos;",
        "\"": "&quot;"
    })


class DocxReader:
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
        if name == 'w:p':
            if cls._text != None:
                REPORT.Error ('DocxNestedParagraph')
            cls._text = ""

    @classmethod
    def _end_element(cls, name):
#        print('>>> End element:', name)
        if name == 'w:p':
            if cls._text == None:
                REPORT.Error ('DocxParagraphEnd')
            cls._lines.append (cls._text)
            cls._text = None

    @classmethod
    def _char_data(cls, data):
#        print('>>> Character data:', type (data), repr(data))
        if cls._text == None:
            REPORT.Error ('DocxBadData')
        else:
            cls._text += data

    ############ end handler functions ############


    @classmethod
    def readDocxFile (cls, filepath):
        xmldata = cls._getDocxContent (filepath)
        return cls.parseXML (xmldata)


    @staticmethod
    def _getDocxContent (filepath):
        """Returns the content xml file – I assume always bytes encoded as utf-8.
        """
        with zf.ZipFile (filepath) as zipfile:
            xmlbytes = zipfile.read (_DOCX_CONTENT_FILE)
        return xmlbytes


    @classmethod
    def readFile (cls, xmlfile):
        with open (xmlfile, "rb") as fi:
            xmldata = fi.read ()
        return cls.parseXML (xmldata)



class DocxTemplate:
    """This uses a very simple content-replacement approach.
    The template file should contain a paragraph with a special key string
    (easiest is probably just a single character, say '*').
    This key string can be replaced by an alternative text (no formatting!)
    and additional paragraphs can be added after this one. These additional
    paragraphs need to be correct XML for the document.
    """
    _paragraph = '<w:p><w:r><w:t>%s</w:t></w:r></w:p>'
    _empty = '<w:p/>'

    @classmethod
    def makeFile (cls, filepath, insertList, key=b'*', template=None):
        def _process (xmldata):
            rem = regex.search (xmldata)
            if not rem:
                REPORT.ERROR ('DocxBadTextTemplateFile', path=template)
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
            REPORT.Error ('DocxMissingTemplateFile', path=template)
            return False
        # Set up the regular expression for finding the correct place in
        # the data file.
        regex = re.compile (br'<w:p>.*?[%s].*?</w:p>' % key, flags=re.DOTALL)

        ilist = [] if insertList == None else insertList.copy ()
        sio = si.BytesIO()
        with zf.ZipFile(sio, "w", compression=zf.ZIP_DEFLATED) as zio:
            with zf.ZipFile(template, "r") as za:
                for infile in za.namelist():
                    indata = za.read(infile)
                    if infile == _DOCX_CONTENT_FILE:
                        indata = _process (indata)
                        if not indata:
                            return False
                    zio.writestr(infile, indata)

        if not filepath.endswith ('.docx'):
            filepath += '.docx'
        with open(filepath, "wb") as oufile:
            oufile.write(sio.getvalue())
        return True
