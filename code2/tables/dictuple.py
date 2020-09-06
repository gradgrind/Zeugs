### python >= 3.7
# -*- coding: utf-8 -*-

"""
tables/dictuple.py - last updated 2020-09-02

A factory function for tuples with named fields and dict-like access to
the individual fields using the <get> method.
A <Dictuple> instance may also be used as a dict-like iterator by using
the <items> method.

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


def dictuple(name, fields):
    """This is a factory function, generating <Dictuple> classes.
    These classes are basically tuples with a fixed length and with
    names/keys asssociated with the individual entries.
    An entry may be retrieved by indexing, dt1a[2] or using the tag,
    dt1a.get("C"):
        dt1 = dictuple("ONE", ["A", "B", "C", "D"])
        dt1a = dt1((9,8,7,6))
    <name> is used to tag the generated class (Dictuple:<name>).
    <fields> is a list of the keys for the generated class.
    There is no default value for <get> calls with invalid keys – a
    <KeyError> exception is raised.
    A real <dict> may be returned by calling the <_dict> method.
    """
    _classname = "Dictuple:%s" % name
    class Dictuple(tuple):
        __name__ = _classname
#        __qualname__ = _classname
        _keylist = tuple(fields)

        @classmethod
        def fieldnames(cls):
            return cls._keylist

        def get(self, item):
            return self[self._keylist.index(item)]

        def __new__(cls, items):
            if isinstance(items, list) or isinstance(items, tuple):
                if len(items) != len(cls._keylist):
                    raise IndexError("Dictuple elements mismatch")
            else:
                raise TypeError("Dictuple requires a list or tuple")
            return tuple.__new__(cls, items)

        def __repr__(self):
            """A print-representation showing field names and values.
            """
            kvlist = ["%s: %s" % (repr(k), str(v))
                    for k, v in self.items()]
            return "<%s>(%s)" % (self.__name__, ", ".join(kvlist))

        def items(self):
            """Return an iterator, as if the object were a <dict>.
            """
            i = 0
            for k in self._keylist:
                yield(k, self[i])
                i += 1

        def _dict(self):
            """Return the data as a true <dict>
            """
            return dict(self.items())

    return type(_classname, (Dictuple,), {})



if __name__ == '__main__':
    l1 = ("A", "B", "C", "D", "E", "F", "G", "H")
    dt1 = dictuple("ONE", l1)
    print ("__qualname__:", dt1.__qualname__, "  //  __name__:", dt1.__name__)
    print (dt1, "// Field names:", dt1._keylist)
    dt1a = dt1((9,8,7,6,5,4,3,2))
    print("TYPE:", type(dt1a))

    dt2 = dictuple("TWO", ["W", "X", "Y", "Z"])
    print (dt2, "// Field names:", dt2.fieldnames())
    dt2a = dt2((None,82,73,64))
    dt2b = dt2(("L","M","N","O"))

    print (dt1a, dt1a.get("B"), dt1a[1], type(dt1a[1]))
    print (dt2a, dt2a.get("X"), dt2a[1])
    print (dt2b, dt2b.get("Z"), dt2b[-1])

    print("\nAs tuple:", dt1a)
    for v in dt1a:
        print(repr(v))

    print("\nAs dict:", dt1a._dict())
    for k, v in dt1a.items():
        print (k, "-->", v)

    """
    import random
    from time import time
    from collections import namedtuple
    dt1Y = namedtuple("NT1", l1)
    dt1c = dt1Y(9,8,7,6,5,4,3,2)
    dt1X = dictuple("ONE", l1)
    dt1b = dt1X((9,8,7,6,5,4,3,2))

    random.seed()
    state = random.getstate()
    t0 = time()
    for n in range(1000000):
        w = dt1b.get(random.choice(l1))
        x = dt1b.get(random.choice(l1))
        y = dt1b.get(random.choice(l1))
        z = dt1b.get(random.choice(l1))
    t1 = time()
    print("Timer 0 done:", t1 - t0)

    random.setstate(state)
    t0 = time()
    for n in range(1000000):
        w = getattr(dt1c, random.choice(l1))
        x = getattr(dt1c, random.choice(l1))
        y = getattr(dt1c, random.choice(l1))
        z = getattr(dt1c, random.choice(l1))
    t1 = time()
    print("Timer 1 done:", t1 - t0)
    """

    # This should fail (only 3 elements)
    print("\nFAIL:")
    dt2c = dt2(("L","M","N"))
    print (dt2c)
