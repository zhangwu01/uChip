import pathlib
import typing

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QToolButton, QSizePolicy, QFrame
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import QPoint, Qt, QSize, QRectF

from UI.CustomGraphicsView import CustomGraphicsView
from UI.ChipViewItems import ValveItem, ImageItem, TextItem, ProgramItem
from UI.ScriptBrowser import ScriptBrowser
from UI.UIMaster import UIMaster
from Data.Chip import Valve, Image, Text, Program, Script


class ChipView(QWidget):
    def __init__(self):
        super().__init__()
        self.graphicsView = CustomGraphicsView()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.layout().addWidget(self.graphicsView)

        self.toolPanel = QWidget(self)
        self.finishEditsButton = ToolButton("Finish editing",
                                            "",
                                            "Assets/Images/checkIcon.png",
                                            lambda: self.SetEditing(False),
                                            size=(70, 70),
                                            icon_size=(40, 40))

        self.editButton = ToolButton("Edit chip",
                                     "",
                                     "Assets/Images/Edit.png",
                                     lambda: self.SetEditing(True),
                                     size=(70, 70),
                                     icon_size=(40, 40))

        self.addValveButton = ToolButton("Add valve",
                                         "Valve",
                                         "Assets/Images/ValveIcon.png",
                                         self.AddNewValve)

        self.addTextButton = ToolButton("Add text",
                                        "Text",
                                        "Assets/Images/TextIcon.png",
                                        self.AddNewText)

        self.addImageButton = ToolButton("Add image",
                                         "Image",
                                         "Assets/Images/imageIcon.png",
                                         self.AddNewImage)

        self.addProgramButton = ToolButton("Add program",
                                           "Program",
                                           "Assets/Images/CodeIcon.png",
                                           self.ShowProgramBrowser)

        toolPanelLayout = QVBoxLayout()
        toolPanelLayout.setContentsMargins(0, 0, 0, 0)
        toolPanelLayout.setSpacing(0)
        self.toolPanel.setLayout(toolPanelLayout)

        toolPanelLayout.addWidget(self.finishEditsButton, alignment=Qt.AlignHCenter)
        toolPanelLayout.addWidget(self.editButton)

        self.toolOptions = QWidget()
        self.toolOptions.setAutoFillBackground(True)
        toolOptionsLayout = QVBoxLayout()
        toolOptionsLayout.setContentsMargins(0, 5, 0, 5)
        toolOptionsLayout.setSpacing(5)
        toolOptionsLayout.addWidget(self.addValveButton, alignment=Qt.AlignHCenter)
        toolOptionsLayout.addWidget(self.addImageButton, alignment=Qt.AlignHCenter)
        toolOptionsLayout.addWidget(self.addTextButton, alignment=Qt.AlignHCenter)
        toolOptionsLayout.addWidget(self.addProgramButton, alignment=Qt.AlignHCenter)
        self.toolOptions.setLayout(toolOptionsLayout)
        toolPanelLayout.addWidget(self.toolOptions)

        self.scriptBrowser = ScriptBrowser(self)

        self.SetEditing(True)

    def resizeEvent(self, event):
        self.UpdateToolPanelPosition()
        super().resizeEvent(event)

    def UpdateToolPanelPosition(self):
        r = self.rect()

        padding = 20
        self.toolPanel.adjustSize()
        self.toolPanel.move(r.topLeft() + QPoint(padding, padding))

    def SetEditing(self, isEditing: bool):
        self.graphicsView.SetInteractive(isEditing)
        self.editButton.setVisible(not isEditing)
        self.finishEditsButton.setVisible(isEditing)
        self.toolOptions.setVisible(isEditing)

        self.UpdateToolPanelPosition()

    def AddNewValve(self):
        highestValveNumber = max(
            [x.solenoidNumber for x in UIMaster.Instance().currentChip.valves] + [-1])
        newValve = Valve()
        newValve.name = "Valve " + str(highestValveNumber + 1)
        newValve.solenoidNumber = highestValveNumber + 1
        UIMaster.Instance().currentChip.valves.append(newValve)
        newValveItem = ValveItem.ValveItem(newValve)
        self.graphicsView.AddItems([newValveItem])
        self.graphicsView.CenterItem(newValveItem)
        self.graphicsView.SelectItems([newValveItem])

    def AddNewImage(self):
        path = ImageItem.ImageItem.Browse(self)
        if path:
            newImage = Image()
            newImage.path = path
            UIMaster.Instance().currentChip.images.append(newImage)
            newImageItem = ImageItem.ImageItem(newImage)
            newImageItem.SetRect(
                QRectF(newImageItem.GetRect().topLeft(),
                       QSize(newImageItem.qtImage.size())))
            self.graphicsView.AddItems([newImageItem])
            self.graphicsView.CenterItem(newImageItem)
            self.graphicsView.SelectItems([newImageItem])

    def AddNewText(self):
        newText = Text()
        newText.text = "New text"
        UIMaster.Instance().currentChip.text.append(newText)
        newTextItem = TextItem.TextItem(newText)
        self.graphicsView.AddItems([newTextItem])
        self.graphicsView.CenterItem(newTextItem)
        self.graphicsView.SelectItems([newTextItem])

    def AddProgram(self, script: Script):
        newProgram = Program(script)
        newProgram.name = script.Name()
        UIMaster.Instance().currentChip.programs.append(newProgram)
        newProgramItem = ProgramItem.ProgramItem(newProgram)
        self.graphicsView.AddItems([newProgramItem])
        self.graphicsView.CenterItem(newProgramItem)
        self.graphicsView.SelectItems([newProgramItem])

    def ShowProgramBrowser(self):
        ScriptBrowser.Instance().Show(self.AddProgram)

    def CloseChip(self):
        self.graphicsView.Clear()

    def OpenChip(self):
        imageItems = [ImageItem.ImageItem(image) for image in
                      UIMaster.Instance().currentChip.images]
        self.graphicsView.AddItems(imageItems)

        valveItems = [ValveItem.ValveItem(valve) for valve in
                      UIMaster.Instance().currentChip.valves]
        self.graphicsView.AddItems(valveItems)

        textItems = [TextItem.TextItem(text) for text in UIMaster.Instance().currentChip.text]
        self.graphicsView.AddItems(textItems)

        programItems = [ProgramItem.ProgramItem(program) for program in
                        UIMaster.Instance().currentChip.programs]
        self.graphicsView.AddItems(programItems)

        self.graphicsView.ZoomBounds()


class ToolButton(QToolButton):
    def __init__(self, tooltip: str, label: str, icon_path: str, delegate: typing.Callable, size=(60, 50),
                 icon_size=(20, 20)):
        super().__init__()

        self.icon_path = icon_path
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip(tooltip)
        self.setText(label)
        self.SetColor(100, 100, 100)
        self.setFixedSize(*size)
        if label != "":
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(*icon_size))
        self.clicked.connect(delegate)

    def SetColor(self, *color):
        self.setIcon(ColoredIcon(self.icon_path, QColor(*color)))


class ColoredIcon(QIcon):
    def __init__(self, filename, color: QColor):
        pixmap = QPixmap(filename)
        replaced = QPixmap(pixmap.size())
        replaced.fill(color)
        replaced.setMask(pixmap.createMaskFromColor(Qt.transparent))
        super().__init__(replaced)
