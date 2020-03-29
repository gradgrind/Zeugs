#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search.py

Last updated:  2020-03-28

A utility for searching the source files for particular text strings.
This is not used by the programm itself, but it may be useful for tracing
the use of names.

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

import os, fnmatch
import sys, builtins

thisdir = os.path.dirname (os.path.realpath ( __file__ ))
appdir = os.path.dirname (thisdir)
basedir = os.path.dirname (appdir)
# This is the path for test data:
userdir = os.path.join (basedir, 'TestData')


def search_dir (dpath, searchstring, mask='*', deep=True):
    #print ('DIR: %s' % dpath)
    dirs = []
    output = []
    for fname in os.listdir (dpath):
        fpath = os.path.join (dpath, fname)
        if os.path.isdir (fpath):
            dirs.append (fpath)
        elif fnmatch.fnmatch (fname, mask):
            try:
                #print ('  --', fpath)
                with open (fpath, encoding='utf-8') as fin:
                    lix = 0
                    found = False
                    while True:
                        line = fin.readline ()
                        if not line:
                            break
                        lix += 1
                        if searchstring in line:
                            if not found:
                                output.append ('\n  in %s' % fname)
                                found = True
                            output.append ('    l. %04d: %s' % (lix, line.rstrip ()))
            except UnicodeDecodeError:
                # Ignore non-utf-8 files
                pass
    if output:
        print ('\n  - - - - - - -\n DIR: %s' % dpath)
        for line in output:
            print (line)
    if deep:
        for d in dirs:
            if d.endswith ('__pycache__'):
                continue
            search_dir (d, searchstring, mask='*')


def search_appdir (searchstring, mask='*'):
    search_dir (appdir, searchstring, mask)


def search_configs (searchstring):
    search_dir (userdir, searchstring, '*')


if __name__ == "__main__":
    import sys
    sstring = sys.argv [-1]
    print ("Seek '%s'" % sstring)
    if sys.argv[1] == '.':
    	search_appdir (sstring)
    else:
	    search_dir (thisdir, sstring, '*.py')
    quit (0)

    search_appdir ('#TODO', '*.py')
    print ('\n  --------------------------------------------------------\n')
    search_configs ('#TODO')
