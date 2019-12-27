#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_core/reporting.py

Last updated:  2019-12-26

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

import traceback


class Report:
    """Handle reporting.
    Messages are collected in a list of tuples (error code, message).
    They can be retrieved (emptying the list) by calling the <messages>
    method.
    The method <printMessages> outputs the messages sequentially with a
    little formatting. By default the output is sent to "stdout", but it
    is also possible to set a file-path: attribute <logfile>.
    A further possibility is to supply the method <getLogFile> which
    returns a file-path. This method takes the message list as argument,
    allowing additional handling of the messages.
    """
    class RuntimeFail(RuntimeError):
        pass

    class RuntimeBug(RuntimeError):
        pass

    ### The 'structural' methods
    def __init__ (self):
        self.logfile = None # defaults to stdout
        # A function to determine the output file, by default undefined:
        self.getLogfile = None
        self._report = []

    def messages (self):
        msgs = self._report
        self._report = []
        return msgs

    def printMessages(self):
        messages = self.messages()
        try:
            outfile = self.getLogfile(messages)
        except:
            # Output to default/fallback log
            outfile = self.logfile
        try:
            fh = (open(outfile, 'a', encoding='utf-8', newline='')
                    if outfile else None)
            for mi, mt, msg in messages:
                if mi >= 4:
                    print("\n *****", mt, "*****", file=fh)
                    print(msg, file=fh)
                    print("------------------------------------\n", file=fh)
                else:
                    print("::: %s:" % mt, msg, file=fh)
        finally:
            if fh:
                fh.close()

    def out (self, enum, etype, msg, **kargs):
        self._report.append ((enum, etype, msg.format (**kargs) if kargs else msg))


    def wrap(self, f, *args, **kargs):
        """Wrap a call to the given function <f>, with the given arguments.
        Exceptions are trapped and finally <printMessages> is called.
        """
        try:
            return f(*args, **kargs)
        except (self.RuntimeFail, self.RuntimeBug):
            pass
        except:
            self.out(10, "Trap", traceback.format_exc())
        finally:
            self.printMessages()


    ### The methods actually used for reporting
    def Test(self, msg):
        self.out(-1, "Test", msg)

    def Background(self, msg):
        self.out(0, "Output", msg)

    def Info(self, msg, **kargs):
        self.out(2, "Info", msg, **kargs)

    def Warn(self, msg, **kargs):
        self.out(4, "Warning", msg, **kargs)

    def Error(self, msg, **kargs):
        self.out(6, "Error", msg, **kargs)

    def Fail(self, msg, **kargs):
        self.out(8, "Fail", msg, **kargs)
        raise self.RuntimeFail

    def Bug(self, msg, **kargs):
        self.out(9, "Bug", msg, **kargs)
        raise self.RuntimeBug
