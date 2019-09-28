#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_core/reporting.py

Last updated:  2019-09-25

Handle the basic reporting needs of the program.
Supports various error levels and other informative output.


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

class Report:
    """Handle reporting.
    Messages are collected in a list of tuples (error code, message).
    They can be retrieved (emptying the list) by calling the <messages>
    method.
    The method <printMessages> outputs the messages sequentially with a
    little formatting. By default the output is sent to "stdout", but it
    is also possible to pass an open file object to the constructor.
    """
    ### The 'structural' methods
    def __init__ (self, ofile=None):
        self._ofile = ofile
        self._report = []

    def messages (self):
        msgs = self._report
        self._report = []
        return msgs

    def PRINT (self, *args):
        print (*args, file=self._ofile)

    def printMessages (self):
        for mt, msg in self.messages ():
            if mt [0] == '-':
                self.PRINT (msg)
            elif mt [0] >= '4':
                self.PRINT ("\n *****", mt.split ('_', 1) [1], "*****")
                self.PRINT (msg)
                self.PRINT ("------------------------------------\n")
            else:
                self.PRINT ("::: %s:" % mt.split ('_', 1) [1], msg)

    def out (self, etype, msg, **kargs):
        self._report.append ((etype, msg.format (**kargs) if kargs else msg))


    ### The methods actually used for reporting
    def Info (self, msg, **kargs):
        self.out ("2_Info", msg, **kargs)

    def Error (self, msg, **kargs):
        self.out ("6_Error", msg, **kargs)

    def Fail (self, msg, **kargs):
        self.out ("8_ERROR", msg, **kargs)
        raise RuntimeError ("REPORT.Fail")

    def Warn (self, msg, **kargs):
        self.out ("4_Warning", msg, **kargs)

    def Bug (self, msg, **kargs):
        self.out ("9_BUG", msg, **kargs)
        raise RuntimeError ("REPORT.Bug")

    def Background (self, msg):
        self.out ("0_Output", msg)

    def Test (self, msg):
        self.out ("-", msg)
