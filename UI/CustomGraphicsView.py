import math
import weakref
from typing import List, Optional
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QWidget, QGraphicsProxyWidget, \
    QGraphicsRectItem, \
    QVBoxLayout, QLabel, QFrame
from PySide6.QtGui import QPen, QColor, QPainter, QBrush, QTransform, QGuiApplication, QPalette
from PySide6.QtCore import Qt, QPointF, QSizeF, QRectF, QLineF, QRect, QMarginsF, QPoint, QTimer
from UI.UIMaster import UIMaster
from enum import Enum, auto
from functools import reduce


class CustomGraphicsViewState(Enum):
    IDLE = auto()
    PANNING = auto()
    MOVING = auto()
    RESIZING = auto()
    BAND_SELECTING = auto()


class CustomGraphicsViewItem:
    def __init__(self, name, itemWidget: QWidget, inspectorWidget: QWidget = None):
        self.itemProxy = QGraphicsProxyWidget()
        self.itemProxy.setWidget(itemWidget)
        if inspectorWidget is None:
            self.inspectorProxy = None
        else:
            self.inspectorProxy = QGraphicsProxyWidget()
            widget = QFrame()
            widget.setFrameShape(QFrame.Shape.Box)
            widget.setLayout(QVBoxLayout())
            widget.layout().setContentsMargins(0, 0, 0, 0)
            widget.layout().setSpacing(0)
            widget.layout().addWidget(inspectorWidget)
            self.inspectorProxy.setWidget(widget)
        self.borderRectItem = QGraphicsRectItem()
        self.updateTimer = QTimer(self.itemProxy)
        self.updateTimer.timeout.connect(self._Update)
        self.updateTimer.start(100)
        self.isResizable = True
        self.isUpdating = False
        self._Update()

    def SetEnabled(self, state):
        self.itemProxy.setEnabled(state)

    def _Update(self):
        self.isUpdating = True
        self.Update()
        self.isUpdating = False

    def Update(self):
        pass

    def GetRect(self):
        return self.itemProxy.sceneBoundingRect()

    def SetRect(self, rect: QRectF):
        self.itemProxy.setPos(rect.topLeft())
        self.itemProxy.resize(rect.size())
        self.UpdateGeometry()

    def UpdateGeometry(self):
        rect = self.GetRect()
        self.borderRectItem.setRect(rect)
        if self.inspectorProxy is not None:
            self.inspectorProxy.setPos(rect.topLeft() - QPointF(0,
                                                                self.inspectorProxy.sceneBoundingRect().height()))

    def OnRemoved(self):
        pass

    def Duplicate(self) -> 'CustomGraphicsViewItem':
        pass


class CustomGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()

        # Set up view
        self.setScene(QGraphicsScene())
        self.setMouseTracking(True)
        self.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing |
            QPainter.VerticalSubpixelPositioning)

        # State
        self.viewOffset = QPointF(0, 0)
        self.zoom = 1
        self.state = CustomGraphicsViewState.IDLE
        self.allItems: List[CustomGraphicsViewItem] = []
        self.selectedItems: List[CustomGraphicsViewItem] = []
        self.isInteractive = True

        # Grid settings
        self.gridSpacing = QSizeF(50, 50)
        self.gridThickness = 1
        self.gridZoomThreshold = 0.25
        self.showGrid = True

        # Mouse control and state
        self.scrollSensitivity = 1 / 1000
        self.mouseDeltaScenePosition = QPointF()
        self.mouseScenePosition = QPointF()
        self._lastMouseViewPosition = QPoint()
        self.itemUnderMouse: Optional[CustomGraphicsViewItem] = None
        self.resizeHandleIndexUnderMouse = -1
        self.isInspectorUnderMouse = False

        # Selection box and transformation handles
        self.selectionBoxRectItem = QGraphicsRectItem()
        self.selectionBoxRectItem.setBrush(Qt.NoBrush)
        self.selectionBoxRectScreenSize = 2
        self.selectionBoxRectColor = QColor(200, 200, 255)
        self.selectedItemBorderSize = 4
        self.hoverItemBorderSize = 3
        self.selectedItemBorderColor = QColor(200, 200, 255)
        self.hoverItemBorderColor = QColor(200, 200, 255)
        self.scene().addItem(self.selectionBoxRectItem)

        self._transformStartMousePos = QPointF()
        self._transformResizeHandleIndex = -1
        self._transformStartRects: List[QRectF] = []

        self.resizeHandleScreenSize = 5
        self.resizeHandleBorderScreenSize = 1
        self.resizeHandleColor = QColor(100, 100, 255)
        self.resizeHandleBorderColor = QColor(100, 100, 255)
        self.resizeHandles = [QGraphicsRectItem() for _ in range(8)]
        [self.scene().addItem(h) for h in self.resizeHandles]

        # Rubber band selection
        self.rubberBandRectItem = QGraphicsRectItem()
        self.rubberBandRectItem.setBrush(Qt.NoBrush)
        self.rubberBandRectScreenSize = 2
        self.rubberBandRectColor = QColor(200, 200, 255)
        self.rubberBandAnchor = QPointF()
        self.scene().addItem(self.rubberBandRectItem)
        self.rubberBandRectItem.setVisible(False)

        # Initialization
        self.UpdateViewMatrix()
        self.UpdateSelectionDisplay()
        self.UpdateSelectionBox()
        self.UpdateInspectors()
        self.UpdateCursor()

        self.updateTimer = QTimer(self)
        self.updateTimer.timeout.connect(self.Update)
        self.updateTimer.start(100)

    def Clear(self):
        self.DeleteItems(self.allItems.copy())

    def Update(self):
        self.UpdateSelectionDisplay()

    def UpdateViewMatrix(self):
        transform = QTransform()
        transform.scale(self.zoom, self.zoom)
        self.setTransform(transform)
        self.setSceneRect(QRectF(self.viewOffset, QSizeF(1, 1)))

    def SelectAll(self):
        self.SelectItems(self.allItems)

    def CenterOnSelection(self):
        if len(self.selectedItems) == 0:
            return
        selectionRect = reduce(QRectF.united, [item.GetRect() for item in self.selectedItems])
        self.viewOffset = selectionRect.center()
        self.UpdateViewMatrix()

    def ZoomBounds(self):
        if len(self.allItems) == 0:
            return
        itemRect: QRectF = reduce(QRectF.united, [item.GetRect() for item in self.allItems])
        self.zoom = 1 / math.log10(max(itemRect.width(), itemRect.height()))
        self.viewOffset = itemRect.center()
        self.UpdateViewMatrix()

    def UpdateZoom(self, scenePositionAnchor: QPointF, newZoom: float):
        anchorScreenSpace = self.mapFromScene(scenePositionAnchor)
        self.zoom = min(max(newZoom, 0.05), 2)
        self.UpdateViewMatrix()
        newAnchorPosition = self.mapToScene(anchorScreenSpace)
        self.viewOffset -= newAnchorPosition - scenePositionAnchor
        self.UpdateViewMatrix()
        self.UpdateSelectionDisplay()
        self.UpdateInspectors()

    def UpdateMouseInfo(self, mousePosition: QPoint):
        self.mouseScenePosition = self.mapToScene(mousePosition)
        self.mouseDeltaScenePosition = self.mouseScenePosition - self.mapToScene(
            self._lastMouseViewPosition)
        self._lastMouseViewPosition = mousePosition

        self.isInspectorUnderMouse = False
        self.itemUnderMouse = None
        self.resizeHandleIndexUnderMouse = -1
        for item in self.allItems:
            if item.inspectorProxy is not None and item.inspectorProxy.isVisible():
                itemUnder = item.inspectorProxy.contains(
                    item.inspectorProxy.mapFromScene(self.mouseScenePosition))
                if itemUnder:
                    self.isInspectorUnderMouse = True
                    return

        for i, handle in enumerate(self.resizeHandles):
            if handle.contains(self.mouseScenePosition):
                self.resizeHandleIndexUnderMouse = i
                return

        for item in sorted(self.allItems, key=lambda x: x.itemProxy.zValue(), reverse=True):
            if item.itemProxy.isUnderMouse():
                self.itemUnderMouse = item
                return

    def IsWindowFocused(self):
        focusItem = self.scene().focusItem()
        return focusItem is not None and focusItem.isWindow()

    def UpdateCursor(self):
        if self.state == CustomGraphicsViewState.PANNING:
            UIMaster.SetCursor(Qt.ClosedHandCursor)
        elif self.state == CustomGraphicsViewState.MOVING:
            UIMaster.SetCursor(Qt.SizeAllCursor)
        elif self.state == CustomGraphicsViewState.RESIZING:
            if self._transformResizeHandleIndex == 0 or self._transformResizeHandleIndex == 7:
                UIMaster.SetCursor(Qt.SizeFDiagCursor)
            if self._transformResizeHandleIndex == 1 or self._transformResizeHandleIndex == 6:
                UIMaster.SetCursor(Qt.SizeVerCursor)
            if self._transformResizeHandleIndex == 2 or self._transformResizeHandleIndex == 5:
                UIMaster.SetCursor(Qt.SizeBDiagCursor)
            if self._transformResizeHandleIndex == 3 or self._transformResizeHandleIndex == 4:
                UIMaster.SetCursor(Qt.SizeHorCursor)
        elif self.state == CustomGraphicsViewState.IDLE:
            if self.resizeHandleIndexUnderMouse >= 0:
                if self.resizeHandleIndexUnderMouse == 0 or self.resizeHandleIndexUnderMouse == 7:
                    UIMaster.SetCursor(Qt.SizeFDiagCursor)
                if self.resizeHandleIndexUnderMouse == 1 or self.resizeHandleIndexUnderMouse == 6:
                    UIMaster.SetCursor(Qt.SizeVerCursor)
                if self.resizeHandleIndexUnderMouse == 2 or self.resizeHandleIndexUnderMouse == 5:
                    UIMaster.SetCursor(Qt.SizeBDiagCursor)
                if self.resizeHandleIndexUnderMouse == 3 or self.resizeHandleIndexUnderMouse == 4:
                    UIMaster.SetCursor(Qt.SizeHorCursor)
            elif self.itemUnderMouse in self.selectedItems and not self.WidgetUnderMouseAlwaysInteractable():
                UIMaster.SetCursor(Qt.SizeAllCursor)
            else:
                UIMaster.SetCursor(None)
        else:
            UIMaster.SetCursor(None)

    @staticmethod
    def Snap(x, div):
        if QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier:
            return x
        return round(float(x) / div) * div

    def WidgetUnderMouseAlwaysInteractable(self):
        if self.itemUnderMouse is None:
            return False
        p = self.itemUnderMouse.itemProxy.mapFromScene(self.mouseScenePosition).toPoint()
        item = self.itemUnderMouse.itemProxy.widget().childAt(p)
        while item is not None and item != self.itemUnderMouse.itemProxy.widget():
            if item.property("AlwaysInteractable"):
                return True
            item = item.parentWidget()
        return False

    def SnapPoint(self, p: QPointF):
        return QPointF(self.Snap(p.x(), self.gridSpacing.width()),
                       self.Snap(p.y(), self.gridSpacing.height()))

    def DoMove(self):
        moveDelta = self.mouseScenePosition - self._transformStartMousePos
        for startRect, item in zip(self._transformStartRects, self.selectedItems):
            newRect = startRect.translated(moveDelta)
            snapOffsets = (self.SnapPoint(newRect.topLeft()) - newRect.topLeft(),
                           self.SnapPoint(newRect.topRight()) - newRect.topRight(),
                           self.SnapPoint(newRect.bottomLeft()) - newRect.bottomLeft(),
                           self.SnapPoint(newRect.bottomRight()) - newRect.bottomRight())
            magnitudes = [d.x() ** 2 + d.y() ** 2 for d in snapOffsets]
            minOffset = min(zip(magnitudes, snapOffsets), key=lambda x: x[0])[1]
            item.SetRect(newRect.translated(minOffset))
        self.UpdateSelectionBox()

    def DoResize(self):
        resizeDelta = self.mouseScenePosition - self._transformStartMousePos
        initialRect = self._transformStartRects[0]
        for r in self._transformStartRects:
            initialRect = initialRect.united(r)
        newRect = QRectF(initialRect)
        if self._transformResizeHandleIndex == 0:
            newRect.setTopLeft(self.SnapPoint(newRect.topLeft() + resizeDelta))
        elif self._transformResizeHandleIndex == 2:
            newRect.setTopRight(self.SnapPoint(newRect.topRight() + resizeDelta))
        elif self._transformResizeHandleIndex == 5:
            newRect.setBottomLeft(self.SnapPoint(newRect.bottomLeft() + resizeDelta))
        elif self._transformResizeHandleIndex == 7:
            newRect.setBottomRight(self.SnapPoint(newRect.bottomRight() + resizeDelta))
        elif self._transformResizeHandleIndex == 1:
            newRect.setTop(self.Snap(newRect.top() + resizeDelta.y(), self.gridSpacing.height()))
        elif self._transformResizeHandleIndex == 6:
            newRect.setBottom(
                self.Snap(newRect.bottom() + resizeDelta.y(), self.gridSpacing.height()))
        elif self._transformResizeHandleIndex == 3:
            newRect.setLeft(self.Snap(newRect.left() + resizeDelta.x(), self.gridSpacing.width()))
        elif self._transformResizeHandleIndex == 4:
            newRect.setRight(self.Snap(newRect.right() + resizeDelta.x(), self.gridSpacing.width()))
        newRect = newRect.normalized()

        def Transform(p: QPointF):
            return QPointF(
                ((p.x() - initialRect.x()) / initialRect.width()) * newRect.width() + newRect.x(),
                ((p.y() - initialRect.y()) / initialRect.height()) * newRect.height() + newRect.y())

        for (r, i) in zip(self._transformStartRects, self.selectedItems):
            if i.isResizable:
                i.SetRect(QRectF(Transform(r.topLeft()), Transform(r.bottomRight())))

        self.UpdateSelectionBox()

    def AddItems(self, items: List[CustomGraphicsViewItem]):
        self.allItems += items
        z = self.GetMaxItemZValue()
        for i in items:
            self.scene().addItem(i.borderRectItem)
            self.scene().addItem(i.inspectorProxy)
            self.scene().addItem(i.itemProxy)
            i.SetEnabled(not self.isInteractive)
            i.itemProxy.setZValue(z + 1)
            i.borderRectItem.setZValue(z + 2)
            i.UpdateGeometry()
            if i.inspectorProxy is not None:
                i.inspectorProxy.setVisible(False)
            z += 2

    def CenterItem(self, item: CustomGraphicsViewItem):
        r = item.GetRect()
        r.moveCenter(self.viewOffset)
        r.moveTopLeft(self.SnapPoint(r.topLeft()))
        item.SetRect(r)

    def DeleteItems(self, items: List[CustomGraphicsViewItem]):
        for i in items:
            self.allItems.remove(i)
            self.scene().removeItem(i.borderRectItem)
            self.scene().removeItem(i.itemProxy)
            self.scene().removeItem(i.inspectorProxy)
            i.OnRemoved()
        self.SelectItems([i for i in self.selectedItems if i not in items])

    def GetMaxItemZValue(self):
        return max([x.borderRectItem.zValue() for x in self.allItems]) if len(
            self.allItems) > 0 else 0

    def SetInteractive(self, interactive: bool):
        self.isInteractive = interactive
        self.showGrid = interactive
        self.SelectItems([])
        for item in self.allItems:
            item.SetEnabled(not interactive)
        self.scene().update()

    def SelectItems(self, items: List[CustomGraphicsViewItem]):
        self.scene().clearFocus()
        self.selectedItems = items
        self.UpdateSelectionDisplay()
        self.UpdateInspectors()
        self.UpdateCursor()

    def GetPixelSceneSize(self, size):
        return self.mapToScene(QRect(0, 0, size, 1)).boundingRect().width()

    def UpdateSelectionDisplay(self):
        selectedItemBorderSceneSize = self.GetPixelSceneSize(self.selectedItemBorderSize)
        hoverItemBorderSceneSize = self.GetPixelSceneSize(self.hoverItemBorderSize)
        itemsInRect = [x for x in self.allItems if x.itemProxy.sceneBoundingRect().intersects(
            self.rubberBandRectItem.sceneBoundingRect()) or x.borderRectItem.contains(
            self.mouseScenePosition)]

        for item in self.allItems:
            isSelected = item in self.selectedItems
            isHovered = item in itemsInRect if self.state == CustomGraphicsViewState.BAND_SELECTING else item == self.itemUnderMouse
            item.borderRectItem.setVisible(isSelected or isHovered)
            if not isSelected and isHovered:
                item.borderRectItem.setPen(
                    QPen(self.hoverItemBorderColor, hoverItemBorderSceneSize))
            else:
                item.borderRectItem.setPen(
                    QPen(self.selectedItemBorderColor, selectedItemBorderSceneSize))
        self.UpdateSelectionBox()

    def UpdateInspectors(self):
        maxZValue = self.GetMaxItemZValue()
        for i in self.allItems:
            if i.inspectorProxy is None:
                continue
            if self.isInteractive and i in self.selectedItems and self.state in \
                    [CustomGraphicsViewState.IDLE, CustomGraphicsViewState.PANNING]:
                i.inspectorProxy.setVisible(True)
                i.inspectorProxy.setScale(1 / self.zoom)
                i.inspectorProxy.setZValue(maxZValue + 3)
                i.UpdateGeometry()
            else:
                i.inspectorProxy.setVisible(False)

    def UpdateSelectionBox(self):
        selectionRect = None if len(self.selectedItems) == 0 else \
            reduce(QRectF.united, [item.GetRect() for item in self.selectedItems])
        selectedItemBorderSceneSize = self.GetPixelSceneSize(self.selectedItemBorderSize)
        if selectionRect is not None:
            maxZValue = self.GetMaxItemZValue()

            selectionRect = selectionRect.marginsAdded(QMarginsF(selectedItemBorderSceneSize,
                                                                 selectedItemBorderSceneSize,
                                                                 selectedItemBorderSceneSize,
                                                                 selectedItemBorderSceneSize))
            self.selectionBoxRectItem.setVisible(True)
            self.selectionBoxRectItem.setRect(selectionRect)
            self.selectionBoxRectItem.setZValue(maxZValue + 1)
            self.selectionBoxRectItem.setPen(
                QPen(self.selectionBoxRectColor,
                     self.mapToScene(
                         QRect(0, 0, self.selectionBoxRectScreenSize, 1)).boundingRect().width(),
                     j=Qt.MiterJoin))

            if all([not x.isResizable for x in self.selectedItems]):
                [h.setVisible(False) for h in self.resizeHandles]
            else:
                handlePositions = (
                    selectionRect.topLeft(),
                    QPointF(selectionRect.center().x(), selectionRect.top()),
                    selectionRect.topRight(),
                    QPointF(selectionRect.left(), selectionRect.center().y()),
                    QPointF(selectionRect.right(), selectionRect.center().y()),
                    selectionRect.bottomLeft(),
                    QPointF(selectionRect.center().x(), selectionRect.bottom()),
                    selectionRect.bottomRight())
                handleSize = self.GetPixelSceneSize(self.resizeHandleScreenSize)
                for pos, h in zip(handlePositions, self.resizeHandles):
                    h.setVisible(True)
                    h.setPen(QPen(self.resizeHandleBorderColor,
                                  self.GetPixelSceneSize(self.resizeHandleBorderScreenSize),
                                  j=Qt.MiterJoin))
                    h.setBrush(QBrush(self.resizeHandleColor))
                    h.setZValue(maxZValue + 2)
                    r = QRectF(QPointF(), QSizeF(handleSize, handleSize))
                    r.moveCenter(pos)
                    h.setRect(r)
        else:
            self.selectionBoxRectItem.setVisible(False)
            [h.setVisible(False) for h in self.resizeHandles]

        rubberBandWidth = self.GetPixelSceneSize(self.rubberBandRectScreenSize)
        self.rubberBandRectItem.setZValue(self.GetMaxItemZValue() + 2)
        self.rubberBandRectItem.setPen(QPen(self.rubberBandRectColor, rubberBandWidth))

    def DoBandSelect(self):
        itemsInRect = [x for x in self.allItems if x.itemProxy.sceneBoundingRect().intersects(
            self.rubberBandRectItem.sceneBoundingRect()) or x.borderRectItem.contains(
            self.mouseScenePosition)]
        if self.IsMultiSelect():
            self.SelectItems(
                [x for x in self.selectedItems if x not in itemsInRect] +
                [x for x in itemsInRect if x not in self.selectedItems])
        else:
            self.SelectItems(itemsInRect)

    @staticmethod
    def IsMultiSelect():
        return QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier

    def Duplicate(self):
        duplicates = []
        for i in self.selectedItems:
            d = i.Duplicate()
            d.SetRect(
                i.GetRect().translated(
                    QPointF(self.gridSpacing.width(), self.gridSpacing.height())))
            duplicates.append(d)
        self.AddItems(duplicates)
        self.SelectItems(duplicates)

    # Events
    def wheelEvent(self, event):
        if self.WidgetUnderMouseAlwaysInteractable():
            super().wheelEvent(event)
            return
        self.UpdateMouseInfo(event.position().toPoint())
        self.UpdateZoom(self.mouseScenePosition,
                        self.zoom + float(event.angleDelta().y()) * self.scrollSensitivity)
        event.accept()

    def keyPressEvent(self, event):
        if self.isInteractive and len(self.selectedItems) > 0 and self.scene().focusItem() is None:
            if event.key() == Qt.Key_Delete:
                self.DeleteItems(self.selectedItems)
            elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
                self.Duplicate()
            elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_A:
                self.SelectItems(self.allItems)
            else:
                super().keyPressEvent(event)
                return
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.UpdateMouseInfo(event.pos())
        if self.IsWindowFocused():
            super().mousePressEvent(event)
            return
        if self.state != CustomGraphicsViewState.IDLE:
            pass
        elif event.button() == Qt.RightButton:
            self.state = CustomGraphicsViewState.PANNING
        elif event.button() == Qt.LeftButton:
            if not self.isInteractive or self.isInspectorUnderMouse:
                super().mousePressEvent(event)
                return
            if self.resizeHandleIndexUnderMouse >= 0:
                self._transformResizeHandleIndex = self.resizeHandleIndexUnderMouse
                self._transformStartRects = [x.itemProxy.sceneBoundingRect() for x in
                                             self.selectedItems]
                self._transformStartMousePos = self.mouseScenePosition
                self.state = CustomGraphicsViewState.RESIZING
            elif self.itemUnderMouse is not None:
                if self.WidgetUnderMouseAlwaysInteractable():
                    super().mousePressEvent(event)
                    return
                if self.IsMultiSelect():
                    if self.itemUnderMouse in self.selectedItems:
                        self.selectedItems.remove(self.itemUnderMouse)
                    else:
                        self.selectedItems.append(self.itemUnderMouse)
                    self.SelectItems(self.selectedItems)
                else:
                    if self.itemUnderMouse not in self.selectedItems:
                        self.SelectItems([self.itemUnderMouse])
                    self.state = CustomGraphicsViewState.MOVING
                    self._transformStartRects = [x.itemProxy.sceneBoundingRect() for x in
                                                 self.selectedItems]
                    self._transformStartMousePos = self.mouseScenePosition
            else:
                self.rubberBandAnchor = self.mouseScenePosition
                self.rubberBandRectItem.setRect(QRectF(self.mouseScenePosition, QSizeF()))
                self.state = CustomGraphicsViewState.BAND_SELECTING
                self.rubberBandRectItem.setVisible(True)

        event.accept()
        self.UpdateCursor()
        self.UpdateInspectors()

    def mouseReleaseEvent(self, event):
        self.UpdateMouseInfo(event.pos())

        if self.IsWindowFocused():
            super().mouseReleaseEvent(event)
            return
        if self.state == CustomGraphicsViewState.PANNING and event.button() == Qt.RightButton:
            self.state = CustomGraphicsViewState.IDLE
        elif self.state == CustomGraphicsViewState.MOVING and event.button() == Qt.LeftButton:
            self.state = CustomGraphicsViewState.IDLE
        elif self.state == CustomGraphicsViewState.RESIZING and event.button() == Qt.LeftButton:
            self.state = CustomGraphicsViewState.IDLE
        elif self.state == CustomGraphicsViewState.BAND_SELECTING and event.button() == Qt.LeftButton:
            self.state = CustomGraphicsViewState.IDLE
            self.rubberBandRectItem.setVisible(False)
            self.DoBandSelect()
        elif event.button() == Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return
        event.accept()
        self.UpdateCursor()
        self.UpdateInspectors()

    def mouseMoveEvent(self, event):
        self.UpdateMouseInfo(event.pos())
        if self.IsWindowFocused():
            super().mouseMoveEvent(event)
            return
        if self.state == CustomGraphicsViewState.PANNING:
            self.viewOffset -= self.mouseDeltaScenePosition
            self.UpdateViewMatrix()
            event.accept()
        elif self.state == CustomGraphicsViewState.MOVING:
            self.DoMove()
            self.scene().update()
            event.accept()
        elif self.state == CustomGraphicsViewState.RESIZING:
            self.DoResize()
            self.scene().update()
            event.accept()
        elif self.state == CustomGraphicsViewState.BAND_SELECTING:
            self.rubberBandRectItem.setRect(
                QRectF(self.rubberBandAnchor, self.mouseScenePosition).normalized())
            self.scene().update()
            event.accept()
        else:
            super().mouseMoveEvent(event)
        self.UpdateCursor()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        if self.backgroundBrush().color() != self.palette().color(QPalette.Light):
            self.setBackgroundBrush(self.palette().color(QPalette.Light))
        super().drawBackground(painter, rect)

        if self.zoom <= self.gridZoomThreshold or not self.showGrid:
            return

        painter.setPen(QPen(self.palette().color(QPalette.Midlight), self.gridThickness))

        lines = []
        if self.gridSpacing.width() > 0:
            xStart = rect.left() - rect.left() % self.gridSpacing.width()
            while xStart <= rect.right():
                line = QLineF(xStart, rect.bottom(), xStart, rect.top())
                lines.append(line)
                xStart = xStart + self.gridSpacing.width()

        if self.gridSpacing.height() > 0:
            yStart = rect.top() - rect.top() % self.gridSpacing.height()
            while yStart <= rect.bottom():
                line = QLineF(rect.left(), yStart, rect.right(), yStart)
                lines.append(line)
                yStart = yStart + self.gridSpacing.height()

        painter.drawLines(lines)
