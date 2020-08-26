### python >= 3.7
# -*- coding: utf-8 -*-

"""
core/pupils.py - last updated 2020-08-26

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


class Pupils:
    def __init__(self):
        self.dbconn = DATABASE.engine.connect()

    def __getitem__(self, pid):
        s = DATABASE.pupils.select().where(DATABASE.pupils.c.PID == pid)
        result = self.dbconn.execute(s)
        pdata = result.fetchone()
        if not pdata:
            raise ValueError(_UNKNOWN_PID.format(pid = pid))
        return pdata

    def pid2name(self, pid):
        """Return the short name of a pupil given the PID.
        """
        pdata = self[pid]
        return self.pdata2name(pdata)

    @staticmethod
    def pdata2name(pdata):
        """Return the short name of a pupil given the database row.
        """
        return pdata['FIRSTNAME'] + ' ' + pdata['LASTNAME']

    def classes(self, stream = None):
        """Return a sorted list of class names. If <stream> is supplied,
        only classes will be return with entries in that stream.
        """
        s = DATABASE.select([DATABASE.pupils.c.CLASS])
        if stream:
            s = s.where(DATABASE.pupils.c.STREAM == stream)
        result = self.dbconn.execute(s.distinct())
        return sorted([c[0] for c in result.fetchall()], reverse = True)

    def streams(self, klass):
        """Return a sorted list of stream names for the given class.
        """
        s = DATABASE.select([DATABASE.pupils.c.STREAM]
                ).where(DATABASE.pupils.c.CLASS == klass)
        result = self.dbconn.execute(s.distinct())
        return sorted([(c[0] or '') for c in result.fetchall()])

    def check_pupil(self, pid):
        """Test whether the given <pid> is used.
        """
        try:
            self[pid]
            return True
        except ValueError:
            return False

    def classPupils (self, klass, stream = None, date = None):
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
        rows = UserList()
        rows.pidmap = {}
        s = DATABASE.pupils.select().where(DATABASE.pupils.c.CLASS == klass)
        if stream:
            s = s.where(DATABASE.pupils.c.STREAM == stream)
        s = s.order_by(DATABASE.pupils.c.PSORT)
        for pdata in self.dbconn.execute(s):
            # Check exit date
            if date:
                exd = pdata['EXIT_D']
                if exd and exd < date:
                    continue
            rows.append(pdata)
            rows.pidmap[pdata['PID']] = pdata
        return rows

    def new(self, **fields):
        """Add a new pupil with the given data. <fields> is a mapping
        containing all the necessary fields.
        """
        self.dbconn.execute(DATABASE.pupils.insert().values(**fields))

    def remove(self, pid):
        """Remove the pupil with the given id from the database.
        """
        self.dbconn.execute(DATABASE.pupils.delete().where(
                DATABASE.pupils.c.PID == pid))

    def update(self, pid, **changes):
        """Edit the given fields (<changes>: {field -> new value}) for
        the pupil with the given id. Field PID may not be changed!
        """
        self.dbconn.execute(DATABASE.pupils.update().where(
                DATABASE.pupils.c.PID == pid).values(**changes))



if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    pupils = Pupils()
    pid = '200502'
    pdata = pupils[pid]
    print("\nPID(%s):" % pid, pupils.pdata2name(pdata))
    print("  ...", pdata)
    print("\nPID(%s):" % pid, pupils.pid2name('200506'))

    print("\nCLASSES:", pupils.classes())
    print("\nCLASSES with RS:", pupils.classes('RS'))

    print("\nSTREAMS in class 12:", pupils.streams('12'))

    cp = pupils.classPupils('12', stream = 'RS', date = None)
    print("\nPUPILS in 12.RS:")
    for pdata in cp:
        print(" --", pdata)
    print("\nPUPIL 200888, in 12.RS:", cp.pidmap['200888'])

    try:
        pupils.remove("XXX")
    except:
        pass
    print("\nAdd, update (and remove) a pupil:")
    pupils.new(PID="XXX", FIRSTNAME="Fred", LASTNAME="Jones", CLASS="12",
        PSORT="ZZZ")
    print(" -->", pupils["XXX"])
    pupils.update("XXX", STREAM="RS", EXIT_D="2016-01-31")
    print("\nUPDATE (showRS):")
    for pdata in pupils.classPupils('12', stream = 'RS', date = None):
        print(" --", pdata)
    print("\n AND ... on 2016-02-01:")
    for pdata in pupils.classPupils('12', stream = 'RS', date = "2016-02-01"):
        print(" --", pdata)
    pupils.remove("XXX")

    print("\nFAIL:")
    pdata1 = pupils['12345']
