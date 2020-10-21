# -*- coding: utf-8 -*-
"""
gui_support.py

Last updated:  2020-10-21

Support stuff for the GUI: dialogs, etc.


=+LICENCE=============================
Copyright 2019-2020 Michael Towers

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
#TODO: This needs a lot of editing ...

#TODO: Maybe a lock mechanism to prevent two instances of the program from
# running?

import os
#from glob import glob
#from collections import OrderedDict

from qtpy.QtWidgets import (QApplication, QStyle,
        QHBoxLayout, QVBoxLayout,
        QLabel, QPushButton, QComboBox,
        QFrame,
        QButtonGroup, QBoxLayout,
        QDialog, QCalendarWidget, QMessageBox,
        QProgressDialog,
        QTableWidget, QTableWidgetItem)
from qtpy.QtGui import QIcon #, QFont
from qtpy.QtCore import Qt, QDate, QObject, Signal, Slot

#from wz_core.configuration import Dates, Paths


# Dialog buttons
_CANCEL = "Abbrechen"
_ACCEPT = "Übernehmen"
_OK = "o.k."
_SETALL = "Alle setzen"
_RESETALL = "Alle zurücksetzen"

_BUSY = "Fortschritt ..."

_DATE = "Datum"


class HLine (QFrame):
    def __init__ (self):
        super ().__init__ ()
        self.setFrameShape (QFrame.HLine)
        self.setFrameShadow (QFrame.Sunken)


class VLine (QFrame):
    def __init__ (self):
        super ().__init__ ()
        self.setFrameShape (QFrame.VLine)
        self.setFrameShadow (QFrame.Sunken)


class BoldLabel (QLabel):
    def __init__ (self, text):
        super ().__init__ ('<b>' + text + '</b>')


class KeySelect(QComboBox):
    def __init__(self, value_mapping, changed_callback = None):
        """A selection widget for key-description pairs. The key is the
        actual selection item, but the description is displayed for
        human consumption.
        <value_mapping> is a list: ((key, display text), ...)
        To work with a callback, pass a function with a single parameter
        (the new key) as <changed_callback>.
        """
        super().__init__()
        self.value_mapping = value_mapping
        self.changed_callback = changed_callback
        self.addItems([text for _, text in value_mapping])
# If connecting after adding the items, there seems to be no signal;
# if before, then the first item is signalled.
        self.currentIndexChanged.connect(self._new)
        self.key = self.value_mapping[self.currentIndex()][0]

    def _new(self, index):
        self.key = self.value_mapping[index][0]
        if self.changed_callback:
            self.changed_callback(self.key)

    def trigger(self):
        self._new(self.currentIndex())


class ZIcon(QIcon):
    def __init__(self, filename):
        super().__init__(os.path.join(ZEUGSDIR, 'icons', filename + '.svg'))



class RadioButton (QPushButton):
    def __init__ (self, label, onClicked):
        super ().__init__ (label)
        self.handler = onClicked
        self.toggled.connect (self.onToggled)
        self.setCheckable (True)

    def onToggled (self, checked):
        # This is also called when <setChecked> is called, i.e. during
        # initial set-up of the default button.
        if checked:
            self.handler ()


class RadioGroup (QBoxLayout):
    def __init__ (self, *buttons, vertical=False, selected=0):
        super ().__init__ (QBoxLayout.TopToBottom if vertical
                else QBoxLayout.LeftToRight)
        self.appSwitch = QButtonGroup ()
        i = 0
        for label, action in buttons:
            b = RadioButton (label, action)
            if i == selected:
                b.setChecked (True)
            i += 1
            self.addWidget (b)
            self.appSwitch.addButton (b)
        self.addStretch ()


def PopupInfo (title, message):
    _InfoDialog (title, message, QMessageBox.Information)

def PopupWarning (title, message):
    _InfoDialog (title, message, QMessageBox.Warning)

def PopupError (title, message):
    _InfoDialog (title, message, QMessageBox.Critical)

def _InfoDialog (title, message, mtype):
    mbox = QMessageBox (mtype, title, message,
            QMessageBox.NoButton, CONTROL)
    mbox.addButton (_OK, QMessageBox.AcceptRole)
    mbox.exec_ ()



def QuestionDialog (title, message):
    qd = QDialog (CONTROL)
    qd.setWindowTitle (title)
    vbox = QVBoxLayout (qd)
    vbox.addWidget (QLabel (message))
    vbox.addWidget (HLine ())
    bbox = QHBoxLayout ()
    vbox.addLayout (bbox)
    bbox.addStretch (1)
    cancel = QPushButton (_CANCEL)
    cancel.clicked.connect (qd.reject)
    bbox.addWidget (cancel)
    ok = QPushButton (_OK)
    ok.clicked.connect (qd.accept)
    bbox.addWidget (ok)
    cancel.setDefault (True)
    return qd.exec_ () == QDialog.Accepted



class CalendarDialog (QDialog):
    @classmethod
    def getLimitedDate (cls, schoolyear=None, date=None, parent=None):
        if date == None:
            qdate = QDate.currentDate ()
        else:
            qdate = QDate.fromString (date, 'yyyy-MM-dd')
        if schoolyear == None:
            schoolyear = qdate.year ()

        m1 = CONFIG.MISC.SCHOOLYEAR_MONTH_1.nat ()
        m2 = m1 - 1
        if m2 == 0:
            m2 = 12
            y1 = schoolyear
        else:
            y1 = schoolyear - 1
        d1 = QDate (y1, m1, 1)
        d2 = d1.addYears (1).addDays (-1)
        cd = cls (qdate, d1, d2, parent)
        cd.exec_ ()
        return cd.getResult ()


    def __init__ (self, qdate=None, start=None, end=None, parent=None):
        """Note that the dates should be <QDate> instances.
        """
        super ().__init__ (parent or CONTROL)
        self._result = None
        calendar = QCalendarWidget ()
        if start != None:
            calendar.setMinimumDate (start)
        if end != None:
            calendar.setMaximumDate (end)
        if qdate == None:
            qdate = QDate.currentDate ()
        calendar.setSelectedDate (qdate)
        calendar.clicked.connect (self.onClicked)
        dbox = QVBoxLayout (self)
        dbox.addWidget (calendar)
#        cancel = QPushButton (_CANCEL)
#        dbox.addWidget (cancel)
#        cancel.clicked.connect (self.reject)

    def onClicked (self, qdate):
        self._result = qdate
        self.accept ()

    def getResult (self):
        """Return selected date in iso-format, or <None> if cancelled.
        """
        return (None if self._result == None
                else self._result.toString ('yyyy-MM-dd'))



class gui_progress (QObject):
    _progress = Signal (int, str)

    def __init__ (self):
        super ().__init__ ()
        self.PD = QProgressDialog (CONTROL)
        self.PD.setWindowModality(Qt.WindowModal)
        self.PD.setMinimumDuration (500)
        self.PD.setCancelButton (None)
        self.PD.reset ()
        self._progress.connect (self._call)

    def _call (self, percent, label):
        if percent == 0:
            self._title = label if label != '' else _BUSY
            self._label = self._title
            REPORT.STARTOP (self._title)
            self.PD.setLabelText (self._label)
            self.PD.setValue (0)
        elif percent == 100:
            self.PD.reset ()
            REPORT.ENDOP (self._title)
            self._title = None
        else:
            self.PD.setValue (percent)
            if label != '':
                self._label = label
                self.PD.setLabelText (label)

    def progress (self, percent, label=None):
        self._progress.emit (percent, label if label != None else '')



class gui_busy (QObject):
    _startS = Signal (str)
    _endS = Signal ()

    def __init__ (self):
        super ().__init__ ()
        self.PD = QProgressDialog (CONTROL)
        self.PD.setWindowModality(Qt.WindowModal)
        self.PD.setMinimumDuration (500)
        self.PD.setCancelButton (None)
        self.PD.setMaximum (0)
        self.PD.reset ()
        self._startS.connect (self._start)
        self._endS.connect (self.PD.reset)

    def start (self, label):
        self._title = label
        REPORT.STARTOP (label)
        self._startS.emit (label)

    def _start (self, label):
        self.PD.setLabelText (label)
        self.PD.setValue (0)
        QApplication.processEvents ()

    def end (self):
        REPORT.ENDOP (self._title)
        self._endS.emit ()



class DateDialog (QDialog):
    """This is a popup widget to allow the setting of a block of dates,
    individuaĺly or all together.
    <title> is the dialog title.
    <description> is a descriptive text, which will be displayed.
    <header> is the title for the key column.
    <data> is a list of tuples: [(key, date), ...].
    """
    @classmethod
    def activate (cls, *args):
        """Static method to run the dialog. The arguments are passed
        unchanged to the dialog instance (via <__init__>).
        """
        d = cls (*args)
        if d.exec_ ():
            return d.getResult ()
        else:
            return None


    def __init__ (self, title, schoolyear, description, header, data):
        self.schoolyear = schoolyear
        super ().__init__ (CONTROL)

        self.setWindowTitle (title)
        self.dates = _DateTable (header, schoolyear, data)

        hbox = QHBoxLayout (self)
        vbox = QVBoxLayout ()
        hbox.addLayout (vbox)
        hbox.setStretchFactor (vbox, 1)
        text = QLabel (description)
        text.setWordWrap (True)
        vbox.addWidget (text)
        vbox.addWidget (HLine ())
        bbox1 = QHBoxLayout ()
        b1 = QPushButton (_SETALL)
        b1.clicked.connect (self.dates.onSetAll)
        bbox1.addWidget (b1)
        b2 = QPushButton (_RESETALL)
        b2.clicked.connect (self.dates.onResetAll)
        bbox1.addWidget (b2)
        bbox1.addStretch (1)
        vbox.addLayout (bbox1)
        vbox.addWidget (HLine ())
        bbox2 = QHBoxLayout ()
        bbox2.addStretch (1)
        b3 = QPushButton (_CANCEL)
        b3.clicked.connect (self.reject)
        bbox2.addWidget (b3)
        b4 = QPushButton (_ACCEPT)
        b4.clicked.connect (self.accept)
        b4.setDefault (True)
        bbox2.addWidget (b4)
        vbox.addLayout (bbox2)

        hbox.addWidget (self.dates)


    def getResult (self):
        result = []
        for i in range (self.dates.rowCount ()):
            result.append ((self.dates.item (i, 0).text (),
                    self.dates.item (i, 1).text () or None))
        return result



class _DateTable (QTableWidget):
    """A table widget with two columns, the first being a key, the second
    an associated date.
    <header> is the title for the first column.
    <data> is a list of tuples: [(key, date), ...].
    """
    def __init__ (self, header, schoolyear, data):
        self.schoolyear = schoolyear
        super ().__init__ ()
        self.cellClicked.connect (self.onCellEdit)
        self.setRowCount (len (data))
        self.setColumnCount (2)
        self.setHorizontalHeaderLabels ((header, _DATE))
        self.setHorizontalScrollBarPolicy (Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy (Qt.ScrollBarAlwaysOn)
        vheader = self.verticalHeader ()
        vheader.hide ()
        hheader = self.horizontalHeader()
#        vheader.sectionResized.connect (self.fitToTable)
        hheader.setSectionResizeMode (hheader.Fixed)
#        hheader.sectionResized.connect (self.fitToTable)
        i = 0
        for k, d in data:
            l = QTableWidgetItem (k)
            l.setFlags (Qt.ItemIsEnabled)
            self.setItem (i, 0, l)
            d = QTableWidgetItem (d or None)
            d.setFlags (Qt.ItemIsEnabled)
            self.setItem (i, 1, d)
            i += 1
        self.fitToTable ()


    def onCellEdit (self, row, col):
        if col != 1:
            return
        item = self.item (row, col)
        date = item.text () or None
        newdate = CalendarDialog.getLimitedDate (self.schoolyear, date, parent=self)
        if newdate != None:
            item.setText (newdate)


    def fitToTable (self):
#        x = self.verticalHeader ().size ().width ()
        x = 0
        for i in range (self.columnCount ()):
            x += self.columnWidth (i)

#        y = self.horizontalHeader ().size ().height ()
#        for i in range (self.rowCount ()):
#            y += self.rowHeight (i)

        scrollbarWidth = QApplication.style ().pixelMetric (QStyle.PM_ScrollBarExtent)
        self.setFixedWidth (x + scrollbarWidth + 2)


    def onSetAll (self):
        newdate = CalendarDialog.getLimitedDate (self.schoolyear, parent=self)
        if newdate != None:
            for i in range (self.rowCount ()):
                item = self.item (i, 1)
                item.setText (newdate)


    def onResetAll (self):
        for i in range (self.rowCount ()):
            item = self.item (i, 1)
            item.setText (None)
