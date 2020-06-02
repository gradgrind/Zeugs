### python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_io/passwords.py

Last updated:  2020-06-02

Generate random passwords.


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
"""

import os, random, re, string, gzip

from wz_core.configuration import Paths


special_characters = r'%&/()=+_#*;:<>@{}'   # At least one is compulsory
special_characters2 = r'.,$[]~-'            # May be included
pw_minlength = 10
pp_minlength = 30
pp_minwords = 5

class Password:
    pw_length = "Ein Passwort muss mindestens %d Zeichen haben." % pw_minlength
    pp_words = "Eine Passphrase muss mindestens %d Wörter enthalten." % pp_minwords
    pp_length = "Eine Passphrase muss mindestens %d Zeichen haben." % pp_minlength
    pp_psc = ("Eine Passphrase muss mindestens ein Sonderzeichen haben: %s"
                    % special_characters)
    pw_chars = [
            ('a-z', 2, "Ein Passwort muss mindestens zwei Kleinbuchstaben (a – z) haben."),
            ('A-Z', 2, "Ein Passwort muss mindestens zwei Großbuchstaben (A – Z) haben."),
            ('0-9', 2, "Ein Passwort muss mindestens zwei Ziffern (0 – 9) haben."),
            (special_characters, 1,
                    "Ein Passwort muss mindestens ein Sonderzeichen haben: %s"
                    % special_characters)
        ]
    pw_illegal = "Das Passwort darf folgende Zeichen nicht enthalten: %s"
    allchars = string.ascii_letters + string.digits + special_characters
#
#
    @classmethod
    def checkStrength(cls, pw):
        """Do a basic check on the strength of a password.
        """
        fail = []
        words = pw.split()
        if len(words) > 1:
            if len(words) < pp_minwords:
                fail.append(cls.pp_words)
            else:
                # Accept passphrases with enough words if also the total
                # length is large enough (not a great test!)
                pw = ' '.join(words)
                if len(pw) < pp_minlength:
                    fail.append(cls.pp_length)
                if not re.search('[%s]' % special_characters, pw):
                    fail.append(cls.pp_psc)
                return fail
            return fail
        if len(pw) < pw_minlength:
            fail.append(cls.pw_length)
        pn = pw
        for ch, n, msg in cls.pw_chars:
            pn, n1 = re.subn('[%s]' % ch, '', pn)
            if n1 < n:
                fail.append(msg)
        if pn:
            chx = [ch for ch in pn if ch not in special_characters2]
            if chx:
                fail.append(cls.pw_illegal % ''.join(chx))
        return fail
#
#
    @classmethod
    def new(cls):
        rnd = random.SystemRandom()
        while True:
            n = rnd.randrange(pw_minlength + 2)
            password = ''.join (rnd.choice(cls.allchars)
                    for i in range (n))
            if not cls.checkStrength(password):
                return password
#
#
    @staticmethod
    def passphrase(n = pp_minwords):
        """Generate a pass phrase consisting of random words from a word
        list (utf-8, one word per line).
        """
        # Read and process word list (file with one word per line).
        wordsfile = Paths.getUserFolder('words.gz')
        if os.path.isfile(wordsfile):
            with gzip.open(wordsfile, 'rt', encoding = 'utf-8') as fh:
                wordlist = fh.read().splitlines()
            # Pick a random selection of words from the list
            rnd = random.SystemRandom()
            wn = len(wordlist)
            words = []
            for i in range(n):
                p = rnd.randrange(wn)
                words.append(wordlist[p])
            return ' '.join(words)
        return None


##################### Test functions
def test_01():
    REPORT.Test("Character frequencies:")
    dist = {}
    for i in range(1000):
        pw = Password.new()
        for c in pw:
            try:
                dist[c] += 1
            except:
                dist[c] = 1
    freq = {}
    for c, n in dist.items():
        try:
            freq[n].add(c)
        except:
            freq[n] = {c}
    for n in sorted(freq, reverse = True):
        REPORT.Test("   %s: %d" % (freq[n], n))

def test_02():
    REPORT.Test("Check passwords:")
    for pw in 'notverysecret', 'AVeryGoodPassword01%':
        REPORT.Test("  %s: %s" % (pw, repr(Password.checkStrength(pw))))

def test_03():
    REPORT.Test("Check passphrases:")
    for pp in 'Far too short', 'A very good passphrase is long&':
        REPORT.Test("  %s:\n        %s" % (pp, repr(Password.checkStrength(pp))))

def test_04():
    return
#TODO: test passphrase generation
