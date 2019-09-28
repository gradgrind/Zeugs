#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz_io/support.py

Last updated:  2019-07-11

Use of supporting applications.

Requirements:
    - libreoffice for grade reports and the outer sheets of text reports
    - tex with xelatex support for the text report bodies

=+LICENCE=============================
Copyright 2017-2019 Michael Towers

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

#TODO: Some functions are not up-to-date. There are still references to
# WZINFO and wzbase, which are no longer provided.

#TODO: read pdf page sizes (for automatic printer selection?
"""
>>> from pdfrw import PdfReader
>>> pdf = PdfReader('example.pdf')
>>> pdf.pages[0].MediaBox
['0', '0', '595.2756', '841.8898']

Lengths are given in points (1 pt = 1/72 inch). The format is ['0', '0', width, height]
"""

_MAKEPDF                = "PDF-Dateien werden erstellt ..."
_MISSINGPDF             = ".. {path} FEHLT"
_GENPDFFAILED           = "PDF-Erstellung schlug fehl"
_GENPDFFAILLOG          = "PDF-Erstellung schlug fehl, siehe log-Datei:\n  {path}"
_MADEPDF                = "PDF-Datei wurde erstellt: {name}.pdf"
#InstallTexLivePackages:    TeX Live Pakete werden installiert ...
#InstallOK:                 Installation erfolgreich beendet
#InstallFailed:             Installation schlug fehl
_PRINTJOBFAILED         = "Druckauftrag schlug fehl: {name}"
_PRINTJOBSENT           = "Die Datei '{name}' wurde an den Drucker gesendet"
_NOPDF                  = "Die PDF-Datei muss zuerst erstellt werden:\n  {path}"
_NOFILEMANAGER          = ("Öffnen des Dateimanagers für das Betriebssytem"
                        " '{ostype}' ist nicht unterstützt")
_OUTPUT                 = ":> {text}"
_NOPATH                 = "Kein Eintrag in 'APPS'-Datei für Befehl '{cmd}'"
_COMMANDNOTPOSSIBLE     = "Befehl '{cmd}' konnte nicht gestartet werden"

import os, platform, shutil, subprocess
from time import sleep

from pdfrw import PdfReader, PdfWriter, PageMerge


def run_extern (command, *args, cwd=None, xpath=None,
        capture_output=False, feedback=False):
    """Run an external program.
    Pass the command and the arguments as individual strings.
    The command must be an entry in the 'paths' file (in the support folder).
    Named parameters can be used to set:
     - cwd: working directory
     - xpath: an additional PATH component (prefixed to PATH)
     - capture_output: <True> -> return the output of the command
         (otherwise it goes to standard output)
     - feedback: <True> -> output will be shown in info-pane, updating
         at regular intervals
    Return a tuple: (return-code, message).
    return-code: 0 -> ok, 1 -> fail, -1 -> command not available.
    If <capture_output> is true and return-code >= 0, return the output
    as the message.
    """
    params = {'universal_newlines':True}
    my_env = os.environ.copy ()
    if capture_output:
        params ['stdout'] = subprocess.PIPE
        params ['stderr'] = subprocess.STDOUT
    if platform.system () == 'Windows':
        # Suppress the console
        startupinfo = subprocess.STARTUPINFO ()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        params ['startupinfo'] = startupinfo
    if xpath:
        # Extend the PATH
        my_env ['PATH'] = xpath + os.pathsep + my_env ['PATH']
        params ['env'] = my_env
    if cwd:
        # Switch working directory
        params ['cwd'] = cwd

    try:
        cmd = list (CONF.APPS [command])
        if cmd [0] == '*':
            cmd = os.path.join (WZINFO.BASE_DIR, 'support', cmd [1:])
    except:
        return (-1, _NOPATH.format (cmd=command))
    try:
        for a in args:
            cmd.append (a)

        if feedback:
            out = []
            with subprocess.Popen (cmd, bufsize=1, **params) as cp:
                for line in cp.stdout:
                    l = line.rstrip ()
                    out.append (l)
                    REPORT.Background (l)
            msg = '\n'.join (out)

        else:
            cp = subprocess.run (cmd, **params)
            msg = cp.stdout

        return (0 if cp.returncode == 0 else 1, msg)

    except FileNotFoundError:
        return (-1, _COMMANDNOTPOSSIBLE.format (cmd=repr (cmd)))


def openFileBrowser (folder):
    if WZINFO.OSTYPE == "linux":
        p = subprocess.Popen(['xdg-open', folder])
        p.wait()
    elif WZINFO.OSTYPE == "windows":
        os.startfile (os.path.normpath(folder))
    elif WZINFO.OSTYPE == "osx":
        # OSX: untested
        p = subprocess.Popen(['open', folder])
        p.wait()
    else:
        REPORT.Error (_NOFILEMANAGER, ostype=wzbase.OSTYPE)


