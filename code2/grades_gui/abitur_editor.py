# -*- coding: utf-8 -*-
"""
grade_editor.py

Last updated:  2020-11-10

Editor for Abitur results.


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

##### Configuration

## Measurements are in mm ##
COLUMNS = (14, 14, 25, 14, 14, 4, 20, 6, 6, 14, 3, 18, 3, 11)
ROWS = (
    6, 3, 6, 3, 4, 5, 4, 10, 5, 1,
    # Written subjects:
    5, 6, 6, 5, 6, 6, 5, 6, 6, 5, 6, 6,
    # Other subjects:
    5, 5, 6, 5, 6, 5, 6, 5, 6,
    # Results:
    5, 5, 3, 5, 3, 5, 3, 5, 3, 5, 5, 6, 5, 6
)

VALID_GRADES = (
    '15', '14', '13',
    '12', '11', '10',
    '09', '08', '07',
    '06', '05', '04',
    '03', '02', '01',
    '00'
)

### Messages


#####################################################


import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

from qtpy.QtWidgets import QDialog, QToolTip, QLabel, \
    QHBoxLayout, QVBoxLayout, QMenu, QFrame, \
    QListWidget, QListWidgetItem, QLineEdit, \
    QPushButton, QToolButton, \
    QApplication
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt

from grades_gui.grid import Grid, CellStyle, PopupDate, PopupTable
from grades_gui.gui_support import VLine, KeySelect, ZIcon
from grades.gradetable import Grades
from core.base import Dates
from core.courses import Subjects
from core.pupils import Pupils
from local.base_config import FONT, print_schoolyear, SCHOOL_NAME
from local.grade_template import REPORT_TYPES


#TODO
class AbiturGrid(Grid):
    def __init__(self):
        super().__init__()
        ### Styles:
        ## The styles which may be used
        baseStyle = CellStyle(FONT, size = 11)
        baseStyle0 = baseStyle.copy(border = 0)
        baseStyle2 = baseStyle.copy(border = 2)
        baseStyleL0 = baseStyle0.copy(align = 'l')
        labelStyle = baseStyle.copy(align = 'l', border = 0, highlight = 'b')
        titleStyle = CellStyle(FONT, size = 12, align = 'l',
                border = 0, highlight = 'b')
        titleStyleR = titleStyle.copy(align = 'r')
        underlineStyle = baseStyle.copy(border = 2)
        smallStyle = baseStyle.copy(size = 10)
        vStyle = smallStyle.copy(align = 'm')
        hStyle = smallStyle.copy(border = 0)
        gradeStyle = baseStyle.copy(highlight = ':2a6099')
        resultStyleL = titleStyle.copy(border = 2)
        resultStyle = titleStyle.copy(border = 2, align = 'c')
        dateStyle = resultStyle.copy(highlight = ':2a6099')

        self.setTable(ROWS, COLUMNS)
        ### Cell editors
        edit_grade = PopupTable(self, VALID_GRADES)
        edit_date = PopupDate(self)

#TODO: Just for testing width, remove it!
        SCHOOLYEAR = "2015 – 2016"
        NAME = "Maria Müller"

        ### Title area
        self.tile(0, 0, text = "Abitur-Berechnungsbogen", cspan = 4,
                style = titleStyle)
        self.tile(0, 4, text = SCHOOL_NAME, cspan = 10, style = titleStyleR)
        self.tile(2, 7, text = "Schuljahr:", cspan = 3, style = titleStyleR)
#TODO: text setting is separate!
        self.tile(2, 10, text = "2015 – 2016", cspan = 4, style = titleStyle,
                tag = 'SCHOOLYEAR')
        self.tile(3, 0, cspan = 14, style = underlineStyle)

        ### Pupil's name
        self.tile(5, 0, cspan = 2, text = "Name:", style = labelStyle)
#TODO: text setting is separate!
        self.tile(5, 2, cspan = 12, text = "Maria Müller", style = labelStyle,
                tag = 'NAME')
        self.tile(6, 0, cspan = 14, style = underlineStyle)

        ### Grade area headers
        self.tile(8, 2, text = "Fach", style = hStyle)
        self.tile(8, 3, text = "Kurspunkte", cspan = 2, style = hStyle)
        self.tile(8, 6, text = "Mittelwert", style = hStyle)
        self.tile(8, 9, text = "Berechnungspunkte", cspan = 3,
                style = hStyle)

        self.tile(10, 11, text = "Fach 1-4", style = smallStyle)
        self.tile(11, 0, text = "Erhöhtes Anforderungsniveau",
                rspan = 8, style = vStyle)
        self.tile(23, 11, text = "Fach 5-8", style = smallStyle)
        self.tile(20, 0, text = "Grundlegendes Anforderungsniveau",
                rspan = 11, style = vStyle)

        ### Subject entries
        # With written exams
        for i in (1, 2, 3, 4):
            istr = str(i)
            row0 = 8 + i*3
            self.tile(row0, 1, text = istr, rspan = 2, style = baseStyle)
#TODO: text setting is separate!
            self.tile(row0, 2, text = "Deutsch", rspan = 2, style = baseStyle,
                    tag = "SUBJECT_%s" % istr)
            self.tile(row0, 3, text = "schr.", style = smallStyle)
            self.tile(row0 + 1, 3, text = "mündl.", style = smallStyle)
#TODO: text setting is separate!
            self.tile(row0, 4, text = "10", style = gradeStyle,
                    validation = edit_grade, tag = "GRADE_%s" % istr)
            self.tile(row0 + 1, 4, style = gradeStyle,
                    validation = edit_grade, tag = "GRADE_%s_m" % istr)
            self.tile(row0, 6, rspan = 2, style = baseStyle,
                    tag = "AVERAGE_%s" % istr)
            self.tile(row0, 7, text = "X", rspan = 2, style = baseStyle0)
            self.tile(row0, 8, text = "12" if i < 4 else "8", rspan = 2,
                    style = baseStyle0)
            self.tile(row0, 9, rspan = 2, style = baseStyle2,
                    tag = "SCALED_%s" % istr)

        # Without written exams
        for i in (5, 6, 7, 8):
            istr = str(i)
            row0 = 14 + i*2
            self.tile(row0, 1, text = istr, style = baseStyle)
#TODO: text setting is separate!
            self.tile(row0, 2, text = "Französisch", style = baseStyle,
                    tag = "SUBJECT_%s" % istr)
            self.tile(row0, 3, text = "mündl." if i < 7 else "2. Hj.",
                    style = smallStyle)
            self.tile(row0, 4, text = "04", style = gradeStyle,
                    validation = edit_grade, tag = "GRADE_%s" % istr)
            self.tile(row0, 6, style = baseStyle,
                    tag = "AVERAGE_%s" % istr)
            self.tile(row0, 7, text = "X", style = baseStyle0)
            self.tile(row0, 8, text = "4", style = baseStyle0)
            self.tile(row0, 9, style = baseStyle2,
                    tag = "SCALED_%s" % istr)

        ### Totals
#TODO: text setting is separate!
        self.tile(11, 11, text = "?", rspan = 11, style = baseStyle,
                    tag = "TOTAL_1-4")
        self.tile(24, 11, text = "?", rspan = 7, style = baseStyle,
                    tag = "TOTAL_5-8")

        ### Evaluation
        i = 0
        for text in (
                "Alle >0:",
                "Fach 1 – 4, mindestens 2mal ≥ 5P.:",
                "Fach 5 – 8, mindestens 2mal ≥ 5P.:",
                "Fach 1 – 4 ≥ 220:",
                "Fach 5 – 8 ≥ 80:"
                ):
            row = 32 + i*2
            i += 1
            self.tile(row, 2, text = text, cspan = 6, style = baseStyleL0)
#TODO: text setting is separate!
            self.tile(row, 9, text = "Nein", style = baseStyle,
                tag = "JA_%d" % i)

        ### Final result
        self.tile(42, 2, text = "Summe:", style = resultStyleL)
#TODO: text setting is separate!
        self.tile(42, 3, text = "590", cspan = 2, style = resultStyle,
                tag = "SUM")
        self.tile(42, 8, text = "Endnote:", cspan = 2, style = resultStyleL)
#TODO: text setting is separate!
        self.tile(42, 10, text = "2,4", cspan = 4, style = resultStyle,
                tag = "FINAL_GRADE")

        self.tile(44, 8, text = "Datum:", cspan = 2, style = resultStyleL)
#TODO: text setting is separate!
        self.tile(44, 10, text = "2016-06-16", cspan = 4, style = dateStyle,
                validation = edit_date, tag = "GRADE_D")
#TODO: Do I want to display the date in local format? If so, I would need
# to adjust the popup editor ...

#TODO: deal with changes
    def valueChanged(self, tag, text):
        if tag == "GRADE_D":
            # date changed
            print("New date:", text)

        elif not tag.startswith('GRADE_'):
            raise Bug("Unexpected field change: %s (%s)" % (tag, text))
        else:
            # grade changed
            subject_n = tag.split('_', 1)[1]
            print("New grade in Subject %s: %s" % (tag, repr(text)))

###########################################

class ListItem(QListWidgetItem):
    def __init__ (self, text, tag=None):
        super().__init__(text)
        self.tag = tag

    def val (self):
        return self.text ()



def gradeEdit(title, year, date):
    ge = _GradeEdit(title)
#    ge.setDate(year, date)
    ge.exec_()


class _GradeEdit(QDialog):
    def __init__(self, title):
#TODO:
        self.gradeInfo = GradeInfo()

        super().__init__()
        self.setWindowTitle(title)
        screen = QApplication.instance().primaryScreen()
#        ldpi = screen.logicalDotsPerInchY()
        screensize = screen.availableSize()
        self.resize(screensize.width()*0.8, screensize.height()*0.8)
#TODO: It might be more desirable to adjust to the scene size.

# Class select and separate stream select?
        topbox = QHBoxLayout(self)
#        self.gridtitle = QLabel ("GRID TITLE")
#        self.gridtitle.setAlignment (Qt.AlignCenter)
        self.gradeView = AbiturGrid()
        topbox.addWidget(self.gradeView)
        topbox.addWidget(VLine())

#        self.gradeView.setToolTip ('This shows the <b>grades</b> for a class')
#        bbox = QHBoxLayout()
#        pbSmaller = QPushButton(ZIcon('zoom-out'), '')
#        pbSmaller.clicked.connect(self.gradeView.scaleDn)
#        pbLarger = QPushButton(ZIcon('zoom-in'), '')
#        pbLarger.clicked.connect(self.gradeView.scaleUp)
#        bbox.addWidget(pbLarger)
#        bbox.addWidget(pbSmaller)

        cbox = QVBoxLayout()
#        cbox.addLayout(bbox)
#        self.yearSelect = KeySelect([(y, print_schoolyear(y))
#                for y in Dates.get_years()],
#                self.changedYear)
#        self.categorySelect = KeySelect(Grades.categories(),
#                self.changedCategory)

        ### Select group (might be just one entry ...)
        self.group_select = KeySelect([('13', 'Klasse 13')],
                self.changedGroup)
        self.group_select

        ### List of pupils
# Rather use another KeySelect?:
        self.select = QListWidget()
        self.select.setMaximumWidth(150)
        self.select.itemClicked.connect(self.changeSelection)
#        cbox.addWidget(self.yearSelect)
        cbox.addWidget(self.group_select)
        cbox.addWidget(self.select)
        pbPdf = QPushButton('PDF')
        cbox.addWidget(pbPdf)
        pbPdf.clicked.connect(self.gradeView.toPdf)
        topbox.addLayout(cbox)
#        self.yearSelect.trigger()

# after "showing"?
#        pbSmaller.setFixedWidth (pbSmaller.height ())
#        pbLarger.setFixedWidth (pbLarger.height ())

    def changedGroup(self, group):
        pass

    def changedYear(self, schoolyear):
        print("Change Year:", schoolyear)
        self.schoolyear = schoolyear
# clear main view?
        self.categorySelect.trigger()


    def changedCategory(self, key):
        print("Change Category:", key)
#TODO: choices -> ???
#        categories = Grades.categories()


#        self.choices = GRADE_REPORT_CATEGORY[key]
        self.select.clear()

        if key == 'A':
            # Abitur, examination results
            pass
        elif key == 'S':
            # A non-scheduled report
            pass
        else:
            ### A term report, select the pupil group.
            # Get a list of (group, default-report-type) pairs for this term.
            # (Note that this will fail for 'A' and 'S'.)
            self.group_choices = term2group_rtype_list(key)

            self.select.addItems([g for g, _ in self.group_choices])
# This doesn't initially select any entry




    def setDate(self, schoolyear, date):
        # GRADE_INFO table: ('_ISSUE_D', '_PGROUP', '_SIDS', 'GDATE_D')
        self.gradeInfo.setDate(schoolyear, date)
        self.classSelect.clear()

#TESTING ...
        for group in ('11', '12.G', '12.R', '13'):
            lwi = ListItem(group)
            self.classSelect.addItem(lwi)

#TESTING ...
        self.gradeView.setGroup() # no argument -> clear display?
# ... or take first entry?
#        self.classSelect.setCurrentRow (0)


    def changeSelection(self, listItem):
        group = listItem.text()
        rtypes = self.choices[group]
        print("Selected:", group, rtypes)
        return

        klass_stream = listItem.text()
#        self.gradeView.setClassStream (klass, stream)

        self.gradeInfo.setClassStream(klass_stream)
#        for pid, grades in self.gradeInfo.pids.items ():
#            print ("§§§", pid, grades)
#            for sid, deps in self.gradeInfo.dependencies.items ():
#                print ("   +++", deps)
#            print ()

        self.gradeView.setNewGroup()


#TODO
class GradeInfo:
    def __init__(self):
        super().__init__()

#?
    def setDate(self, schoolyear, date):
        self.schoolyear = schoolyear
        self.date = date

##    def setClassStream(self, klass_stream):
#    def setGroup(self, group):
#        super().setGroup(group)


#TODO
    def validators(self):
        return {}

    def newValue(self, pid, sid, text):
        print("NEW:", pid, sid, text)

    def title(self):
        """The title line for the table editor.
        """
#TODO
        return "Noten: 11.G // 2016, 2. Halbjahr"

    def infoRows(self):
        """Return a mapping of the group info parameters.
        """
#TODO
        return {}

    def grade_groups(self):
        """Return a list of grade groups for the present pupil group
        (and report type?).
        The list should be ordered as desired for the column order.
        """
#TODO
        return []

    def subjects(self):
        """Return an ordered mapping {sid -> <SubjectData>}.
        """
        return Subjects(self.schoolyear).grade_subjects(self.klass)

    def pupils(self):
        """Return a list of <PupilData> objects.
        """
#TODO
        return []



if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    schoolyear = 2016
    date = '2016-06-22'
    #date = '2016-06-20'
    #date = '2016-01-28'
    #schoolyear = 2019
    #date = '2019-06-20'

    import sys
    from qtpy.QtWidgets import QApplication, QStyleFactory
    from qtpy.QtCore import QLocale, QTranslator, QLibraryInfo

#    print(QStyleFactory.keys())
#    QApplication.setStyle('windows')

    app = QApplication(sys.argv)
    LOCALE = QLocale(QLocale.German, QLocale.Germany)
    QLocale.setDefault(LOCALE)
    qtr = QTranslator()
    qtr.load("qt_" + LOCALE.name(),
            QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtr)

    gradeEdit("Abitur-Ergebnisse", schoolyear, date)
