### python >= 3.7
# -*- coding: utf-8 -*-

"""
template_engine/template_sub.py

Last updated:  2020-09-26

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
        if not filename.endswith('.tex'):
            filename += '.tex'
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

    sdict0 = {
        'CLASS': '11',              # ?
        'CLASSYEAR': '11',          # ?
        'SCHOOLYEAR': '2019 – 2020',
#        'REPORT': 'Abgangszeugnis',
#        'REPORT': 'Abschlusszeugnis',
        'REPORT': 'Zeugnis',
        'LEVEL': 'Maßstab Gymnasium',   # Sek I, not Abschluss
#        'LEVEL': 'Erweiterter Sekundarabschluss I',    # Abschluss only
#        'abschluss': 'x',
#        'abschluss': 'a',
#        'abschluss': '0',
        'abschluss': 'v',
#        'gleichstellung': 'h',
#       'gleichstellung': '0',
        'ISSUE.D': '15.07.2020',    # always
        'V.D': '06.07.2020',        # Versetzung only (Zeugnis 11.Gym, 12.Gym)

# Pupil data
        'POB': 'Burgwedel',
        'DOB.D': '02.12.2002',
        'ENTRY.D': '01.08.2009',
        'FIRSTNAMES': 'Lucia Caterina Lisanne',
        'LASTNAME': 'Binder',
        'EXIT.D': '15.07.2020',     # Abschluss / Abgang only

        'S.V.01': 'Deutsch', 'G.V.01': 'sehr gut',
        'S.V.02': 'Englisch', 'G.V.02': 'gut',
        'S.V.03': 'Französisch', 'G.V.03': 'befriedigend',
        'S.V.04': 'Kunst', 'G.V.04': 'gut',
        'S.V.05': 'Musik', 'G.V.05': 'gut',
        'S.V.06': 'Geschichte', 'G.V.06': 'gut',
        'S.V.07': 'Sozialkunde', 'G.V.07': 'befriedigend',
        'S.V.08': 'Religion', 'G.V.08': 'gut',
        'S.V.09': 'Mathematik', 'G.V.09': 'befriedigend',
        'S.V.10': 'Biologie', 'G.V.10': 'sehr gut',
        'S.V.11': 'Chemie', 'G.V.11': 'gut',
        'S.V.12': 'Physik', 'G.V.12': 'mangelhaft',
        'S.V.13': 'Sport', 'G.V.13': 'gut',
        'S.V.14': '––––––––––', 'G.V.14': '––––––––––',
        'S.V.15': '––––––––––', 'G.V.15': '––––––––––',
        'S.V.16': '––––––––––', 'G.V.16': '––––––––––',

        'S.K.01': 'Eurythmie', 'G.K.01': 'sehr gut',
        'S.K.02': 'Buchbinden', 'G.K.02': 'gut',
        'S.K.03': 'Kunstgeschichte', 'G.K.03': '––––––',
        'S.K.04': '––––––––––', 'G.K.04': '––––––––––',
        'S.K.05': '––––––––––', 'G.K.05': '––––––––––',
        'S.K.06': '––––––––––', 'G.K.06': '––––––––––',
        'S.K.07': '––––––––––', 'G.K.07': '––––––––––',
        'S.K.08': '––––––––––', 'G.K.08': '––––––––––',
    }

#TODO: This could perhaps be part of the <substitute> function?
    sdict = {k.replace('_', '.'): v for k, v in sdict0.items()}

    t = Template('Notenzeugnis-SI.tex')
    print("\nKeys:", sorted(t.allkeys()))

#    quit(0)

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
