#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_io/passwords.py

Last updated:  2020-05-31

Generate random passwords/passphrases.


=+LICENCE=============================
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

=-LICENCE========================================
"""

import random
import string
import gzip
import re
from collections import OrderedDict


punctuation = '.-_#+=)(/%!'
CHARLIST = string.ascii_letters + string.digits + punctuation
TO_ASCII = {'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'Ä': 'AE', 'Ö': 'OE', 'Ü': 'UE'}
ASCIIFAIL = '?'
NOSEP = string.ascii_letters + string.digits + ''.join (TO_ASCII) + ASCIIFAIL

_LOWERNEEDSSEP = "Passphrase: Ohne Großbuchstaben muss es ein Trennzeichen geben."
_BADSEP = "Passphrase: Das angegebene Trennzeichen ist nicht gültig."


class _PassWordError (ValueError):
    pass

class Password:
    def __init__ (self, n, words=None,
            # Passphrase options (<words> = path to words.gz or words.txt):
            sep=None, tolower=False, toASCII=False):
        self.random = random.SystemRandom()
        if words != None:
            # Read and process word list.
            if words.endswith ('.gz'):
                with gzip.open (words, 'rt', encoding='utf-8') as fh:
                    wordlist = fh.read ().splitlines ()
            else:
                with open(words, encoding='utf-8') as fh:
                    wordlist = fh.read ().splitlines ()

            # Use a mapping to retain the order and suppress duplicates
            _wordlist = OrderedDict ()
            self.sep = sep
            if sep == None:
                for word in wordlist:
                    _word = word [0].upper () + word [1:]
                    if toASCII:
                        _word = asciify (_word)
                    _wordlist [_word] = None

                self.sep = ''
                if tolower:
                    raise _MyError (_LOWERNEEDSSEP)

            elif sep in NOSEP:
                raise _MyError (_BADSEP)

            elif tolower:
                for word in wordlist:
                    _word = word.lower ()
                    if toASCII:
                        _word = asciify (_word)
                    _wordlist [_word] = None

            else:
                for word in wordlist:
                    if toASCII:
                        word = asciify (word)
                    _wordlist [word] = None

            self.words = list (_wordlist)
            if n == None or n < 3:
                n = 4  # default

        else:
            self.words = None
            if n == None or n < 3:
                n = 10  # default

        self.n = n


    def get (self):
        if self.words == None:
            # Password
            while True:
                password = ''.join (self.random.choice (CHARLIST)
                        for i in range (self.n))

                if (    any (c.islower () for c in password)
                        and any (c.isupper () for c in password)
                        and any (c in punctuation for c in password)
#                        and sum (c.isdigit () for c in password) >= 2):
                        and any (c.isdigit () for c in password)):
                    return password

        # Passphrase
        # Assuming the table is sorted according to word frequency
        # (most common first), a phrase is accepted if it has at least
        # one less common word.
        wn = len (self.words)
#        print ("Choose %d from %d words" % (self.n, wn))
        barrier = wn // 2
        while True:
            words = []
            test = 0
            for i in range (self.n):
                p = self.random.randrange (wn)
                words.append (self.words [p])
                if p >= barrier:
                    test += 1
            if test > 1:
                return self.sep.join (words)


def asciify (string):
    """This converts a utf-8 word to ASCII, to avoid possible typing
    difficulties.
    """
    def rsub (m):
        c = m.group (0)
        try:
            return TO_ASCII [c]
        except:
            return ASCIIFAIL

    return re.sub (r'[^A-Za-z0-9-.]', rsub, string)


def pp (p):
    print (" ->", p, len (p))

if __name__ == '__main__':
    password = Password (None)
    for i in range (10):
        pp (password.get ())


#    pp (Password (None, words='words.gz').get ())
#    pp (Password (None, words='words.gz', sep = ' ').get ())
#    pp (Password (None, words='words.gz', sep = ' ', toASCII=True).get ())
#    pp (Password (None, words='words.gz', sep='_', tolower=True).get ())
