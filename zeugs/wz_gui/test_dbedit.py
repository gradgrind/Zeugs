#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wz_gui/_test/test_dbedit.py

Last updated:  2019-09-21
"""

#TODO: Allow a row to be deleted?

import os
os.environ['QT_API'] = 'PySide2'

from qtpy.QtWidgets import (QApplication, QDialog, QPushButton,
        QVBoxLayout, QTableView, QLabel, QMessageBox)
from qtpy.QtGui import QIcon
from qtpy.QtCore import Qt
from qtpy.QtSql import QSqlDatabase, QSqlTableModel

from gui_table import TableView


class MyTableView (TableView):
    def __init__ (self, *args, **kargs):
        super ().__init__ (cut=True, paste=True)
        self.setEditTriggers (self.EditTriggers (self.DoubleClicked
                ^ self.SelectedClicked ^ self.AnyKeyPressed))
        self.setStyleSheet("QTableView:focus{border-width: 1px;"
                    "border-style: solid;"
                    "border-color: red;}")

    def keyPressEvent (self, e):
        if e.key () == Qt.Key_Tab:
            e.ignore ()
        else:
            if e.key () == Qt.Key_Return:
                if self.state () != self.EditingState:
                    ci = self.currentIndex ()
                    if not ci.isValid ():
                        return
                    self.edit (ci)
            super ().keyPressEvent (e)


class PushButton (QPushButton):
    def __init__ (self, label):
        super ().__init__ (label)
        self.setAutoDefault (False)
        self.setStyleSheet("QPushButton:focus{border-width: 1px;"
                    "border-style: solid;"
                    "border-color: red;}")

    def keyPressEvent (self, e):
        if e.key () == Qt.Key_Return:
            self.animateClick ()
            e.ignore ()



class TestApp (QDialog):
    def __init__ (self, model, hiddenCols = None, parent = None):
        super ().__init__ (parent)
        self._model = model

        table = MyTableView (paste=True)
#        table.activated.connect (self._cellActivated)
#        table.doubleClicked.connect (self._cellDoubleClicked)
        table.setModel (self._model)
#        i = 0
#        for h in fields:
#            i += 1
#            model.setHeaderData(i, Qt.Horizontal, h)
        if hiddenCols:
            for col in hiddenCols:
                table.setColumnHidden (col, True)
                table.setColumnHidden (col, True)
        table.resizeColumnsToContents ()

        label = QLabel ("Action buttons:")
        button = PushButton ("Add a row")
#        button.setEnabled (False)
        layout = QVBoxLayout (self)
        layout.addWidget (table)
        layout.addWidget (label)
        layout.addWidget (button)
        self._bsubmit = PushButton ("Submit changes")
        layout.addWidget (self._bsubmit)
        self._dirty = icon ('dialog-warning')
        self._clean = icon ('dialog-ok')
        self._bsubmit.setIcon (self._clean)
        self._brevert = PushButton ("Revert changes")
        layout.addWidget (self._brevert)
        self._brevert.setIcon (icon ('dialog-trash'))
        self._bsubmit.setEnabled (False)
        self._brevert.setEnabled (False)
        self._pending = False

        button.clicked.connect (self._addRow)
        self._bsubmit.clicked.connect (self._submit)
        self._brevert.clicked.connect (self._revert)

        # Signal that there are changes to be submitted (or reverted)
        model.dataChanged.connect (self._changed)

    def _addRow (self):
        print ("ADD ROW")
        self._model.insertRows (self._model.rowCount (), 1)

    def _changed (self, *args):
        if not self._pending:
            self._pending = True
            self._bsubmit.setEnabled (True)
            self._brevert.setEnabled (True)
            self._bsubmit.setIcon (self._dirty)

    def _submit (self):
        tf = self._model.submitAll ()
        if tf:
            self._pending = False
            self._bsubmit.setIcon (self._clean)
            self._bsubmit.setEnabled (False)
            self._brevert.setEnabled (False)
        else:
            emsg = self._model.lastError ().databaseText ()
            QMessageBox.warning (self.parent (),
                    "Submit", "Error: %s" % emsg)
            #assert False, "Couldn't submit"

    def _revert (self):
        self._model.revertAll ()
        self._pending = False
        self._bsubmit.setIcon (self._clean)
        self._bsubmit.setEnabled (False)
        self._brevert.setEnabled (False)

    def _cellActivated (self, model):
        print ("Activated", model.row (), model.column ())

    def _cellDoubleClicked (self, model):
        print ("DoubleClicked", model.row (), model.column ())



class myModel (QSqlTableModel):
    def __init__ (self, table, parent=None, sortcol=None, readonly=None):
        self.ro = readonly
        super ().__init__ (parent)
        self.beforeUpdate.connect (self._slotUpdate)
        self.beforeInsert.connect (self._slotInsert)
#        self.beforeDelete.connect (self._slotDelete)
#        self.setEditStrategy (QSqlTableModel.OnFieldChange)
        self.setEditStrategy (QSqlTableModel.OnManualSubmit)
        self.setTable (table)
        if sortcol != None:
            self.setSort (sortcol, Qt.AscendingOrder)
        i = 0
        self._fieldnames = []
        while True:
            f = self.record().fieldName(i)
            if not f:
                break
            self._fieldnames.append (f)
            i += 1
########
        print ("FIELDS:", self._fieldnames)

    def setClass (self, klass):
        self.setFilter ("CLASS='{}'".format (klass))
        self.select ()

    def _slotUpdate (self, row, record):
        print ("\nUPDATE", row, record)

    def _slotInsert (self, record):
        print ("\nINSERT", record)

    def _slotDelete (self, row, record):
        print ("\nDELETE", row)

    def flags(self, index):
        if self.ro and (index.column() in self.ro):
            return Qt.ItemIsEnabled
        return (Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)



#########################################################
def icon (name):
    return QIcon (os.path.join (
            os.path.dirname (
            os.path.dirname (
            os.path.dirname (os.path.realpath (__file__)))),
                    'icons', name + '.svg'))

if __name__ == "__main__":
    import sys
    schoolyear = 2016
    dbpath = '../test.sqlite3'

    app = QApplication (sys.argv)
    myDb = QSqlDatabase.addDatabase ("QSQLITE")
    myDb.setDatabaseName (dbpath)
    if not myDb.open ():
        print ("Unable to create connection!")
        print ("have you installed the sqlite driver?")
        sys.exit(1)

# Note that readonly is not compatible with adding a new row!
    model = myModel("PUPILS", sortcol = 1, readonly = (2,))
    model.setClass ('09')

#    dl = TestApp(model, hiddenCols = (2,))
    dl = TestApp(model)
    dl.exec_()