def toPdf (folder, *files):
    """Convert the given files (in folder <folder>) to pdf using LibreOffice.
    Run it in the background thread. The converted files are placed in the
    subfolder 'pdf'.
    """
# One call possibility:
#   libreoffice --headless --convert-to pdf --outdir pdf <files>

    ofolder = os.path.join (folder, 'pdf')
    if not files:
        return
    REPORT.Info (_MAKEPDF)
    rc, msg = run_extern ('EXEC_LO', '--headless', '--convert-to' ,'pdf',
            '--outdir', ofolder,
            *[os.path.join (folder, f) for f in files],
            capture_output=True, feedback=True)

    pdf_files = []  # collect paths to pdf files
    if rc == 0:
        # Because the return code doesn't indicate failure in this case,
        # check the existence of the output files:
        for f in files:
            fpdf = f.rsplit ('.', 1) [0] + '.pdf'
            pdfpath = os.path.join (ofolder, fpdf)
#TODO: The number 10 was found empirically – for some reason the files
# don't appear for a while ...
            for i in range (10):
                if os.path.isfile (pdfpath):
#                    print ("++COUNT", i)
                    pdf_files.append (fpdf)
                    break
                sleep (0.1)
            else:
                REPORT.Error (_MISSINGPDF, path=pdfpath)
                continue
    elif rc == 1:
        REPORT.Error (_GENPDFFAILED)
    else:
        REPORT.Error (_OUTPUT, text=msg)
    return ofolder, pdf_files


def tex2pdf (folder, basefile, draft=False):
    """Run xelatex on the given file (<basefile> is without suffix).
    This must be done twice to resolve references (page numbers).
    Remove temporary files. Return <True> if successful.
    Use: xelatex -interaction=batchmode -output-directory=out <input file>
    It creates *.aux, *.log and *.pdf files.
    The additional option "-halt-on-error" makes it a bit easier to find
    an error message in the log file.

    If <draft> is <True>, the macro "\isdraft" is defined in the tex file.
    """
    def texcompile ():
        rc, msg = run_extern ('EXEC_LATEX', '-interaction=batchmode',
                '-halt-on-error',
                (r'\def\isdraft{1} \input{%s}' % basefile) if draft else basefile,
                cwd=folder, capture_output=True)
        if rc == 0:
            return True
        elif rc == 1:
            logfile = wzbase.getBaseDir (wzbase.LOG_DIR, 'xelatex-log')
            if os.path.isfile (logfile):
                os.remove (logfile)
            REPORT.Error (_GENPDFFAILLOG, path=logfile)
            os.rename (os.path.join (folder, basefile + '.log'), logfile)
        else:
            REPORT.Error (_OUTPUT, text=msg)
        return False

    rc = texcompile () and texcompile ()
    if rc:
        REPORT.Info (_MADEPDF, name=basefile)

    # Clean up - remove .log and .aux files
    for filename in os.listdir (folder):
        fs = filename.rsplit ('.', 1)
        if len (fs) == 2 and (fs [1] == 'log' or fs [1] == 'aux'):
            os.remove (os.path.join (folder, filename))

    return rc


#TODO ... This should probably not be here at all, as it is only needed
# for setting up the application.
def texPackages ():
    """For 'TeX Live' only! And then only for a 'manual' installation.
    This should not be used if TeX Live was installed from a Linux package
    manager, etc. In that case the package manager should be used to install
    missing packages.
    This function tries to install the packages listed in the file
    'texlive-packages' in the support folder. If any are already installed
    they will just be skipped.
    On some systems this call may cause packages to be updated.
    """
    tpath = wzbase.getBaseDir (wzbase.SUPPORT_DIR, 'texlive-packages')
    with open (tpath, encoding='utf-8') as fin:
        lines = fin.readlines ()
    packs = []
    for line in lines:
        l = line.strip ()
        if l and l [0] != '#':
            packs.append (l)
    REPORT.Info ('InstallTexLivePackages')
    rc, msg = run_extern ('EXEC_TLMGR', 'install', *packs,
            capture_output=True, feedback=True)
    if rc == 0:
        REPORT.Info ('InstallOK')
        return True
    elif rc == 1:
        REPORT.Error ('InstallFailed', "Installation schlug fehl")
    else:
        REPORT.Error (_OUTPUT, text=msg)
    return False


def toA3 (folder, *files):
    """Convert the given (pdf) files to A3 (from A4) using makeA3.
    """
    ofiles = []
    for f in files:
        fp = os.path.join (folder, f)
        ft = fp.replace ('.pdf', '-A3.pdf')
        ofiles.append (ft)
        makeA3 (fp, ft)
        os.remove (fp)
    return ofiles


