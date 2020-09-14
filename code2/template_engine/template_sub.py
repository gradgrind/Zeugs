### python >= 3.7
# -*- coding: utf-8 -*-

"""
template_engine/template_sub.py

Last updated:  2020-09-10

Manage the substitution of "special" fields in a latex template.

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

The special substitution fields in a template start with '(*' and end
with '*)'. Between these delimiters there may be only ASCII-alphanumeric
characters and '.'.
"""

#TODO: Change the templates to use the pupil data fields without
# "translation". This would add some flexibility concerning exactly
# which fields are used – making all of them available would allow the
# template to "pick out" the ones it needs.
# One caveat: '_' characters must be changed to '.', as '_' is a special
# character in LaTeX.

#Messages:
_NOBLOCK = "Vorlage: Ende eines Blocks ohne Anfang"
_BLOCKMISMATCH = "Vorlage: Block-Anfang und -Ende stimmen nicht überein"
_BLOCKTAG = "Vorlage: Block-Bezeichnung wurde schon verwendet"
_BLOCKENDS = "Vorlage: Block endet nicht"

import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

import re

from core.run_extern import lualatex2pdf

RX_SUB = re.compile(r'\(\*([A-Za-z][A-Za-z0-9.]*?)\*\)')
TEX_ESC = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
RX_TEX_ESC = re.compile('|'.join(re.escape(key) for key in TEX_ESC.keys()))

