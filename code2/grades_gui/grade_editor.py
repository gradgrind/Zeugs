# -*- coding: utf-8 -*-
"""
grade_editor.py

Last updated:  2020-11-05

Grade Editor.


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

##### Configuration for grade tables
## Measurements are in mm ##

FONT = 'Arial'
FONT_SIZE = 10
FONT_SIZE_TITLE = 12
FONT_SIZE_TAG = 9

### Column width (approximate)
WIDTH_PID = 15
WIDTH_NAME = 50
WIDTH_STREAM = 25
WIDTH_GRADE = 8
## special columns
# Composite:
WIDTH_SPECIAL_DEFAULT = 15
WIDTH_SEP = 2
# Row heights (approximate)
HEIGHT_TITLE = 10
HEIGHT_INFO = 8
HEIGHT_ROW = 8
HEIGHT_SID = 6
HEIGHT_SBJ = 40
HEIGHT_SEP = 2

BG_COLOURS = {
    'INVALID':  '888888',
    'QUALI':    'AAFFAA',
    'SEP':      'CCCCCC',
    'Ku':       'FFFF80',
    'NOQUAL':   'DDF0FF'
}

FG_STYLE = {
    'COMPOSITE': ':4444D0',
    'INVALID':  ':C90000'
}

### Field names for the grade tables
GRADETABLE_FIELDNAMES = {
    '_TITLE': 'Notentabelle',
    '_ISSUE_D': 'Ausgabedatum',
    'PGROUP': 'Klasse/Gruppe',
    'GDATE_D': 'Notenkonferenz',
    '%subject': 'Fach',
    '%pupil': 'Schüler/in'
}

### Messages
_SID_IN_MULTIPLE_GROUPS = "Fächertabelle: Fachgruppe für Fach {sid}" \
        " ist nicht eindeutig"
_GROUP_CHANGE = "{pname} hat die Gruppe gewechselt: {delta}"


#####################################################


import sys, os
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

from qtpy.QtWidgets import QDialog, QToolTip, QLabel, \
    QHBoxLayout, QVBoxLayout, QMenu, QFrame, QListWidget, \
    QListWidgetItem, QLineEdit, \
    QPushButton, QToolButton, \
    QApplication
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt

from grades_gui.grid import Grid, CellStyle, PopupDate, PopupLineEdit, \
        PopupTable
from grades_gui.gui_support import VLine, KeySelect, ZIcon
from grades.gradetable import Grades
from core.base import Dates
from core.courses import Subjects
from core.pupils import Pupils
from local.base_config import print_schoolyear
from local.grade_template import REPORT_TYPES

#TODO: It would probably be good to display at least the date, perhaps
# also the schoolyear (somewhere).


# Suggestion: Select (config)
#    1. Halbjahr (-> group select)
#    2. Halbjahr (-> group select)
#    Sonderzeugnis (-> class/pupil select)
#    Abitur (-> pupil select)
# The group selection could be: name -> class:stream,stream,... or class
#  ... or something else (put it in localisable code). A function would
# return a title and list of pids. The report templates must be at least
# "compatible", if not identical.

### I need to get the data for a grade group ...
# ... GradeValues seems to have vanished! It has turned into GradeBase,
# but the instances have a different purpose ...
# I probably need some of the stuff from makereports.

#TODO: What about unscheduled reports?
def get_grade_data(schoolyear, term, group):
# Assume first that we are dealing with old data. This is primarily
# determined by the entries in the GRADES table and should normally
# not be changed!
# In the case of the current term, it is possible that there are
# changes to pupil data, including stream – and even class. Thus it
# is probably necessary to distinguish the two cases.

    ### Pupil data
    pupils = Pupils(schoolyear)
    # Needed here for pupil names, can use pupils.pid2name(pid)
    # Fetching the whole class may not be good enough, as it is vaguely
    # possible that a pupil has changed class.

    ### Subject data (for whole class)
    _courses = Subjects(schoolyear)
    klass, streams = Grades.group2klass_streams(group)
    sdata_list = _courses.grade_subjects(klass)

    gdata_list = [] # collect row data
    for gdata in Grades.forGroupTerm(schoolyear, term, group):
        # Get all the grades, including composites.
        gdata.get_full_grades(sdata_list)
        gdata.set_pupil_name(pupils.pid2name(gdata['PID']))
        gdata_list.append(gdata)

    return gdata_list


#TODO ...
### The alternative, for the current term, might be
    gdata_list = [] # collect row data
    for pdata in pupils.classPupils(klass):
#TODO: date?
        if streams and (pdata['STREAM'] not in streams):
            continue
        try:
            gdata = Grades.forPupil(schoolyear, term, pdata['PID'])
        except GradeTableError:
            # No entry in database table
            gdata = Grades.newPupil(schoolyear, TERM = term,
                    CLASS = pdata['CLASS'], STREAM = pdata['STREAM'],
                    PID = pdata['PID'])
        else:
            # Check for changed pupil stream and class
            changes = {}
            if pdata['CLASS'] != gdata['CLASS']:
                changes['CLASS'] = pdata['CLASS']
            if pdata['STREAM'] != gdata['STREAM']:
                changes['STREAM']  = pdata['STREAM']
            if changes:
                REPORT(_GROUP_CHANGE.format(
                        pname = pupils.pdata2name(pdata),
                        delta = repr(changes)))
                gdata.update(**changes)
        # Get all the grades, including composites
        grades = gdata.get_full_grades(sdata_list)



#TODO
class GradeGrid(Grid):
    def __init__(self):
        super().__init__()
        ### Styles:
        ## The styles which may be used
        baseStyle = CellStyle(FONT, size = FONT_SIZE, align = 'l')
        padStyle = CellStyle(None, None, border = 0)
        titleStyle = CellStyle(FONT, size = FONT_SIZE_TITLE, align = 'c',
                border = 2)
        subjectStyle = baseStyle.copy(align = 'b')
        gradeStyle = baseStyle.copy(align = 'c')
        componentStyle = gradeStyle.copy(bg = BG_COLOURS['Ku'])
        compositeStyle = componentStyle.copy(highlight = FG_STYLE['COMPOSITE'])
        noqualStyle = gradeStyle.copy(bg = BG_COLOURS['NOQUAL'])

#TODO:
#        ### Cell editors
# Change name! There are too many gradeEdits at the moment!
#        gradeEdit = PopupTable(gradeInfo.gradeValidationList())
#        self.addItem(gradeEdit)
#        dateEdit = PopupDate()
#        self.addItem(dateEdit)
#        lineEdit = PopupLineEdit ()
#        self.addItem(lineEdit)
# These should probably be added in <setData>, but old ones should
# also be removed ...

#TODO
    def setData(self, gradeInfo):
        sid_col = {}       # mapping: { sid -> column index }
        spacer_cols = []    # collect indexes of spacer columns
        ### Determine column sizes and styles
        ### The entries are (width, cell style)
        columns = [
            (WIDTH_PID, baseStyle),     # pid
            (WIDTH_NAME, baseStyle),    # pupil name
            (WIDTH_STREAM, baseStyle),  # pupil stream
        ]
        ## Now add subject columns
        # Group the subjects
        grade_groups = {gg: [] for gg in gradeInfo.grade_groups()}
        unused = []     # Collect sids not covered by subject groups
# Maybe setGroup does this already?
        subjects = gradeInfo.subjects()
        for sid, sdata in subjects.items():
            sdone = False
            for gg in grade_groups:
                if gg in sdata.report_groups:
                    if sdone:
                        raise GradeConfigError(_SID_IN_MULTIPLE_GROUPS.format(
                                sid = sid))
                    grade_groups[gg].append((sid, sdata))
                    sdone = True
            if not sdone:
                unused.append(sid)
        # Add the columns
        for gg, sid_sdata in grade_groups.items():
            if not sid_sdata:
# Report?
                continue
            # Start with a spacer column
            spacer_cols.append(len(columns))
            columns.append((WIDTH_SEP, padStyle))
            for sid, sdata in sid_sdata:
                if sdata.composite:
                    # It is a component
                    if sdata.composite == '/':
                        style = noqualStyle
                    else:
                        style = componentStyle
                elif not sdata.tids:
                    # It is a composite
# Need the component list to calculate the value ...
                    style = compositeStyle
                else:
                    style = gradeStyle
                sid_col[sid] = len(columns)
                columns.append((WIDTH_GRADE, style))

        ### Determine row sizes
        ### The entries are (width, cell style)
        rows = [HEIGHT_TITLE]
        for info in gradeInfo.infoRows():
            rows.append[HEIGHT_INFO]
        rows += [HEIGHT_SEP, HEIGHT_SID, HEIGHT_SBJ, HEIGHT_SEP]
        for pdata in gradeInfo.pupils():
            rows.append[HEIGHT_ROW]

        self.setTable(rows, columns)

        ### Title
        self.tile(0, 0, cspan = len(cols), text = gradeInfo.title(),
                style = titleStyle)
        rowix = 0

        ### Initialise popup editors
        # (line editor and date editor are "built-in")
        self.addSelect('GRADE', gradeInfo.valid_grades)
        # Editors for 'EXTRA' columns
        for tag, vlist in gradeInfo.validators.items():
            self.addSelect(tag, vlist)

        ### Info lines
        for info, val in gradeInfo.infoRows().items():
            rowix += 1
            self.tile(rowix, 1, text = info, style = baseStyle)
            self.tile(rowix, 2, cspan = len(cols) - 2, text = info,
                    style = baseStyle)
        sid_rowix = rowix + 2   # leave a spacer row

        ### Subject headers
        for sid, col in sid_col.items():
            self.tile(rowix, col, text = sid, style = gradeStyle)
            self.tile(rowix + 1, col, text = subjects[sid].name,
                    style = subjectStyle)


#################################

        # Vertical spacer column:
        xsep.append(x)
        x += XSEPW
        xmarks.append(x)

        # Map <sid> to column for x-coordinates (in <xmarks>)
        sid_ncol = {}
        # Set background colour according to column type
        sid_bg = {}
        # Subject name fields
        sid_name = {}
        # Associate editor pop-ups with sids
        editors = {}
#        for sid in gradeInfo.groupInfo['_SIDS'].split ('&'):
        for sid in ('De', 'En', 'Fr', 'Ma', 'Ges', 'Ch', 'Ph', 'Mu', 'Ku'):
#            cdata = gradeInfo.courseData [sid]
#            if '#' in cdata.flags:
#                continue
            sid_ncol[sid] = len(xmarks)
            # Column width is fixed for grades. For special types there
            # is a default, but it can be overridden by an entry with
            # the "tid" as key.
#            sname = cdata.name
#            tid = cdata.teacher
            sname = 'Subject Name'
            tid = 'ATN'


#            sid_bg[sid] = bgclrs.get(cdata.gtype)
            sid_bg[sid] = bgclrs.get('-0')
            if tid[0] == '*':
#????
                if tid in configs:
                    width = configs [tid].nat ()
                else:
                    width = WIDTH_SPECIAL_DEFAULT
                sid_name [sid] = sname
                if tid [0] == EXTRA:
                    try:
                        editors [sid] = xeditors [tid]
                    except:
                        pass

            else:
                width = WIDTH_GRADE
                editors[sid] = gradeEdit
                sid_name[sid] = sname + ' (' + tid + ')'
            x += width * self.MM2PT
            xmarks.append(x)

        # <x> is now the maximum x-coordinate
        y = 0.0
        h = HEIGHT_TITLE * self.MM2PT
        self.addItem (Tile (None, '_TITLE', 0.0, y, x, h,
                fieldnames ['_TITLE'],
                titleStyle))
        y += h

#        ysep.append (y)
        y += YSEPH
        ### "info" fields
        h = HEIGHT_INFO * self.MM2PT
        for ik, iv in fieldnames.items():
            try:
                val = gradeInfo.groupInfo[ik]
            except:
                continue
            self.addItem(Tile (None, None, 0.0, y, xmarks[0], h,
                    '#', infoStyle))
            self.addItem(Tile (None, None, xmarks[0], y,
                    xmarks[1] - xmarks[0], h,
                    iv, infoStyle))
            # The "sid" field is here the info-key
            w = xmarks[-1] - xmarks[1]
            if ik [0] == '_':
                # Read-only
                self.addItem(Tile(None, ik, xmarks[1], y, w, h,
                        val, infoStyle))
            elif ik.endswith('_D'):
                # For a date in the form yyyy-mm-dd
                self.addItem(Tile(None, ik, xmarks[1], y, w, h,
                        val, infoStyle, dateEdit))
            else:
                # Text editor as validator
                self.addItem(Tile (None, ik, xmarks[1], y, w, h,
                        val, infoStyle, lineEdit))
            y += h

        ysep.append(y)
        y += YSEPH
        y0 = y

        ### Add header line for the main table
        h = HEIGHT_SBJ * self.MM2PT
        self.addItem(Tile (None, None, 0.0, y, xmarks[1], h,
                fieldnames['%subject'], taghStyle))
        for sid, n in sid_ncol.items():
            x0 = xmarks[n-1]
            self.addItem(Tile (None, None, x0, y, xmarks[n] - x0, h,
                    sid_name[sid], v2Style, bg=sid_bg[sid]))
        y += h

        ysep.append(y)
        y += YSEPH

        ### Grade area
        h = HEIGHT_ROW * self.MM2PT
#
#        pdata = gradeInfo.classData
#        for pid, sid_grades in gradeInfo.pids.items ():
#
        for pid in ('1234', '1235', '1236', '1237'):
#?
            sid_grades = {'En': '3', 'Ma': 'nb', 'Bio': '4'}

            self.addItem(Tile (None, None, 0.0, y, xmarks[0], h,
                    pid, tagStyle, None))
            self.addItem(Tile (None, None, xmarks[0], y,
                    xmarks[1] - xmarks[0], h,
#                    pdata[pid].name, h1Style, None))
                    'Markus Mustermann', h1Style, None))
            for sid, n in sid_ncol.items():
#?
                if sid in sid_grades:
#                    g = sid_grades[sid]['ENTRY']
                    g = sid_grades[sid]
                    try:
                        v = editors[sid]
                    except:
                        v = None
                    bg = sid_bg[sid]
                else:
                    g = INVALID_CELL
                    s = invalidStyle
                    v = None
                    bg = bgclrs['INVALID']
                x0 = xmarks[n-1]
                self.addItem(Tile (pid, sid, x0, y, xmarks[n] - x0, h,
                        g, entryStyle, v, bg = bg))
            y += h

        # <y> is now the maximum y-coordinate

        ### Separators
        bg = bgclrs['SPACER']
        for xs in xsep:
            self.addItem(Tile (None, None, xs, y0, XSEPW, y-y0,
                    None, padStyle, bg = bg))
        for ys in ysep:
            self.addItem(Tile (None, None, 0.0, ys, x, YSEPH,
                    None, padStyle, bg = bg))












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
        self.gradeView = GradeGrid()
        topbox.addWidget(self.gradeView)
        topbox.addWidget(VLine())

#        self.gradeView.setToolTip ('This shows the <b>grades</b> for a class')
        bbox = QHBoxLayout()
        pbSmaller = QPushButton(ZIcon('zoom-out'), '')
        pbSmaller.clicked.connect(self.gradeView.scaleDn)
        pbLarger = QPushButton(ZIcon('zoom-in'), '')
        pbLarger.clicked.connect(self.gradeView.scaleUp)
        bbox.addWidget(pbLarger)
        bbox.addWidget(pbSmaller)

        cbox = QVBoxLayout()
        cbox.addLayout(bbox)
        self.yearSelect = KeySelect([(y, print_schoolyear(y))
                for y in Dates.get_years()],
                self.changedYear)
        self.categorySelect = KeySelect(Grades.categories(),
                self.changedCategory)
# Rather use another KeySelect?:
        self.select = QListWidget()
        self.select.setMaximumWidth(150)
        self.select.itemClicked.connect(self.changeSelection)
        cbox.addWidget(self.yearSelect)
        cbox.addWidget(self.categorySelect)
        cbox.addWidget(self.select)
        pbPdf = QPushButton('PDF')
        cbox.addWidget(pbPdf)
        pbPdf.clicked.connect(self.gradeView.toPdf)
        topbox.addLayout(cbox)
        self.yearSelect.trigger()

# after "showing"?
#        pbSmaller.setFixedWidth (pbSmaller.height ())
#        pbLarger.setFixedWidth (pbLarger.height ())

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
class GradeInfo(GradeValues):
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

    gradeEdit("View/Edit grades", schoolyear, date)