def makeA3 (ipath, opath, onesided=False):
    """Take the first 4 (A4) pages of the input file and place them in
    "booklet" order on an A3 sheet (double-sided, short-side join).
    If <onesided> is <True>, or there are only two pages in the input file,
    place the first two (A4) pages on one side of an A3 sheet, the first
    page on the right-hand side.
    Note that the input pages do not have to be A4, the output will simply
    be twice as wide (as the first page). All input pages should have the same size.
    """
    ipages = PdfReader(ipath).pages
    # Make sure we have an even number of pages
    if len(ipages) & 1:
        ipages.append(None)
    fpage = PageMerge ()
    fpage.add (ipages [0])
    width = fpage [0].w
    opages = []
    if onesided or len (ipages) == 2:
        p4 = ipages [1]
    else:
        p4 = ipages [3]
        bpage = PageMerge ()
        bpage.add (ipages [1])
        bpage.add (ipages [2], prepend=True)
        bpage [0].x = width
        opages.append (bpage.render())
    if p4:
        fpage.add (p4)
    fpage [0].x = width
    opages.insert (0, fpage.render())
    PdfWriter().addpages(opages).write(opath)


def concat (ifiles, ofile):
    """Concatenate the given input files (pdf) to the output file.
    All files with full path.
    """
    writer = PdfWriter()
    for fi in ifiles:
        writer.addpages(PdfReader(fi).pages)
    writer.write(ofile)


def getPrinters ():
    """Return a list of printer names.
    """
    from qtpy.QtPrintSupport import QPrinterInfo
    return QPrinterInfo.availablePrinterNames ()   # -> ['DCPJ515W']
    #qpi = QPrinterInfo.printerInfo ('DCPJ515W')
    #qpi.defaultPageSize ().name () # -> 'Letter'


def toPrinter (pdffile, folder=None):
    """Print the given pdf file. The '.pdf' suffix may be omitted
    in <pdffile>, but the file itself must have this suffix.
    If <folder> is given, <pdffile> is the name of a (pdf-)file within that
    folder. Otherwise <pdffile> is the complete file path.
    The print commands are in the configuration file 'APPS'.
    """
    pdffile, filepath = _filecheck (pdffile, folder)
    if not filepath:
        return False

    command = 'PDF_PRINTER'
    try:
        cmdx = pdffile.rsplit ('-', 1) [1].split ('.') [0]
    except:
        cmdx = ''
    try:
        cmd = list (CONF.APPS.get (command + '_' + cmdx)
                or CONF.APPS.get (command))
    except:
        REPORT.Error (_NOPATH, cmd=command)

    i = 0
    for c in cmd:
        if c == '{filepath}':
            cmd [i] = filepath
        i += 1
    if cmd [0] [0] == '*':
        cmd [0] = os.path.join (WZINFO.BASE_DIR, 'support',
                *cmd [0] [1:].split ('/'))
    cp = subprocess.run (cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True)
    if cp.returncode != 0:
#TODO ...
        REPORT.Error (_PRINTJOBFAILED, name=pdffile, x=True)
        return False
    else:
        REPORT.Info (_PRINTJOBSENT, name=pdffile)
        return True


#TODO ...
def makeDraft (pdffile, folder=None, printername=None):
    """Make a "draft" version of the given pdf file by adding a watermark.
    Print this file and then delete it. The '.pdf' suffix may be omitted
    in <pdffile>, but the file itself must have this suffix.
    If <folder> is given, <pdffile> is the name of a (pdf-)file within that
    folder. Otherwise <pdffile> is the complete file path.
    If <printername> is given, it must be the name of a known printer.
    If no <printername> is given, the system default printer is used.
    """
    pdffile, filepath = _filecheck (pdffile, folder)
    if not filepath:
        return False

    wmarkfn = Configuration.getFormsDir ('Draft.pdf')
    wmark = PageMerge().add(PdfReader(wmarkfn).pages[0])[0]
    underneath = True
    opath = os.path.join (os.path.dirname (filepath), "Entwurf.pdf")
    reader = PdfReader(filepath)
    for page in reader.pages:
        PageMerge(page).add(wmark, prepend=underneath).render()
    PdfWriter().write(opath, reader)
    rc = toPrinter (opath, printername=printername)
    if rc:
        # delete the draft file
        os.remove (opath)
    return rc


def _filecheck (pdffile, folder):
    if not pdffile.endswith ('.pdf'):
        pdffile += '.pdf'
    if folder:
        filepath = os.path.join (folder, pdffile)
    else:
        filepath = pdffile
        pdffile = os.path.basename (pdffile)
    if not os.path.isfile (filepath):
#TODO ...
        REPORT.Error (_NOPDF, path=filepath, x=True)
        filepath = None
    return (pdffile, filepath)