def tex_escape(text):
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX
    """
    return RX_TEX_ESC.sub(lambda match: TEX_ESC[match.group()], text)



def substitute(text, sdict):
    """Substitute keys in the string <text> using the mapping <sdict>.
    Return a tuple (new text, {substituted keys}, {unsubstituted keys}).
    """
    subbed = set()
    unsubbed = set()
    def fsub(m):
        s = m.group(1)
        try:
            val = tex_escape(sdict[s])
            subbed.add(s)
        except KeyError:
            unsubbed.add(s)
            return '?' + s + '?'
        return val
    stext = RX_SUB.sub(fsub, text)
    return (stext, subbed, unsubbed)

# Blocks (may be nested):
#   Start: %[*tag*
#   End:   %]*tag*
RX_BLOCK_START = re.compile(r'\s*\%\[\*([A-Za-z][A-Za-z0-9.]*?)\*')
RX_BLOCK_END = re.compile(r'\s*\%\]\*([A-Za-z][A-Za-z0-9.]*?)\*')
SUB_BLOCK = '!!!!!*%s*'
class TemplateError(Exception):
    pass
class Template:
    def __init__(self, filename):
        filepath = os.path.join(RESOURCES, 'templates', filename)
        stack = []          # For nested blocks
        lines = []          # Current line accumulator
        self.lines = []     # All lines (unmodified)
        self.blocks = {}    # tag -> block (list of lines)
        with open(filepath, 'r', encoding='utf-8') as fin:
            for line in fin:
                line = line.rstrip()
                self.lines.append(line)
                # Check for start / end of blocks (tagged).
                m = RX_BLOCK_START.match(line)
                if m:
                    tag = m.group(1)
                    if tag in self.blocks:
                        raise TemplateError("%s:: %d\n  %s ('%s')" %
                                (filepath, len(self.lines), _BLOCKTAG, tag))
                    self.blocks[tag] = None
                    stack.append((tag, lines))
                    lines = []
                else:
                    m = RX_BLOCK_END.match(line)
                    if m:
                        if not stack:
                            raise TemplateError("%s:: %d\n  %s ('%s')" %
                                    (filepath, len(self.lines), _NOBLOCK,
                                            m.group(1)))
                        tag, _lines = stack.pop()
                        if m.group(1) != tag:
                            raise TemplateError("%s:: %d\n  %s ('%s' -> '%s')"
                                    % (filepath, len(self.lines),
                                    _BLOCKMISMATCH, tag, m.group(1)))
                        self.blocks[tag] = lines
                        lines = _lines
                        lines.append(SUB_BLOCK % tag)
                    else:
                        lines.append(line)
        if stack:
            tags = [tag for tag, _lines in stack]
            raise TemplateError("%s::\n  %s ('%s')" % (filepath, _BLOCKENDS,
                    ", ".join(tags)))
        self.blocks[':'] = lines

    def text(self, tag=None):
        """Return the tex-block with tag <tag>. If no block is given,
        return the whole template.
        """
        return '\n'.join(self.blocks[tag] if tag else self.lines)

    def allkeys(self, tag=None):
        """Return a set of all keys in the given block (tag).
        If no block is given, search the whole template.
        """
        return set(RX_SUB.findall(self.text(tag)))

    def substitute(self, sdict, tag, text=None):
        """Substitute keys in the block <tag> using the mapping <sdict>.
        If no block is given, use the whole template.
        Return a tuple (new text, {substituted keys}, {unsubstituted keys}).
        """
        return substitute(self.text(tag), sdict)

    def insert(self, block, tag, tex):
        """Insert the tex-string <tex> at the tag <tag> in the block
        with tag <block>.
        """
        return self.text(block).replace(SUB_BLOCK % tag, tex)

    def insert_and_substitute(self, sdict, block, **tags):
        """Insert text at the given tags into the block with tag <block>,
        then use the mapping <sdict> to substitute keys.
        If no <block> is given, use the whole template.
        <tags> has the form {tag: text}.
        Return a tuple (new text, {substituted keys}, {unsubstituted keys}).
        """
        tex = self.text(block)
        for tag, text in tags:
            tex = tex.replace(SUB_BLOCK % tag, text)
        return substitute(tex, sdict)

    @staticmethod
    def makepdf(ustring):
        return lualatex2pdf(ustring)


if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    print(' --->', substitute("TEST TEMPLATE\n"
            "First (*Substitution.1*).\n"
            "Second: (*S2*), (*S_2*).\n"
            "With space: (*a b*).\n"
            "With escapes: (*%~\\\\{...}*).\n"
            "Non-ASCII: (*übrig*).\n"
            "????: (*S3*)."
            ,
            {"Substitution.1": "FRED", "S2": "$100 for <Fred>"}))

#TODO: use program-internal keys ...
    sdict0 = {
        'Schule': 'Freie Michaelschule',
        'Klasse': '11',
        'Schuljahr': '2019 – 2020',
#        'Zeugnis': 'Abgangszeugnis',
#        'Zeugnis': 'Abschlusszeugnis',
        'Zeugnis': 'Zeugnis',
        'Massstab': 'Maßstab Gymnasium',
#        'Massstab': 'Erweiterter Sekundarabschluss I',
#        'abschluss': 'x',
#        'abschluss': 'a',
        'abschluss': '0',
#        'gleichstellung': 'h',
        'I.DAT': '15.07.2020',
        'P.G.ORT': 'Burgwedel',
        'P.G.DAT': '02.12.2002',
        'P.E.DAT': '01.08.2009',
        'P.VORNAMEN': 'Lucia Caterina Lisanne',
        'P.X.DAT': '15.07.2020',
        'Jahrgang': '11',
        'P.NACHNAME': 'Binder',

        'Fach.01': 'Deutsch', 'Note.01': 'sehr gut',
        'Fach.02': 'Englisch', 'Note.02': 'gut',
        'Fach.03': 'Französisch', 'Note.03': 'befriedigend',
        'Fach.04': 'Kunst', 'Note.04': 'gut',
        'Fach.05': 'Musik', 'Note.05': 'gut',
        'Fach.06': 'Geschichte', 'Note.06': 'gut',
        'Fach.07': 'Sozialkunde', 'Note.07': 'befriedigend',
        'Fach.08': 'Religion', 'Note.08': 'gut',
        'Fach.09': 'Mathematik', 'Note.09': 'befriedigend',
        'Fach.10': 'Biologie', 'Note.10': 'sehr gut',
        'Fach.11': 'Chemie', 'Note.11': 'gut',
        'Fach.12': 'Physik', 'Note.12': 'mangelhaft',
        'Fach.13': 'Sport', 'Note.13': 'gut',
        'Fach.14': '––––––––––', 'Note.14': '––––––––––',
        'Fach.15': '––––––––––', 'Note.15': '––––––––––',
        'Fach.16': '––––––––––', 'Note.16': '––––––––––',

        'FachKP.01': 'Eurythmie', 'NoteKP.01': 'sehr gut',
        'FachKP.02': 'Buchbinden', 'NoteKP.02': 'gut',
        'FachKP.03': 'Kunstgeschichte', 'NoteKP.03': '––––––',
        'FachKP.04': '––––––––––', 'NoteKP.04': '––––––––––',
        'FachKP.05': '––––––––––', 'NoteKP.05': '––––––––––',
        'FachKP.06': '––––––––––', 'NoteKP.06': '––––––––––',
        'FachKP.07': '––––––––––', 'NoteKP.07': '––––––––––',
        'FachKP.08': '––––––––––', 'NoteKP.08': '––––––––––',
    }

#TODO: This could perhaps be part of the <substitute> function?
    sdict = {k.replace('_', '.'): v for k, v in sdict0.items()}

    t = Template('Notenzeugnis-SI.tex')
    print("\nKeys:", t.allkeys())
    t1, s, u = t.substitute(sdict, 'body')
    print("\nSubstituted:", t1)
    print("\nsubbed", s)
    print("\nunsubbed", u, "\n")

    # Make multiple copies of body
    tex = '\n\n\\newpage\n\n'.join([t1]*30)
    # Insert in frame
    texfile = t.insert(':', 'body', tex)
    pdf = t.makepdf(texfile)
    if pdf:
        with open('file.pdf', 'wb') as fout:
            fout.write(pdf)
        print("\Generated file.pdf")
