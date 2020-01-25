# python >= 3.7
# -*- coding: utf-8 -*-
"""
wz_core/configuration.py

Last updated:  2020-01-25

Configuration items and the handler for the configuration files.

=+LICENCE=================================
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

=-LICENCE=================================
"""

_CONFIGDIR = 'conf'  # folder within user-data folder containing config files

### Messages
_CONFIGDIRFAIL      = "Konfigurationsabschnitt fehlt: {name} in\n   {path}"
_CONFIGITEMFAIL     = "Konfigurationselement existiert nicht: {name} in\n   {path}"
_CONFIGFILEFAIL     = ("Konfigurationsdatei konnte nicht gelesen werden:"
                    "\n   {path}")
_MULTIPLECONFIGKEY  = ("Konfigurationselement mehrfach definiert:"
                    " {name} in\n   {path}")
_CONFIGINVALIDLINE  = ("Konfigurationsdatei '{path}', ungültige Zeile:"
                    "\n   {line}")
_CONFIGNOKEY        = ("In Konfigurationsdatei '{path}':\n"
                    "  Kein Schlüssel für Zeile <{line}>")
_INVALIDDATE        = "Ungültiges Datum: {date}"
_CONFIGNATVAL       = ("In Konfigurationsdatei '{path}':\n"
                    " Ungültige natürliche Zahl, {k} = {val}")
_CONFIGFLOATVAL     = ("In Konfigurationsdatei '{path}':\n"
                    " Ungültige Dezimalzahl, {k} = {val}")
_CONFIGKEYMISSING   = ("In Konfigurationsdatei '{path}':\n"
                    " 'Schlüssel' fehlt ('Schlüssel = Wert' fehlt)")
_PATHSBADPATH       = ("Ungültiger Eintrag in Konfigurationsdatei PATHS:\n"
                    "   {k} = {v}")
_APPENDNONE         = ("In Konfigurationsdatei '{path}':\n"
                    "  Folgezeile nicht erwartet: {line}")


import os, re, glob
from collections import OrderedDict
import datetime
import builtins

from .reporting import Report


def init (userFolder, logfile=None, xlog=None):
    appdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    zeugsdir = os.path.join(os.path.dirname (appdir))
    if os.path.isfile(os.path.join(zeugsdir, 'TESTING')):
        userFolder = os.path.join(zeugsdir, 'TestData')
    elif not userFolder:
        userFolder = os.path.join(zeugsdir, 'zeugs_data')
    builtins.REPORT = Report () # set up basic logging (to console)
    Paths._init (userFolder)
    if logfile:
        REPORT.logfile = logfile
    if xlog:
        REPORT.getLogfile = xlog
    return userFolder


def readFloat (string):
    # Allow spaces (e.g. as thousands separator)
    inum = string.replace (' ', '')
    # Allow ',' as decimal separator
    return float (inum.replace (',', '.'))



class ConfigDir (dict):
    """This is basically a <dict>, but it allows attribute-like
    reading of its items.
    Note that to avoid possible problems with file and directory names,
    these should consist of upper case ASCII letters, numbers and '_' only.
    Lower case letters in the supplied path will be converted to upper
    case, so they may be used for accessing the items. That makes it
    impossible to access configuration folders and files which include
    lower case letters.
    """
    def __getattr__ (self, name):
        """Called when an attribute access fails.
        """
        return self [name]

    def __getitem__ (self, name):
        name = name.upper ()
        if name in self:
            return self.get (name)
        dpath = os.path.join (self._path, name)
        if os.path.isdir (dpath):
            val = ConfigDir (dpath)
        elif os.path.isfile (dpath):
            val = ConfigFile (dpath)
        else:
            REPORT.Fail (_CONFIGDIRFAIL, name=name, path=self._path)

        self [name] = val
        return val

    def __init__ (self, path):
        super ().__init__ ()
        self._path = path

    def list (self):
        return sorted (os.listdir (self._path))



class _ConfigList (tuple):
    """A tuple which retains information about the configuration file and
    key from which it was read. This allows these to be referred to in
    error messages
    """
    def __new__ (cls, cfile, key, vlist):
        self = super ().__new__ (cls, vlist)
        self._cfile = cfile
        self._ckey = key
        return self

    def getSource (self):
        return (self._cfile, self._ckey)



