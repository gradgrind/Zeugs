### python >= 3.7
# -*- coding: utf-8 -*-
"""
core/run_extern.py

Last updated:  2020-10-27


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

# Commands
LUALATEX = 'lualatex'

# Messages
_COMMANDNOTPOSSIBLE = "Befehl '{cmd}' konnte nicht ausgeführt werden"
_NOPDF              = "Keine PDF-Datei wurde erstellt"

#----------------------------------------------------------------------#
import os, platform, subprocess, tempfile


def run_extern(command, *args, cwd = None, xpath = None, feedback = None):
    """Run an external program.
    Pass the command and the arguments as individual strings.
    The command must be either a full path or a command known in the
    run-time environment (PATH).
    Named parameters can be used to set:
     - cwd: working directory. If provided, change to this for the
       operation.
     - xpath: an additional PATH component (prefixed to PATH).
     - feedback: If provided, it should be a function. It will be called
         with each line of output as this becomes available.
    Return a tuple: (return-code, message).
    return-code: 0 -> ok, 1 -> fail, -1 -> command not available.
    If return-code >= 0, return the output as the message.
    If return-code = -1, return a message reporting the command.
    """
#TODO: Is timeout appropriate?
# Not for subprocess.Popen!
    params = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'universal_newlines':True
    }
    if not feedback:
        params['timeout'] = 30  # timeout in seconds
    my_env = os.environ.copy()
    if platform.system() == 'Windows':
        # Suppress the console
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        params['startupinfo'] = startupinfo
    if xpath:
        # Extend the PATH for the process
        my_env['PATH'] = xpath + os.pathsep + my_env['PATH']
        params['env'] = my_env
    if cwd:
        # Switch working directory for the process
        params['cwd'] = cwd

    cmd = [command] + list(args)
    try:
        if feedback:
            out = []
            with subprocess.Popen(cmd, bufsize=1, **params) as cp:
                for line in cp.stdout:
                    l = line.rstrip()
                    out.append(l)
                    feedback(l)
            msg = '\n'.join(out)

        else:
            cp = subprocess.run(cmd, **params)
            msg = cp.stdout

        return (0 if cp.returncode == 0 else 1, msg)

    except FileNotFoundError:
        return (-1, _COMMANDNOTPOSSIBLE.format(cmd=repr(cmd)))


def lualatex2pdf(tex, runs=1, errorhandler=None):
    """Run lualatex on the given string (<tex>).
    Return the generated pdf as <bytes>.
    If the conversion fails, call <errorhandler> with a message and
    return <None>.
    If there is no <errorhandler>, <print> is used.
    """
    def texcompile(texfile):
        rc, msg = run_extern(LUALATEX,
                '-interaction=batchmode',
                '-halt-on-error',
                texfile,
                cwd=os.path.dirname(texfile))
        if rc == 0:
            return None
        elif rc == 1:
            with open(texfile.rsplit('.', 1)[0] + '.log', 'r',
                    encoding='utf-8') as fin:
                log = []
                for line in fin:
                    if log or line[0] == '!':
                        log.append(line.rstrip())
            return '\n'.join(log)
        else:
            return msg

#TODO:
    wdir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__))), 'workingdir')

    with tempfile.TemporaryDirectory(dir=wdir) as td:
        filebase = os.path.join(td, 'file')
        texfile = filebase + '.tex'
        with open(texfile, 'w', encoding='utf-8') as fout:
            fout.write(tex)
        run = 0
        while runs > run:
            run += 1
            msg = texcompile(texfile)
            if msg:
                if errorhandler:
                    errorhandler(msg)
                else:
                    print(msg, flush=True)
                return None

        # Get pdf as bytes
        try:
            with open(filebase + '.pdf', 'rb') as fin:
                pdf = fin.read()
        except FileNotFoundError:
            msg = _NOPDF
            if errorhandler:
                errorhandler(msg)
            else:
                print(msg, flush=True)
            return None

    return pdf
