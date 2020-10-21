### python >= 3.7
# -*- coding: utf-8 -*-
"""
grid.py

Last updated:  2020-10-20

Widget with editable tiles on grid layout (QGraphicsScene/QGraphicsView).


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

#TODO:
#  - Consider replacing graphicsitem popups by modal dialogs (like for date).

##### Configuration #####################
FONT_DEFAULT = 'Arial'
FONT_SIZE_DEFAULT = 11

# Line width (indexed table: 0 - 3) for borders
LINE_WIDTH = (0, 1.0, 2.0, 3.0)

_DATE_POPUP = "Datum wählen"

#####################

### Messages
_TILE_OUT_OF_BOUNDS = ("Kachel außerhalb Tabellenbereich:\n"
        " Zeile {row}, Höhe {rspan}, Spalte {col}, Breite {cspan}")
_INVALIDLINEWIDTH = "Ungültige Strichbreite: {val}"
_NOTSTRING          = "In <grid::Tile>: Zeichenkette erwartet: {val}"

#####################################################

import sys, os, copy
if __name__ == '__main__':
    # Enable package import if running as module
    this = sys.path[0]
    sys.path[0] = os.path.dirname(this)

from qtpy.QtWidgets import (QLineEdit,
    QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsLineItem,
    QGraphicsProxyWidget,
    QCalendarWidget, QVBoxLayout, QLabel,
    QFileDialog, QDialog, QDialogButtonBox)
from qtpy.QtGui import (QFont, QPen, QColor, QBrush, QTransform,
        QPainter, QPdfWriter, QPageLayout)
from qtpy.QtCore import Qt, QDate, QMarginsF, QRectF, QBuffer, QByteArray

from grades_gui.gui_support import PopupError

class GridError(Exception):
    pass


class Grid(QGraphicsView):
    """This is the grid widget.
    Rows and columns are 0-indexed.
    """
    def __init__(self):
        self._scale = 1.0
        super ().__init__()
        self.ldpi = self.logicalDpiX()
        if self.logicalDpiY() != self.ldpi:
            REPORT("WARNING: LOGICAL DPI different for x and y")
        self.MM2PT = self.ldpi / 25.4
#        self._popup = None
#        self._scene = None
#        self.xmarks = None
#        self.ymarks = None
        self.DEFAULT_STYLE = CellStyle(FONT_DEFAULT, FONT_SIZE_DEFAULT,
                align = 'c', border = 1)


    def setTable(self, rowheights, columnwidths):
        """Set the grid size.
            <columnwidths>: a list of column widths (mm)
            <rowheights>: a list of row heights (mm)
        Calling this function will delete all existing data.
        """
        self.tagmap = {}
        self._scene = QGraphicsScene()
        self.xmarks = [0.0]
        x = 0.0
        for c in columnwidths:
            x += c * self.MM2PT
            self.xmarks.append(x)
        self.ymarks = [0.0]
        y = 0.0
        for r in rowheights:
            y += r * self.MM2PT
            self.ymarks.append(y)
# Allow a little margin? e.g.(-1.0, -1.0, x + 1.0, y + 1.0)
        self._sceneRect = QRectF(0.0, 0.0, x, y)
#?        self._scene.setSceneRect(self._sceneRect)
        self.setScene(self._scene)
        # Fix the view's scene area (pop-ups could otherwise extend it)
        self.setSceneRect(self._sceneRect)
        # For popup editors
        self.editors = {
            'LINE': PopupLineEdit(self),
            'DATE': PopupDate(self)
        }
        self._popup = None

    def ncols(self):
        return len(self.xmarks) - 1

    def nrows(self):
        return len(self.ymarks) - 1

    def viewWH(self):
        """Return the width and height of the viewing area scaled to
        scene coordinates.
        """
        vp = self.viewport()
        vw1 = vp.width()
        vh1 = vp.height()
        spoint = self.mapToScene(vw1, vh1)
        return (spoint.x(), spoint.y())


    ### Methods dealing with cell editing
    def editCell(self, tile, x, y, validation):
        self.popdown(True)
        self._popup = validation
        validation.activate(tile, x, y)

    def popdown (self, force = False):
        if self._popup != None and self._popup.hideMe(force):
            self._popup = None

    def mousePressEvent(self, event):
        point = event.pos()
#        print("POS:", point, self.mapToGlobal(point), self.itemAt(point))
# The Tile may not be the top item.
        if self.items(point):
            return super().mousePressEvent(event)
        self.popdown(True)

    def addSelect(self, tag, valuelist):
        if tag in self.editors:
            raise Bug(_EDITOR_TAG_REUSED.format(tag = tag))
        self.editors[tag] = PopupTable(self, valuelist)


    ### View scaling
    def scaleUp (self):
        self.scale(1)

    def scaleDn (self):
        self.scale(-1)

    def scale(self, delta):
        t = QTransform()
        self._scale += self._scale * delta / 10
        t.scale(self._scale, self._scale)
        self.setTransform(t)
    ### ---------------


    ### pdf output
    def setPdfMargins(self, left = 20, top = 20, right = 20, bottom = 20):
        self._pdfmargins = (left, top, right, bottom)
        return self._pdfmargins

    def pdfMargins(self):
        try:
            return self._pdfmargins
        except AttributeError:
            return self.setPdfMargins()

    def toPdf(self, filename = None):
        """Produce and save a pdf of the table.
        <filename> is a suggestion for the save dialog.
        The output orientation is selected according to the aspect ratio
        of the table.
        """
#TODO:
#    - Fixed / selectable page orientation.
#    - Select page size
#    - Shrink to page size

        qbytes = QByteArray()
        qbuf = QBuffer(qbytes)
        qbuf.open(qbuf.WriteOnly)
        printer = QPdfWriter(qbuf)
        printer.setPageSize(printer.A4)
        printer.setPageMargins(QMarginsF(*self.pdfMargins()),
                QPageLayout.Millimeter)
        sceneRect = self._sceneRect
        sw = sceneRect.width()
        sh = sceneRect.height()
        if sw > sh:
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        painter = QPainter(printer)
        scale = printer.resolution() / self.ldpi
        pdfRect = QRectF(0, 0, sw * scale, sh * scale)
        self.scene().render(painter, pdfRect, sceneRect)
        painter.end()
        qbuf.close()
        # Write resulting file
        QFileDialog.saveFileContent(qbytes, filename or 'grid.pdf')
    ### ---------------


    def tile(self, row, col, text = None, cspan = 1, rspan = 1,
            style = None, validation = None, tag = None):
        """Add a tile to the grid.
        If <tag> is not set, it will be set to '#row:col'.
        """
        # Check bounds
        if (row < 0 or col < 0
                or (row + rspan) >= len(self.ymarks)
                or (col + cspan) >= len(self.xmarks)):
            raise GridError(_TILE_OUT_OF_BOUNDS.format(
                row = row, col = col, cspan = cspan, rspan = rspan))
        x = self.xmarks[col]
        y = self.ymarks[row]
        w = self.xmarks[col + cspan] - x
        h = self.ymarks[row + rspan] - y
        if not tag:
            tag = '#%d:%d' % (row, col)
        t = Tile(self, tag, x, y, w, h, text,
                style or self.DEFAULT_STYLE, validation)
        self._scene.addItem(t)
        self.tagmap[tag] = t


    def valueChanged(self, tag, text):
        """Cell-changed callback.
        This should be overridden if it is needed.
        """
        pass



class CellStyle:
    """Handle various aspects of cell styling.
    Also manage caches for fonts, pens and brushes.
    """
    _fonts = {}
    _brushes = {}
    _pens = {}

    @classmethod
    def getFont(cls, fontFamily, fontSize, fontBold, fontItalic):
        ftag = (fontFamily, fontSize, fontBold, fontItalic)
        try:
            return cls._fonts[ftag]
        except:
            pass
        font = QFont()
        if fontFamily:
            font.setFamily(fontFamily)
        if fontSize:
            font.setPointSizeF(fontSize)
        if fontBold:
            font.setBold(True)
        if fontItalic:
            font.setItalic(True)
        cls._fonts[ftag] = font
        return font


    @classmethod
    def getPen(cls, width):
        """Manage a cache for pens of different width.
        """
        width = width or 0
        try:
            return cls._pens[width]
        except:
            pass
        try:
            widthF = LINE_WIDTH[width]
        except IndexError as e:
            raise GridError(_INVALIDLINEWIDTH.format(val = width)) from e
        pen = QPen()
        if width == 0:
            pen.setStyle(Qt.NoPen)
        else:
            pen.setWidthF(widthF)
        cls._pens[width] = pen
        return pen


    @classmethod
    def getBrush(cls, colour):
        """Manage a cache for brushes of different colour.
        <colour> is a colour in the form 'RRGGBB'.
        """
        try:
            return cls._brushes[colour]
        except:
            pass
        brush = QBrush(QColor('#FF' + colour))
        cls._brushes[colour] = brush
        return brush


    def __init__(self, font, size, align = 'c', highlight = None,
            bg = None, border = 1):
        """
        <font> is the name of the font (<None> => default, not recommended,
            unless the cell is to contain no text).
        <size> is the size of the font (<None> => default, not recommended,
            unless the cell is to contain no text).
        <align> is the horizontal (l, c or r) OR vertical (b, m, t) alignment.
            Vertical alignment is for rotated text (-90° only).
        <highlight> can set bold, italic and font colour: 'bi:RRGGBB'. All bits
            are optional, but the colon must be present if a colour is given.
        <bg> can set the background colour ('RRGGBB').
        <border>: Only three border types are supported here:
            0: none
            1: all sides
            2: (thicker) underline
        """
        # Font
        self.setFont(font, size, highlight)
        # Alignment
        self.setAlign(align)
        # Background colour
        self.bgColour = self.getBrush(bg) if bg else None
        # Border
        self.border = border

    def setFont(self, font, size, highlight):
        self._font, self._size, self._highlight = font, size, highlight
        try:
            emph, clr = highlight.split(':')
        except:
            emph, clr = highlight or '', None
        self.fontColour = self.getBrush(clr) if clr else None
        self.font = self.getFont(font, size, 'b' in emph, 'i' in emph)

    def setAlign(self, align):
        if align in 'bmt':
            # Vertical
            self.alignment = ('c', align, True)
        else:
            self.alignment = (align, 'm', False)

    def copy(self, font = None, size = None, align = None,
            highlight = None, bg = None, border = None):
        """Make a copy of this style, but with changes specified by the
        parameters.
        Note that a change to a 'None' parameter value is not possible.
        """
        newstyle = copy.copy(self)
        if font or size or highlight:
            newstyle.setFont(font or self._font,
                    size or self._size, highlight or self._highlight)
        if align:
            newstyle.setAlign(align)
        if bg:
            self.bgColour = self.getBrush(bg)
        if border:
            self.border = border
        return newstyle


class Tile(QGraphicsRectItem):
    """The graphical representation of a table cell.
    This cell can span rows and columns.
    """
    def __init__(self, grid, tag, x, y, w, h, text, style, validation):
        self._grid = grid
        self.tag = tag
        self.height0 = h
        self.width0 = w
        self.validation = validation
        super().__init__(0, 0, w, h)
        self.setFlag(self.ItemClipsChildrenToShape, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setPos(x, y)

        # Background colour
        if style.bgColour != None:
            self.setBrush(style.bgColour)

        # Border
        if style.border == 1:
            # Set the pen for the rectangle boundary
            pen0 = CellStyle.getPen(1)
        else:
            # No border for the rectangle
            pen0 = CellStyle.getPen(None)
            if style.border != 0:
                # Thick underline
                line = QGraphicsLineItem(self)
                line.setPen(CellStyle.getPen(2))
                line.setLine(0, h, w, h)
        self.setPen(pen0)

        # Alignment and rotation
        self.halign, self.valign, self.rotation = style.alignment
        # Text
        self.textItem = QGraphicsSimpleTextItem(self)
        self.textItem.setFont(style.font)
        if style.fontColour != None:
            self.textItem.setBrush(style.fontColour)
        if text != None:
            self.setText(text)


    def margin(self):
        return 1.0 * self._grid.MM2PT


    def value(self):
        return None if self.textItem == None else self.textItem.text()


    def setText(self, text):
        if type(text) != str:
            raise Bug(_NOTSTRING.format(val = repr(text)))
        self.textItem.setText(text)
        w = self.textItem.boundingRect().width()

        if self.rotation:
            maxh = self.height0 - self.margin() * 2
            if w > maxh:
                self.textItem.setScale(maxh / w)
            trf = QTransform().rotate(-90)
            self.textItem.setTransform(trf)
            bdrect = self.textItem.mapRectToParent(
                    self.textItem.boundingRect())
            yshift = - bdrect.top()
        else:
            maxw = self.width0 - self.margin() * 2
            if w > maxw:
                self.textItem.setScale(maxw / w)
            bdrect = self.textItem.mapRectToParent(
                    self.textItem.boundingRect())
            yshift = 0.0
        w = bdrect.width()
        h = bdrect.height()
        xshift = 0.0
        if self.halign == 'l':
            xshift += self.margin()
        elif self.halign == 'r':
            xshift += self.width0 - self.margin() - w
        else:
            xshift += (self.width0 - w) / 2
        if self.valign == 't':
            yshift += self.margin()
        elif self.valign == 'b':
            yshift += self.height0 - self.margin() - h
        else:
            yshift += (self.height0 - h) / 2
        self.textItem.setPos(xshift, yshift)


    def mousePressEvent(self, event):
        if self.validation:
#            point = event.scenePos ()
            point = self.pos()
            # Select type of popup and activate it
            self._grid.editCell(self, point.x(), point.y(),
                    self.validation)
        else:
            # This should cause any existing pop-up to be cancelled
            self._grid.popdown(True)


    def newValue(self, text):
        """Called with the new value. The tile should be updated and the
        callback invoked.
        """
        self.setText(text)
        self._grid.valueChanged(self.tag, text)



class MiniTile(QGraphicsRectItem):
    """A small tile for the grid view – specifically for the table popup.
    """
    def __init__(self, parent, x, y, w, h, textitem):
        super().__init__(0, 0, w, h, parent)
        self.width = w
        self.height = h
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.textItem = textitem
        textitem.setParentItem(self)
        self.adjust()
        self.setBrush(parent.normalBrush)
        self.setPos(x, y)

    def setText(self, text):
        self.textItem.setText(text)
        self.adjust()

    def adjust(self):
        bdrect = self.textItem.boundingRect()
        wt = bdrect.width()
        xshift = (self.width - wt) / 2
        ht = bdrect.height()
        yshift = (self.height - ht) / 2
        self.textItem.setPos(xshift, yshift)

    def hoverEnterEvent(self, event):
        self.setBrush(self.parentItem().highlightBrush)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.parentItem().normalBrush)

    def mousePressEvent(self, event):
        self.hoverLeaveEvent(None)
        self.parentItem().selected(self.textItem.text())



class PopupTable(QGraphicsRectItem):
    """A selection-table popup for the grid view.
    """
    def __init__(self, grid, items):
        self._grid = grid
        texts = []
        w0, h0 = 0, 0
        for item in items:
            t = QGraphicsSimpleTextItem(item)
            texts.append(t)
            br = t.boundingRect()
            w = br.width()
            if w > w0:
                w0 = w
            h = br.height()
            if h > h0:
                h0 = h
        texts.append(QGraphicsSimpleTextItem(''))
        w0 += 5
        h0 += 5

        rows = (len (texts) + 2) // 3
        self.boxwidth = w0*3 + 2
        self.boxheight = h0*rows + 2
        super().__init__(0, 0, self.boxwidth, self.boxheight)
        self.setZValue(10)
        self.setVisible(False)
        grid._scene.addItem(self)
        pen = QPen(QColor('#ff0040'))
        pen.setWidth(2)
        self.setPen(pen)

        self.normalBrush = QBrush(QColor('#ffffff'))
        self.highlightBrush = QBrush(QColor('#ffe080'))
        self.setBrush(self.normalBrush)
        x = 1
        y = 1
        ncols = 3
        n = 0
        i = len(texts)
        for t in texts:
            i -= 1
            if i == 0:
                # Last tile (null)
                w0 *= (3 - n)
            MiniTile(self, x, y, w0, h0, t)
            n += 1
            if n >= ncols:
                n = 0
                x = 1
                y += h0
            else:
                x += w0

    def hideMe(self, force):
        """This should be called only by <GridView.popdown>.
        This popup is hidden regardless of <force> as the
        only interesting click is on one of the values.
        """
        self.setVisible(False)
        return True

    def activate(self, tile, x, y):
        # x and y are scene coordinates.
        # Get the visible area by converting view width and height to scene
        # coordinates ...
        self.tile = tile
        # Try to keep the popup within the grid area
        sx, sy = self._grid.viewWH()
        overlapx = sx - (x + self.boxwidth + 2)
        overlapy = sy - (y + self.boxheight + 2)
        if overlapx < 0:
            x += overlapx
            if x < 0:
                x = 0
        if overlapy < 0:
            y += overlapy
            if y < 0:
                y = 0
        self.setPos(x, y)
        self.setVisible(True)


    def selected(self, text):
        self.setVisible(False)
        self.tile.newValue(text)


class PopupDate(QDialog):
    def __init__(self, grid):
        self._grid = grid
        super().__init__()
        vbox = QVBoxLayout(self)
        self.cal = QCalendarWidget(self)
        self.cal.setGridVisible(True)
        self.cal.clicked[QDate].connect(self.newDate)
        vbox.addWidget(self.cal)
        self.lbl = QLabel(self)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok
                | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        vbox.addWidget(self.lbl)
        vbox.addWidget(buttonBox)
        self.setLayout(vbox)
        self.setWindowTitle(_DATE_POPUP)
#        self.setWindowFlags(Qt.SplashScreen)

    def activate(self, tile, x, y):
        # Set date
        self.tile = tile
        date = tile.value()
        self.cal.setSelectedDate(QDate.fromString(date, 'yyyy-MM-dd')
                if date else QDate.currentDate())
        self.newDate(self.cal.selectedDate())
        viewp = self._grid.mapFromScene(x, y)
        self.move(self._grid.mapToGlobal(viewp))
        if self.exec_():
            self.tile.newValue(self.date)

    def newDate(self, date):
        self.lbl.setText(QLocale().toString(date))
        self.date = date.toString('yyyy-MM-dd')

    def hideMe(self, force):
        """This should be called only by <Grid.popdown>.
        Here it is a dummy function because <PopupDate> is a modal
        dialog.
        """
        return True


class PopupLineEdit(QGraphicsProxyWidget):
    """A line editor.
    Press enter-key to accept new text.
    """
    def __init__(self, grid):
        self._grid = grid
        super().__init__()
        self.setZValue(10)
        self.lineedit = QLineEdit()
        self.lineedit.setStyleSheet("background-color: #c0c0ff")
#        self.lineedit.editingFinished.connect(self.onDone)
        self.lineedit.returnPressed.connect(self.onDone)
        self.setWidget(self.lineedit)
        self.setVisible(False)
        grid._scene.addItem(self)

    def hideMe(self, force):
        """This should be called only by <Grid.popdown>.
        It hides only when <force> is true because the widget needs to
        capture clicks.
        """
        if force:
            self.setVisible(False)
            return True
        return False

    def activate(self, tile, x, y):
        """Start the editing widget.
        x and y are scene coordinates.
        """
        # Get the visible area by converting view width and height to scene
        # coordinates ...
        self.tile = tile
        w = tile.width0
        if w < 50.0:
            w = 50.0
        self.lineedit.setFixedWidth(w)
        self.lineedit.setText(tile.value() or '')
        self.setPos(x, y)
        self.setVisible(True)
        self.lineedit.setFocus()

# If signal "editingFinished" is used in place of "returnPressed", this
# method is called twice on pressing "Enter".
    def onDone(self):
        self._grid.popdown(True)
        text = self.lineedit.text()
        self.tile.textItem.setText(text)
        self.tile.newValue(text)




if __name__ == '__main__':
    from core.base import init
    init('TESTDATA')

    from qtpy.QtWidgets import QApplication, QDialog, QHBoxLayout, \
            QPushButton
    from qtpy.QtCore import QLocale, QTranslator, QLibraryInfo

    app = QApplication(sys.argv)
    LOCALE = QLocale(QLocale.German, QLocale.Germany)
    QLocale.setDefault(LOCALE)
    qtr = QTranslator()
    qtr.load("qt_" + LOCALE.name(),
            QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtr)

    window = QDialog()
    grid = Grid()

    topbox = QHBoxLayout(window)
    topbox.addWidget(grid)

#        self.gradeView.setToolTip ('This shows the <b>grades</b> for a class')
#        bbox = QHBoxLayout ()
    pb = QPushButton('–')
#    pb.clicked.connect(function)
    topbox.addWidget(pb)

    # Add some data
    titleStyle = CellStyle('Serif', size = 12, align = 'c', border = 2)

    rows = (10, 2, 6, 6, 6, 6, 6)
    cols = (25, 10, 8, 20, 8, 8, 25)
    grid.setTable(rows, cols)

    # Title
    grid.tile(0, 0, cspan = len(cols), text = "Table Testing",
                style = titleStyle)

    editS = PopupTable(grid,
            ('1', '2', '3', '4', '5', '6', 'nb', 'nt', '*', '/'))
    editD = PopupDate(grid)
    editL = PopupLineEdit(grid)

    grid.tile(2, 0, tag = 'd1', text = "2020-08-10", validation = editD)
    grid.tile(2, 6, tag = 'd2', text = "2020-09-02", validation = editD)
# Why isn't the date centred? It is connected with shrink-fitting!
    grid.tile(4, 3, tag = 'd3', text = "2020-02-09", validation = editD)
    grid.tile(6, 0, tag = 'd4', text = "2020-01-31", validation = editD)
    grid.tile(6, 6, tag = 'd5', text = "2020-12-01", validation = editD)

    grid.tile(5, 4, tag = 'g1', text = "4", validation = editS)
    grid.tile(3, 2, tag = 'g2', validation = editS)

    grid.tile(3, 0, cspan = 2, tag = 't1', validation = editL, text = "Text")
    grid.tile(4, 5, tag = 't2', validation = editL, text = "X")

    window.exec_()