class _ConfigString (str):
    """A string with extra methods and attributes, exclusively for
    use with configuration item values. It retains information about
    the configuration file and key from which it was read.
    """
    def __new__ (cls, cfile, key, vstring):
        self = super ().__new__ (cls, vstring)
        self._cfile = cfile
        self._ckey = key
        return self

    def nat (self, imax=None, imin=0):
        """Convert to an integer, with optional range check.
        """
        try:
            n = int (self)
            if n < imin:
                raise ValueError
            if imax and n > imax:
                raise ValueError
            return n
        except:
            REPORT.Fail (_CONFIGNATVAL, k=self._ckey, val=self,
                    path=self._cfile)

    def float (self):
        """Convert to a floating point value.
        """
        try:
            return readFloat (self)
        except:
            REPORT.Fail (_CONFIGFLOATVAL, k=self._ckey, val=self,
                    path=self._cfile)

    def split (self, splitch = ','):
        """Split the string at <splitch> (default is ',').
        The resulting items are stripped of whitespace left and right.
        """
        return [i.strip () for i in super ().split (splitch)]



class ConfigFile (OrderedDict):
    """This is basically an <OrderedDict>, but it allows attribute-like
    reading of its items.
    Although the file name should be upper case, the contained keys need
    not be. Indeed they can consist of practically any character sequence
    (not '#' or '='), but if they are not valid python identifiers they
    will not be accessible as attributes, but only with the 'd [key]' form.
    An item can be a string (possibly spread over several lines, with or
    without line breaks) or a tuple of strings.
    String items are returned as instances of <_ConfigString>.
    All string values are stripped of whitespace left and right.
    """
    def __getattr__ (self, name):
        """Called when an attribute access fails.
        """
        return self [name]

    def __getitem__ (self, name):
        if name in self:
            return self.get (name)
#TODO: change back to Fail?
        REPORT.Error (_CONFIGITEMFAIL, name=name, path=self._path)
        raise KeyError

    def __init__ (self, fpath):
        """Read in a configuration text and add its contents to the
        <ConfigFile> instance.
        """
        def firstLine (_line):
            _l = _line.lstrip ()
            try:
                l0 = _l [0]
            except IndexError:
                pass
            else:
                if l0 == '|':
                    return _l [1:]
                if l0 in ('+', '/'):
                    REPORT.Fail (_APPENDNONE, path=fpath, line=line)
            return _l

        def clearkey ():
            if key != None:
                if vlist == None:
                    self [key] = _ConfigString (self._path, key, val)
                else:
                    vlist.append (val)
                    self [key] = _ConfigList (self._path, key, vlist)

        super ().__init__ ()
        self._path = fpath
        self._name = os.path.basename (fpath)
        try:
            with open (fpath, encoding='utf-8') as fh:
                text = fh.read ()
        except:
            # Couldn't read file
            REPORT.Fail (_CONFIGFILEFAIL, path=fpath)
            assert False

        key = None
        val = None
        vlist = None
        for line in text.splitlines ():
            line = line.strip ()
            if not line: continue
            if line [0] == '#': continue
            if line [0] == '&':
                # List continuation
                if vlist == None:
                    REPORT.Fail (_CONFIGNOKEY, path=self._path, line=line)
                vlist.append (val)
                val = firstLine (line [1:])
                continue
            try:
                if line [0] == '+':
                    val += line [1:]
                    continue
                if line [0] == '/':
                    val += '\n' + _l [1:]
                    continue
            except:
                REPORT.Fail (_APPENDNONE, path=fpath, line=line)

            try:
                key0, val0 = line.split ('=', 1)
                key0 = key0.rstrip ()
                if not key0:
                    raise KeyError
            except:
                REPORT.Fail (_CONFIGINVALIDLINE, path=self._path, line=line)

            clearkey ()
            vlist = None
            key = key0
            if key in self:
                REPORT.Fail (_MULTIPLECONFIGKEY, name=key, path=self._path)

            if val0 != '' and val0 [0] == '&':
                # List value
                vlist = []
                val = firstLine (val0 [1:])
                continue

            # Normal entry
            val = firstLine (val0)

        clearkey ()



