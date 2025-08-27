import pathlib

import PySide6
import typing
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QMenuBar, QFileDialog, \
    QMessageBox, QHBoxLayout, QPushButton, QSizePolicy, QProxyStyle, QStyle
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence
from UI.ChipView import ChipView
from UI.RigView import RigView
from UI.UIMaster import UIMaster
from UI.ProgramWorker import ProgramWorker
from UI.USBWorker import USBWorker
from Data.FileIO import SaveObject, LoadObject
from Data.Chip import Chip, Script
from UI.ScriptEditor import ScriptEditor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.chipEditor = ChipView()
        centralWidget = QWidget()
        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
        centralWidget.setLayout(l)
        self.setCentralWidget(centralWidget)
        self.setWindowIcon(QIcon("Assets/Images/icon.png"))
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.TabPosition.North)

        self.resize(1600, 900)

        self.rigView = RigView()
        self.dockPositions = {self.rigView: Qt.RightDockWidgetArea}

        self.BuildMenu()

        self.toggleButton = QPushButton()
        self.toggleButton.clicked.connect(self.ToggleRig)
        self.toggleButton.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.toggleButton.setStyleSheet("""
        QPushButton {
        background-color: rgba(0, 0, 0, 0.1);
        padding: 5px;
        font-weight: bold;
        }
        QPushButton:hover {
        background-color: rgba(0, 0, 0, 0.2);
        }
        """)
        l.addWidget(self.chipEditor, stretch=1)
        l.addWidget(self.toggleButton)
        l.addWidget(self.rigView, stretch=0)

        self.programWorker = ProgramWorker(5.0)
        self.usbWorker = USBWorker()
        watchdogTimer = QTimer(self)
        watchdogTimer.timeout.connect(self.CheckForTimeout)
        watchdogTimer.start(1000)

        self.NewChip()
        self.ToggleRig()
        self.ToggleRig()

        self.scriptEditors: typing.List[ScriptEditor] = []
        self.chipEditor.scriptBrowser.onEditScript = self.OpenScriptEditor

        self.setStyleSheet(UIMaster.StyleSheet())

        self.show()


    def OpenScriptEditor(self, script: typing.Optional[Script]):
        self.scriptEditors = [e for e in self.scriptEditors if e is not None and e.isVisible()]
        if script is None:
            self.scriptEditors.append(ScriptEditor(None, self.OnScriptSaved))
            return

        for editor in self.scriptEditors:
            if editor.script == script:
                editor.activateWindow()
                editor.raise_()
                return

        self.scriptEditors.append(ScriptEditor(script, self.OnScriptSaved))

    def OnScriptSaved(self, script: Script):
        self.chipEditor.scriptBrowser.RelistAndSelect(script)

    def ToggleRig(self):
        self.rigView.setHidden(not self.rigView.isHidden())
        self.toggleButton.setText("<" if self.rigView.isHidden() else ">")

    def CheckForTimeout(self):
        if self.programWorker.IsStuck():
            QMessageBox.critical(self, "Stuck",
                                 "Function %s in program %s has blocked the update thread for "
                                 ">5 seconds. Ensure that this script does not have a long-running "
                                 "or infinite loop. Programs may not run until uChip is restarted."
                                 % (self.programWorker.tickStartFunctionSymbol,
                                    self.programWorker.tickStartProgram.program.name))

    def NewChip(self):
        if not self.PromptCloseChip():
            return
        self.chipEditor.CloseChip()
        UIMaster.Instance().currentChip = Chip()
        self.chipEditor.OpenChip()
        UIMaster.Instance().modified = False
        self.SetWindowTitle()

    def SaveChip(self, saveAs: bool):
        if saveAs or UIMaster.Instance().currentChipPath is None:
            d = QFileDialog.getSaveFileName(self, "Save Path", filter="uChip Project (*.ucp)")
            if d[0]:
                UIMaster.Instance().currentChipPath = pathlib.Path(d[0])
            else:
                return False
        UIMaster.Instance().currentChip.ConvertPathsToRelative(UIMaster.Instance().currentChipPath)
        SaveObject(UIMaster.Instance().currentChip, UIMaster.Instance().currentChipPath)
        UIMaster.Instance().currentChip.ConvertPathsToAbsolute(UIMaster.Instance().currentChipPath)
        UIMaster.Instance().modified = False
        self.SetWindowTitle()
        return True

    def OpenChip(self):
        if not self.PromptCloseChip():
            return
        d = QFileDialog.getOpenFileName(self, "Open Chip", filter="uChip Project (*.ucp)")
        if d[0]:
            self.OpenChipPath(d[0])
        else:
            return

    def OpenChipPath(self, path):
        self.chipEditor.CloseChip()
        UIMaster.Instance().currentChipPath = pathlib.Path(path)
        UIMaster.Instance().currentChip = LoadObject(UIMaster.Instance().currentChipPath)
        UIMaster.Instance().currentChip.ConvertPathsToAbsolute(UIMaster.Instance().currentChipPath)
        self.chipEditor.OpenChip()
        UIMaster.Instance().modified = False
        self.SetWindowTitle()

    def PromptCloseChip(self):
        if UIMaster.Instance().modified:
            value = QMessageBox.critical(self, "Confirm Action",
                                         "This uChip project has been modified. Do you want to discard changes?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                         QMessageBox.StandardButton.Cancel)
            if value == QMessageBox.StandardButton.Cancel:
                return False
            elif value == QMessageBox.StandardButton.Save:
                return self.SaveChip(False)
        return True

    def SetWindowTitle(self):
        chipName = "New Chip" if UIMaster.Instance().currentChipPath is None else UIMaster.Instance().currentChipPath.stem
        self.setWindowTitle("µChip - " + chipName)

    def closeEvent(self, event):
        if self.PromptCloseChip():
            super().closeEvent(event)
            self.programWorker.doStop = True
            self.usbWorker.doStop = True
            self.programWorker.thread.join()
            self.usbWorker.thread.join()
            for v in self.scriptEditors:
                if v is not None:
                    v.close()
            UIMaster.Shutdown()
        else:
            event.ignore()

    def BuildMenu(self):
        menuBar = QMenuBar()

        fileMenu = menuBar.addMenu("&File")
        newAction = fileMenu.addAction("New")
        newAction.triggered.connect(self.NewChip)
        newAction.setShortcut(QKeySequence("Ctrl+N"))
        openAction = fileMenu.addAction("Open...")
        openAction.setShortcut(QKeySequence("Ctrl+O"))
        openAction.triggered.connect(self.OpenChip)

        saveAction = fileMenu.addAction("Save")
        saveAction.setShortcut(QKeySequence("Ctrl+S"))
        saveAction.triggered.connect(lambda: self.SaveChip(False))

        saveAsAction = fileMenu.addAction("Save As...")
        saveAsAction.setShortcut(QKeySequence("Ctrl+Shift+S"))
        saveAsAction.triggered.connect(lambda: self.SaveChip(True))

        exitAction = fileMenu.addAction("Exit")
        exitAction.triggered.connect(self.close)

        selectMenu = menuBar.addMenu("&Select")
        selectAllAction = selectMenu.addAction("All")
        selectAllAction.triggered.connect(lambda: self.chipEditor.graphicsView.SelectAll())
        selectAllAction.setShortcut(QKeySequence("Ctrl+A"))
        selectNoneAction = selectMenu.addAction("None")
        selectNoneAction.triggered.connect(lambda: self.chipEditor.graphicsView.SelectItems([]))
        selectNoneAction.setShortcut(QKeySequence("Esc"))

        viewMenu = menuBar.addMenu("&View")
        centerOnSelected = viewMenu.addAction("Center On Selection")
        centerOnSelected.triggered.connect(lambda: self.chipEditor.graphicsView.CenterOnSelection())

        self.setMenuBar(menuBar)
