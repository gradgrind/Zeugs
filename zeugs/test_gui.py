# python >= 3.7
# -*- coding: utf-8 -*-
"""
test_gui.py

Last updated:  2020-02-01

Gui-wrapper for the flask server and browser starter.


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

import os, platform, subprocess, threading, webbrowser
from queue import Queue, Empty

# tkinter must be installed, e.g. deb package python3-tk
from tkinter import Tk, scrolledtext, Button, PhotoImage


class RunExtern:
    def __init__(self, command, *args, cwd=None, xpath=None, xenv=None):
        """Run an external program.
        Pass the command and the arguments as individual strings.
        <command> is the executable (either absolute, relative or in PATH)
        to be run.
        Named parameters can be used to set:
         <cwd>: working directory
         <xpath>: an additional PATH component (prefixed to PATH)
         <xenv>: a mapping containing environment values
        """
        self.params = {'universal_newlines':True}
#        my_env = os.environ.copy()      # use existing os environment
        my_env = xenv or {}
        # Capture subprocess output (both stdout and stderr):
        self.params['stdout'] = subprocess.PIPE
        self.params['stderr'] = subprocess.STDOUT
        if platform.system() == 'Windows':
            # Suppress the console
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.params['startupinfo'] = startupinfo
        if xpath:
            # Extend the PATH
            my_env['PATH'] = xpath + os.pathsep + my_env['PATH']
        self.params['env'] = my_env
        if cwd:
            # Switch working directory
            self.params['cwd'] = cwd

        self.cmd = [command]
        for a in args:
            self.cmd.append(a)


    def start(self, feedback):
        """Start the subprocess.
        <feedback>: object handling line output and waiting.
        """
        self.feedback = feedback
        # Start subprocess
        self.process = subprocess.Popen(self.cmd, bufsize=1, **self.params)
        # Read output from process in separate thread.
        # Get output via queue.
        self.q = Queue()
        self.thread = threading.Thread(target=self.readoutput)
        #? , daemon=True)
        self.thread.start()
        # Start polling queue
        self.feedback.wait(500, self.poll)    # delay in ms.


    def readoutput(self):
        for line in self.process.stdout:
            self.q.put(line)


    def poll(self):
        try:
            while True:
                self.feedback.print(self.q.get_nowait())
        except Empty:
            self.feedback.wait(500, self.poll)    # delay in ms.


    def terminate(self):
        self.process.terminate()



class Window(Tk):
    def __init__(self, title, program):
        super().__init__()
        self.title(title)
        self.text = scrolledtext.ScrolledText(self, width=80, height=25)
        self.text.grid(column=0, row=0, columnspan=3, sticky="nsew")

        btn = Button(self, text="Start Browser", command=self.visit, width=12)
        btn.grid(column=2, row=1, sticky="e")

        btn = Button(self, text="Quit", command=self.quit, width=12)
        btn.grid(column=1, row=1, sticky="e")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, pad=3)
        self.columnconfigure(2, pad=3)
        self.rowconfigure(1, pad=3)

        self.program = program
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.program.start(self)
        self.wait(1000, self.visit)


    def wait(self, delay, f):
        self.after(delay, f)


    def visit(self):
        webbrowser.open_new("http://127.0.0.1:%s/" % PORT)
        self.wm_state("iconic")


    def quit(self):
        self.program.terminate()
        quit()


    def print(self, text):
        fully_scrolled_down = self.text.yview()[1] == 1.0
        self.text.insert("end", text)
        if fully_scrolled_down:
            self.text.see("end")

basedir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
PORT = "5005"
xenv = {
    "FLASK_APP": "flask_app",
    "FLASK_ENV": "development",
    "FLASK_RUN_PORT": PORT,
    "ZEUGS_BASE": basedir
}

pexec = os.path.join(basedir, "venv", "bin", "python")
program = RunExtern(pexec, "-m", "flask", "run", xenv=xenv)

window = Window("Zeugs server", program)
window.iconphoto(False, PhotoImage(file=os.path.join(basedir, 'favicon.png')))
window.mainloop()
