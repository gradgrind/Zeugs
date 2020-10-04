### python >= 3.7
# -*- coding: utf-8 -*-
"""
core/base.py

Last updated:  2020-10-04

Basic configuration and structural stuff.

=+LICENCE=================================
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

=-LICENCE=================================
"""

### Messages
_BAD_DATE = "Ungültiges Datum im Kalender: {line}"
_INVALID_SCHOOLYEAR = "Ungültiges Schuljahr: {year}"
_BAD_CALENDAR_LINE = "Ungültige Zeile im Kalender: {line}"
_DOUBLE_DATE_TAG = "Mehrfacher Kalendereintrag: {tag} = ..."


import sys, os, builtins, datetime
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

class Bug(Exception):
    pass
builtins.Bug = Bug

# First month of school year (Jan -> 1, Dec -> 12):
import local.base_config as CONFIG
from core.db import year_path # core.db is also needed for initialisation

def init(datadir = 'DATA'):
    appdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    builtins.ZEUGSDIR = os.path.join(os.path.dirname (appdir))
    builtins.DATA = os.path.join(ZEUGSDIR, datadir)
    builtins.RESOURCES = os.path.join(DATA, 'RESOURCES')


def report(text):
    """The default reporting function prints to stdout.
    It can be overridden later.
    """
    print(text)
builtins.REPORT = report

#    set_schoolyear()


#def set_schoolyear(schoolyear = None):
#    allyears = Dates.get_years()
#    if schoolyear:
#        if schoolyear not in allyears:
#            raise ValueError(_INVALID_SCHOOLYEAR.format(year=schoolyear))
#    else:
#        schoolyear = Dates.get_schoolyear()
#        if schoolyear not in allyears:
#            # Choose the latest school year, if there is one
#            try:
#                schoolyear = allyears[0]
#            except:
#                pass
#    builtins.DATABASE = DB(schoolyear)
#    builtins.SCHOOLYEAR = schoolyear


def read_float(string):
    # Allow spaces (e.g. as thousands separator)
    inum = string.replace(' ', '')
    # Allow ',' as decimal separator
    return float(inum.replace (',', '.'))


def str2list(string, sep = ','):
    """Convert a string with separator character to a list.
    Accept also <None> as string input.
    """
    if string:
        return [s.strip() for s in string.split(sep)]
    return []

###

class DateError(Exception):
    pass
class Dates:
    @staticmethod
    def print_date(date, trap = True):
        """Convert a date string from the program format (e.g. "2016-12-06")
        to the format used for output (e.g. "06.12.2016").
        If an invalid date is passed, a <DateError> is raised, unless
        <trap> is false. In that case <None> – an invalid date – is returned.
        """
        try:
            d = datetime.datetime.strptime(date, "%Y-%m-%d")
            return d.strftime(CONFIG.DATEFORMAT)
        except:
            if trap:
                raise DateError("Ungültiges Datum: '%s'" % date)
        return None

    @classmethod
    def convert_dates(cls, mapping):
        """Convert all date values in the given mapping to the format
        used for output (see method <print_date>). The date values are
        those with keys ending '_D'.
        Return a list of the keys for failed conversions.
        """
        fails = []
        for key, val in mapping.items():
            if key.endswith('_D'):
                try:
                    mapping[key] = cls.print_date(val)
                except DateError:
                    fails.append(key)
        return fails

    @classmethod
    def today(cls, iso = True):
        today = datetime.date.today().isoformat()
        return today if iso else cls.dateConv(today)

    @staticmethod
    def day1(schoolyear):
        return '%d-%02d-01' % (schoolyear if CONFIG.SCHOOLYEAR_MONTH_1 == 1
                else schoolyear - 1, CONFIG.SCHOOLYEAR_MONTH_1)

    @classmethod
    def check_schoolyear(cls, schoolyear, d = None):
        """Test whether the given date <d> lies within the schoolyear.
        Return true/false.
        If no date is supplied, return a tuple (first day, last day).
        """
        d1 = cls.day1(schoolyear)
        oneday = datetime.timedelta(days = 1)
        d2 = datetime.date.fromisoformat(cls.day1(schoolyear + 1))
        d2 -= oneday
        d2 = d2.isoformat()
        if d:
            if d < d1:
                return False
            return d <= d2
        return (d1, d2)

    @classmethod
    def get_schoolyear(cls, d = None):
        """Return the school-year containing the given date <d>.
        If no date is given, use "today".
        """
        if not d:
            d = cls.today()
        y = int(d.split('-', 1)[0])
        if d >= cls.day1(y + 1):
            return y + 1
        return y

    @classmethod
    def get_years(cls):
        """Return a list of the school-years ([<int>, ...]) for which
        there is data available, sorted with the latest first.
        No validity checks are made on the data, beyond checking that
        a database file exists for each year.
        """
        sypath = os.path.join(DATA, 'SCHOOLYEARS')
        years = []
        for d in os.listdir(sypath):
            try:
                y = int(d)
                if os.path.exists(os.path.join(sypath, d,
                        'db_%d.sqlite3' % y)):
                    years.append(y)
            except:
                pass
        return sorted(years, reverse=True)

    @classmethod
    def get_calendar(cls, schoolyear):
        """Read the calendar file for the given school year.
        """
        fpath = year_path(schoolyear, CONFIG.CALENDAR_FILE)
        calendar = {}
        with open(fpath, encoding = 'utf-8') as fi:
            for l in fi:
                line = l.strip()
                if (not line) or line[0] == '#':
                    continue
                try:
                    k, v = line.split('=')
                except ValueError as e:
                    raise DateError(_BAD_CALENDAR_LINE.format(
                            line = l)) from e
                k = k.strip()
                if not k:
                    raise DateError(_BAD_CALENDAR_LINE.format(line = l))
                if k in calendar:
                    raise DateError(_DOUBLE_DATE_TAG.format(tag = k))
                try:
                    v1, v2 = v.split(':')
                except:
                    # single day
                    date = v.strip()
                    # check validity
                    if cls.check_schoolyear(schoolyear, date):
                        calendar[k] = date
                        continue
                else:
                    # range of days
                    date1, date2 = v1.strip(), v2.strip()
                    if (cls.check_schoolyear(schoolyear, date1)
                            and cls.check_schoolyear(schoolyear, date2)):
                        calendar[k] = (date1, date2)
                        continue
                raise DateError(_BAD_DATE.format(line = l))
        return calendar




if __name__ == '__main__':
    init('TESTDATA')
    print("Current school year:", Dates.get_schoolyear())
    print("DATE:", Dates.print_date('2016-04-25'))
    try:
        print("BAD Date:", Dates.print_date('2016-02-30'))
    except DateError as e:
        print(" ... trapped:", e)
    print("\nCalendar for 2016:\n", Dates.get_calendar(2016))