class Paths:
    _userdir = None
    _paths = None
    # For characters which should be substituted in file names:
    _invalid_re = r'[^A-Za-z0-9_.~-]'

    @classmethod
    def _init (cls, userdir):
        cls._userdir = userdir
        builtins.CONF = ConfigDir (cls.getUserFolder (_CONFIGDIR))


    @classmethod
    def _getPaths (cls):
        if cls._paths == None:
            cls._paths = {}
            for k, v in CONF.PATHS.items ():
                try:
                    for i in v:
                        if len (i) == 0:
                            raise ValueError
                    first = v [0]
                    if first [0] == '*':
                        v = _ConfigList (v._cfile, k,
                                cls._paths [first [1:]] + v [1:])
                    cls._paths [k] = v
                except:
                    REPORT.Fail (_PATHSBADPATH, k=k, v=v)
        return cls._paths


    @classmethod
    def getUserFolder (cls, *l):
        """Return a path within the user-data folder.
        The arguments are the path components within this folder.
        """
        assert cls._userdir
        return os.path.join (cls._userdir, *l)


    @classmethod
    def getUserPath (cls, item):
        """Return a path within the user-data folder.
        <item> is the name (key) of a path defined in the 'PATHS'
        configuration file.
        """
        return cls.getUserFolder (*(cls._getPaths () [item]))


    @classmethod
    def getYearPath (cls, year, item=None, make=0, **parms):
        """Return a (full) path within the school year folder.
        <item> is the name (key) of a path defined in the 'PATHS'
        configuration file.
        If <item> is not set, just return the base address.
        If <make> is non-zero, missing elements of the path will be
        created. If it is >0 the last element will be created as a
        folder, if it is <0 all elements except the last will be
        created as folders.
        The additional parameters are substitution strings.
        """
        path0 = cls.getUserPath ('DIR_SCHOOLYEAR')
        if item:
            path = os.path.join (path0, *(cls._getPaths () [item])).format (
                    year=str (year), **parms)
        else:
            path = path0.format (year=str (year))
        if make != 0:
            mpath = path if make > 0 else os.path.dirname (path)
            if not os.path.isdir (mpath):
                os.makedirs (mpath)
        return path


    @classmethod
    def getYears(cls):
        """Return a list of the school-years (<int>) for which there is
        data available, sorted with the latest first.
        No validity checks are made on the data, beyond checking that
        a database file exists for each year.
        """
        path = cls.getYearPath('*', 'FILE_SQLITE')
        return sorted([int(re.search(r'_(\d{4})\.', f).group(1))
                for f in glob.glob(path)],
                reverse=True)


    @classmethod
    def logfile(cls, tag):
        """Return a user- and time-based log-file path.
        Excess old log files for the given user are deleted.
        """
        folder = cls.getUserPath('DIR_LOGS')
        user = tag.rsplit('-', 1)[1]
        files = sorted(glob.glob(os.path.join(folder, '*-%s.log' % user)),
                reverse=True)
        # Delete excess old log files for this user
        nmax = CONF.MISC.MAXLOGFILES.nat()
        while len(files) > nmax:
            os.remove(files.pop())
        return os.path.join(folder, tag + '.log')



class Dates:
    @classmethod
    def today (cls, iso=True):
        today = datetime.date.today ().isoformat ()
        return today if iso else cls.dateConv (today)


    @staticmethod
    def day1 (schoolyear):
        month1 = CONF.MISC.SCHOOLYEAR_MONTH_1.nat (imax=12, imin=1)
        return '%d-%02d-01' % (schoolyear if month1 == 1 else schoolyear - 1,
                month1)


    @staticmethod
    def dateConv (date, trap=True):
        """Convert a date string from the program format (e.g. "2016-12-06") to
        the format used for output (e.g. "06.12.2016"), set in the configuration file.
        """
        dformat = CONF.FORMATTING.DATEFORMAT
        try:
            d = datetime.datetime.strptime (date, "%Y-%m-%d")
            return d.strftime (dformat)
        except:
            if trap:
                REPORT.Error (_INVALIDDATE, date=repr (date))
                return "00.00.0000"
            else:
                return None


    @staticmethod
    def getCalendar (schoolyear):
        """Read the calendar file for the given school year.
        """
        return ConfigFile (Paths.getYearPath (schoolyear, 'FILE_CALENDAR'))


#TODO: Is this useful?
#    @classmethod
#    def guessTerm(cls, schoolyear):
#        """Guess an initial value for the term field based on the current date.
#        """
#        today = cls.today()
#        cal = cls.getCalendar(schoolyear)
#        for term in CONF.MISC.TERMS:
#            if today <= cal['REPORTS_%s' % term]:
#                return term
#        return CONF.MISC.TERMS[-1]



##################### Test functions
def test_1 ():
    REPORT.Test ("DATE: " + Dates.dateConv ('2016-04-25'))

def test_2 ():
    REPORT.Test (Dates.dateConv ('2016-02-30'))

def test_3 ():
    path = 'DIR_GRADES_BASE'
    REPORT.Test ("PATH %s:\n  %s" % (path, Paths.getYearPath (2016,
            path, term='1')))

def test_4 ():
    REPORT.Test (".TTDATA: " + CONF.TABLES.PUPILS_FIELDNAMES.FIRSTNAME)
    REPORT.Test ("[TTDATA]: " + CONF.TABLES.PUPILS_FIELDNAMES ['FIRSTNAME'])

def test_5 ():
    REPORT.Test ("CONF.PATHS:")
    for key, val in CONF.PATHS.items ():
        REPORT.Test ("  > " + key + ": " + repr (val))

def test_6():
    REPORT.Test("Calendar:")
    REPORT.Test(Dates.getCalendar(2016))
