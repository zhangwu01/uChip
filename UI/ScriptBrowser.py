from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QFileDialog, \
    QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt, QPoint
from Data.Chip import Script
from UI.PythonEditor import PythonEditor
from UI.UIMaster import UIMaster

import pathlib


class ScriptBrowser(QDialog):
    _instance: 'ScriptBrowser' = None

    def __init__(self, parent):
        super().__init__(parent)
        self.onScriptChosen = None
        self.setWindowTitle("Script Browser")

        self.setModal(False)
        self.previewPath = QLabel("")
        self.previewWindow = PythonEditor()
        self.previewWindow.setMinimumWidth(500)
        self.previewWindow.setReadOnly(True)
        self.editScriptButton = QPushButton("Edit Script...")
        self.editScriptButton.clicked.connect(self.EditScript)

        self.scriptList = QListWidget()
        self.scriptList.currentRowChanged.connect(self.SelectionChanged)
        self.scriptList.itemDoubleClicked.connect(self.DoubleClicked)

        self.chooseButton = QPushButton("Choose")
        self.chooseButton.clicked.connect(self.DoChoice)

        self.chooseButton.setProperty("MainButton", True)
        self.newButton = QPushButton("New Script...")
        self.newButton.clicked.connect(self.NewScript)
        self.importButton = QPushButton("Import...")
        self.importButton.clicked.connect(self.ImportScript)
        self.removeButton = QPushButton("Remove")
        self.removeButton.clicked.connect(self.RemoveScript)
        self.relocateButton = QPushButton(parent=self.previewWindow, text="Relocate...")
        self.relocateButton.clicked.connect(self.RefindScript)

        previewLayout = QVBoxLayout()
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.previewPath, stretch=0)
        topLayout.addStretch(1)
        topLayout.addWidget(self.editScriptButton, stretch=0)
        previewLayout.addLayout(topLayout)
        previewLayout.addWidget(self.previewWindow)

        listLayout = QVBoxLayout()
        listLayout.addWidget(self.scriptList)
        listLayout.addWidget(self.chooseButton)
        listLayout.addWidget(self.newButton)
        listLayout.addWidget(self.importButton)
        listLayout.addWidget(self.removeButton)

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(listLayout, stretch=0)
        mainLayout.addLayout(previewLayout, stretch=1)

        self.setLayout(mainLayout)
        self.onEditScript = lambda x: None

        if ScriptBrowser._instance is None:
            ScriptBrowser._instance = self

    def resizeEvent(self, arg__1) -> None:
        r = self.previewWindow.rect()
        b = self.relocateButton.rect()
        p = r.center() - QPoint(b.width() / 2, b.height() / 2)
        self.relocateButton.move(p)
        super().resizeEvent(arg__1)

    def Relist(self):
        self.scriptList.blockSignals(True)
        self.scriptList.clear()
        self.scriptList.addItems(
            [("[built-in]  " if script.isBuiltIn else "") + script.Name() for script in ScriptBrowser.Scripts()])
        self.scriptList.blockSignals(False)
        self.scriptList.setCurrentRow(0)

    def RemoveScript(self):
        UIMaster.Instance().currentChip.scripts.remove(self.SelectedScript())
        self.Relist()

    def NewScript(self):
        self.onEditScript(None)

    def EditScript(self):
        self.onEditScript(self.SelectedScript())

    def RelistAndSelect(self, script: Script):
        self.Relist()
        self.SelectScript(script)

    @staticmethod
    def Scripts():
        ls = UIMaster.Instance().currentChip.scripts
        bis = sorted([l for l in ls if l.isBuiltIn], key=lambda x: x.Name())
        nBis = sorted([l for l in ls if not l.isBuiltIn], key=lambda x: x.Name())
        return bis + nBis

    def DoubleClicked(self, i: QListWidgetItem):
        self.scriptList.setCurrentRow(self.scriptList.row(i))
        self.DoChoice()

    def SelectedScript(self):
        return ScriptBrowser.Scripts()[self.scriptList.currentRow()]

    def SelectionChanged(self):
        self.relocateButton.hide()
        if self.SelectedScript().isBuiltIn:
            self.previewPath.setText(self.SelectedScript().Name() + " <i>[built-in]</i>")
            self.removeButton.setEnabled(False)
            self.removeButton.setToolTip("Cannot remove built-in script.")
            self.editScriptButton.setEnabled(False)
        else:
            if not self.SelectedScript().path.exists():
                self.relocateButton.show()
                self.previewPath.setText("Cannot find path " + str(self.SelectedScript().path.absolute()))
                self.editScriptButton.setEnabled(False)
            else:
                self.previewPath.setText(str(self.SelectedScript().path.absolute()))
                self.editScriptButton.setEnabled(True)

            # Remove button.
            if self.SelectedScript() in [program.script for program in UIMaster.Instance().currentChip.programs]:
                self.removeButton.setToolTip("Cannot remove a script in use by the current project.")
                self.removeButton.setEnabled(False)
            else:
                self.removeButton.setEnabled(True)
                self.removeButton.setToolTip("")

        s = self.SelectedScript()
        if s is None or (not s.isBuiltIn and not s.path.exists()):
            self.previewWindow.setPlainText("")
        else:
            self.previewWindow.setPlainText(self.SelectedScript().Read())

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.DoChoice()

    def DoChoice(self):
        self.onScriptChosen(self.SelectedScript())
        self.hide()

    def SelectScript(self, script: Script):
        if script not in ScriptBrowser.Scripts():
            return
        self.scriptList.setCurrentRow(ScriptBrowser.Scripts().index(script))

    def RefindScript(self):
        s = self.BrowseForScript()
        if s is None:
            return
        if s in UIMaster.Instance().currentChip.scripts:
            QMessageBox.critical(self, "Could not add script",
                                 "The script '" + str(s.path.absolute()) + "' is already used in this project.")
        else:
            self.SelectedScript().path = s.path
        self.Relist()
        self.SelectScript(s)

    def BrowseForScript(self):
        scriptPath = QFileDialog.getOpenFileName(self, "Browse for script",
                                                 filter="uChip script (*.py)")
        if scriptPath[0]:
            path = pathlib.Path(scriptPath[0])
            for i, existingScript in enumerate(UIMaster.Instance().currentChip.scripts):
                if not existingScript.isBuiltIn and existingScript.path == path:
                    return existingScript
            return Script(path)

    def ImportScript(self):
        s = self.BrowseForScript()
        if s is None:
            return
        if s not in UIMaster.Instance().currentChip.scripts:
            UIMaster.Instance().currentChip.scripts.append(s)
        self.Relist()
        self.SelectScript(s)

    def Show(self, onScriptChosen, selectedScript: Script = None):
        self.onScriptChosen = onScriptChosen
        self.Relist()
        if selectedScript:
            self.SelectScript(selectedScript)
        self.show()

    @staticmethod
    def Instance():
        return ScriptBrowser._instance
