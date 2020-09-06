### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/pupils.py - last updated 2020-09-05

Database access for reading pupil data.

==============================
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
"""

import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

### Messages
_UNKNOWN_PID = "Schüler „{pid}“ ist nicht bekannt"


#from fnmatch import fnmatchcase
from collections import UserList

from core.db import DB


#TODO: The school year needs to be handled somehow, otherwise the module
# cannot be used in parallel by different users!
class Pupils:
    def __init__(self, schoolyear):
        self.schoolyear = schoolyear
#??
        self.dbconn = DB(schoolyear)
#
    def __getitem__(self, pid):
        with self.dbconn:
            pdata = self.dbconn.select1('PUPIL', PID = pid)
        if not pdata:
            raise KeyError(_UNKNOWN_PID.format(pid = pid))
        return pdata
#
    def pid2name(self, pid):
        """Return the short name of a pupil given the PID.
        """
        pdata = self[pid]
        return self.pdata2name(pdata)
#
    @staticmethod
    def pdata2name(pdata):
        """Return the short name of a pupil given the database row.
        """
        return pdata['FIRSTNAME'] + ' ' + pdata['LASTNAME']
#
    def classes(self, stream = None):
        """Return a sorted list of class names. If <stream> is supplied,
        only classes will be return with entries in that stream.
        """
        with self.dbconn:
            if stream:
                return sorted(self.dbconn.selectDistinct('PUPIL', 'CLASS',
                        STREAM = stream))
            return sorted(self.dbconn.selectDistinct('PUPIL', 'CLASS'))
#
    def streams(self, klass):
        """Return a sorted list of stream names for the given class.
        """
        with self.dbconn:
            return sorted(self.dbconn.selectDistinct('PUPIL', 'STREAM',
                    CLASS = klass))
#
    def check_pupil(self, pid):
        """Test whether the given <pid> is used.
        """
        try:
            self[pid]
            return True
        except KeyError:
            return False
#
    def classPupils(self, klass, stream = None, date = None):
        """Read the pupil data for the given school-class (possibly with
        stream).
        Return a list of pupil-data (database rows), the pupils being
        ordered alphabetically.
        If a <date> is supplied, pupils who left the school before that
        date will not be included.
        If <stream> is provided, only pupils in that stream are included,
        otherwise all pupils in the class.
        To enable indexing on pupil-id, the result has an extra
        attribute, <pidmap>: {pid-> <PupilData> instance}
        """
        with self.dbconn:
            if stream:
                fetched = self.dbconn.select('PUPIL', CLASS = klass,
                        STREAM = stream)
            else:
                fetched = self.dbconn.select('PUPIL', CLASS = klass)
        rows = UserList()
        rows.pidmap = {}
        for row in fetched:
            # Check exit date
            if date:
                exd = row['EXIT_D']
                if exd and exd < date:
                    continue
            rows.append(row)
            rows.pidmap[row['PID']] = row
        return rows
#
    def new(self, **fields):
        """Add a new pupil with the given data. <fields> is a mapping
        containing all the necessary fields.
        """
        with self.dbconn:
            self.dbconn.addEntry('PUPIL', fields)
#
    def update(self, pid, **changes):
        """Edit the given fields (<changes>: {field -> new value}) for
        the pupil with the given id. Field PID may not be changed!
        """
        with self.dbconn:
            self.dbconn.updateOrAdd('PUPIL', changes, update_only = True,
                    PID = pid)
#
    def remove(self, pid):
        """Remove the pupil with the given id from the database.
        """
        with self.dbconn:
            self.dbconn.deleteEntry('PUPIL', PID = pid)




if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    pupils = Pupils(2016)
    pid = '200502'
    pdata = pupils[pid]
    print("\nPID(%s):" % pid, pupils.pdata2name(pdata))
    print("  ...", dict(pdata))
    print("\nPID(%s):" % pid, pupils.pid2name('200506'))

    print("\nCLASSES:", pupils.classes())
    print("\nCLASSES with RS:", pupils.classes('RS'))

    print("\nSTREAMS in class 12:", pupils.streams('12'))

    cp = pupils.classPupils('12', stream = 'RS', date = None)
    print("\nPUPILS in 12.RS:")
    for pdata in cp:
        print(" --", dict(pdata))
    print("\nPUPIL 200888, in 12.RS:", dict(cp.pidmap['200888']))

    try:
        pupils.remove("XXX")
    except:
        pass
    print("\nAdd, update (and remove) a pupil:")
    pupils.new(PID="XXX", FIRSTNAME="Fred", LASTNAME="Jones", CLASS="12",
        PSORT="ZZZ")
    print(" -->", dict(pupils["XXX"]))
    pupils.update("XXX", STREAM="RS", EXIT_D="2016-01-31")
    print("\nUPDATE (showRS):")
    for pdata in pupils.classPupils('12', stream = 'RS', date = None):
        print(" --", dict(pdata))
    print("\n AND ... on 2016-02-01:")
    for pdata in pupils.classPupils('12', stream = 'RS', date = "2016-02-01"):
        print(" --", dict(pdata))
    pupils.remove("XXX")

    print("\nFAIL:")
    pdata1 = pupils['12345']
