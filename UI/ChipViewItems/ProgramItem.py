import traceback
import typing
import pathlib
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFormLayout, QLineEdit, \
    QSpinBox, QDoubleSpinBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QScrollArea, QFrame, QSizePolicy, \
    QCheckBox
from PySide6.QtCore import QRectF, Signal, Qt
from PySide6.QtGui import QIcon, QColor, QPixmap

import ucscript
from UI.UIMaster import UIMaster
from UI.CustomGraphicsView import CustomGraphicsViewItem
from UI.ScriptBrowser import ScriptBrowser
from Data.Chip import Program, Script
from Data.ProgramCompilation import IsTypeValidList, IsTypeValidOptions, DoTypesMatch, \
    NoneValueForType, Message


class ColoredIcon(QIcon):
    def __init__(self, filename, color: QColor):
        pixmap = QPixmap(filename)
        replaced = QPixmap(pixmap.size())
        replaced.fill(color)
        replaced.setMask(pixmap.createMaskFromColor(Qt.transparent))
        super().__init__(replaced)


# The most complicated/involved chip item. Lots of components!
class ProgramItem(CustomGraphicsViewItem):
    def __init__(self, program: Program):

        self.shownIcon = ColoredIcon("Assets/Images/Visible.png", QColor(100, 100, 100))
        self.hiddenIcon = ColoredIcon("Assets/Images/Hidden.png", QColor(150, 150, 150))

        self.program = program

        # Set up the inspector for this item:
        inspectorWidget = QWidget()
        inspectorWidget.setStyleSheet("""
        QLabel {
        padding: 5px;
        }""")
        inspectorWidgetLayout = QVBoxLayout()
        inspectorWidgetLayout.setContentsMargins(0, 0, 0, 0)
        inspectorWidgetLayout.setSpacing(0)
        inspectorWidget.setLayout(inspectorWidgetLayout)

        # Program name field
        nameAndSourceLayout = QFormLayout()
        nameAndSourceLayout.setContentsMargins(1, 1, 1, 1)
        nameAndSourceLayout.setSpacing(0)
        inspectorWidget.layout().addLayout(nameAndSourceLayout)
        self.nameField = QLineEdit()
        self.nameField.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        self.nameField.textChanged.connect(self.RecordChanges)
        nameAndSourceLayout.addRow("Name", self.nameField)

        # Program source field with browse button.
        self.scriptNameWidget = QLabel()
        self.selectScriptButton = QPushButton("...")
        self.selectScriptButton.setFixedWidth(50)
        self.selectScriptButton.clicked.connect(self.SelectScript)
        sourceLayout = QHBoxLayout()
        sourceLayout.addWidget(self.scriptNameWidget, stretch=1)
        sourceLayout.addWidget(self.selectScriptButton, stretch=0)
        nameAndSourceLayout.addRow("Source", sourceLayout)

        # Program scale field
        self.scaleWidget = QDoubleSpinBox()
        self.scaleWidget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        self.scaleWidget.setMinimum(0.1)
        self.scaleWidget.setMaximum(10.0)
        self.scaleWidget.setSingleStep(0.1)
        self.scaleWidget.valueChanged.connect(self.RecordChanges)
        nameAndSourceLayout.addRow("Display scale", self.scaleWidget)

        #Hide messages field
        self.hideMessages = QComboBox()
        self.hideMessages.addItems(["Show", "Hide"])
        self.hideMessages.currentIndexChanged.connect(self.RecordChanges)
        nameAndSourceLayout.addRow("Log", self.hideMessages)

        dummyWidget = QWidget()
        inspectorWidget.layout().addWidget(dummyWidget)
        dummyWidget.setFixedHeight(5)
        dummyWidget.setStyleSheet("""background-color: black;""")

        # Parameters will be kept in this layout for the inspector. All parameters are shown here.
        self.parametersLayout = QGridLayout()
        self.parametersLayout.setContentsMargins(0, 0, 0, 0)
        self.parametersLayout.setSpacing(0)
        parametersWidget = QFrame()
        parametersWidget.setLineWidth(2)
        parametersWidget.setLayout(self.parametersLayout)
        inspectorWidget.layout().addWidget(parametersWidget)

        # Parameters will be kept in this layout for the item. Only visible parameters will be
        # shown.
        self.visibleParametersLayout = QGridLayout()
        self.visibleParametersLayout.setContentsMargins(0, 0, 0, 0)
        self.visibleParametersLayout.setSpacing(0)
        visibleParametersWidget = QFrame()
        visibleParametersWidget.setLineWidth(2)
        visibleParametersWidget.setLayout(self.visibleParametersLayout)
        inspectorWidget.layout().addWidget(visibleParametersWidget)

        # Functions will be kept in this layout for the item. All zero-argument functions will be
        # shown here as buttons.
        self.functionsLayout = QGridLayout()
        self.functionsLayout.setContentsMargins(0, 0, 0, 0)
        self.functionsLayout.setSpacing(0)
        functionsWidget = QWidget()
        functionsWidget.setLayout(self.functionsLayout)

        # Widget sets for each parameter.
        self.parameterWidgetSets: typing.List[ParameterWidgetSet] = []

        # Widget sets for each function
        self.functionWidgetSets: typing.List[FunctionWidgetSet] = []

        # Actual item widget
        itemWidget = ProgramItem.ResizeDelegate(self.OnResized)
        itemWidget.setObjectName("itemWidget")
        itemWidget.setStyleSheet("""
        #itemWidget {
        border: 1px solid black;
        }
        QLabel {
        padding: 5px;
        }""")
        self.nameWidget = QLabel()
        self.nameWidget.setStyleSheet("color: white; background-color: black;")
        self.nameWidget.setAlignment(Qt.AlignCenter)
        itemLayout = QVBoxLayout()
        itemLayout.setContentsMargins(0, 0, 0, 0)
        itemLayout.setSpacing(0)
        itemWidget.setLayout(itemLayout)
        itemWidget.layout().addWidget(self.nameWidget)
        itemWidget.layout().addWidget(visibleParametersWidget)

        dummyWidget = QWidget()
        itemWidget.layout().addWidget(dummyWidget)
        dummyWidget.setFixedHeight(5)
        dummyWidget.setStyleSheet("""background-color: black;""")

        itemWidget.layout().addWidget(functionsWidget)

        # Compilation/program error reporting
        self.messageArea = MessageArea()
        self.messageArea.setProperty("AlwaysInteractable", True)
        self.clearMessagesButton = QPushButton("Clear Messages")
        self.clearMessagesButton.clicked.connect(self.ClearMessages)
        self.clearMessagesButton.setProperty("AlwaysInteractable", True)
        spacerWidget = QLabel()
        spacerWidget.setStyleSheet("background-color: #999999;")
        spacerWidget.setFixedHeight(1)
        itemWidget.layout().addWidget(spacerWidget)
        itemWidget.layout().addWidget(self.messageArea)
        itemWidget.layout().addWidget(self.clearMessagesButton)

        self.fadeWidget = QWidget(itemWidget)
        self.fadeWidget.setStyleSheet("background-color: rgba(255, 255, 255, 200);")

        super().__init__("Program", itemWidget, inspectorWidget)
        super().SetRect(QRectF(*program.position, 0, 0))
        self.isResizable = False

    def OnResized(self, event):
        self.fadeWidget.move(1, 1)
        height = self.itemProxy.widget().height()
        if not self.program.hideMessages:
            height += - self.messageArea.height() - self.clearMessagesButton.height()
        self.fadeWidget.setFixedSize(self.itemProxy.widget().width() - 2, height - 2)

    class ResizeDelegate(QFrame):
        def __init__(self, delegate):
            super().__init__()
            self.delegate = delegate

        def resizeEvent(self, event) -> None:
            super().resizeEvent(event)
            self.delegate(event)

    def ClearMessages(self):
        compiled = UIMaster.GetCompiledProgram(self.program)
        compiled.messages = [m for m in compiled.messages if m.messageType == Message.ERROR_CT]

    def SetEnabled(self, state):
        for c in self.itemProxy.widget().children():
            if isinstance(c, QWidget) and c != self.messageArea and c != self.clearMessagesButton:
                c.setEnabled(state)
        self.fadeWidget.setVisible(not state)

    def SelectScript(self):
        def Selected(s: Script):
            self.program.script = s
            self.RecordChanges()

        ScriptBrowser.Instance().Show(Selected, self.program.script)

    # Called whenever the user changes the program parameters/name/visibility etc.
    def RecordChanges(self):
        if self.isUpdating:
            return

        # Store the program name and widget size.
        self.program.name = self.nameField.text()
        rect = self.GetRect()
        self.program.position = [rect.x(), rect.y()]

        # Record visibility changes
        for parameterSymbol, parameterWidgetSet in zip(self.program.parameterValues,
                                                       self.parameterWidgetSets):
            self.program.parameterVisibility[
                parameterSymbol] = parameterWidgetSet.inspectorVisibilityToggle.isChecked()

        self.program.scale = self.scaleWidget.value()
        self.program.hideMessages = self.hideMessages.currentText() == "Hide"
        UIMaster.Instance().modified = True

    def Update(self):
        # Called regularly to make sure that the fields match the backing program.
        if self.program.name != self.nameField.text():
            self.nameField.setText(self.program.name)
        if self.program.name != self.nameWidget.text():
            self.nameWidget.setText("<b>%s</b>" % self.program.name)
        if self.program.script.isBuiltIn:
            fullPath = self.program.script.Name() + " <i>[BUILTIN]</i>"
            displayPath = fullPath
        else:
            fullPath = str(self.program.script.path.absolute())
            displayPath = str(self.program.script.path.name)
        if displayPath != self.scriptNameWidget.text():
            self.scriptNameWidget.setText(displayPath)
        if fullPath != self.scriptNameWidget.toolTip():
            self.scriptNameWidget.setToolTip(fullPath)

        compiled = UIMaster.GetCompiledProgram(self.program)
        self.messageArea.Update(compiled.messages)
        if self.scaleWidget.value() != self.program.scale:
            self.scaleWidget.setValue(self.program.scale)

        if self.hideMessages.currentIndex() != int(self.program.hideMessages):
            self.hideMessages.setCurrentIndex(int(self.program.hideMessages))
        self.messageArea.setVisible(not self.program.hideMessages)
        self.clearMessagesButton.setVisible(not self.program.hideMessages)


        # Update the parameter and function widgets. These are complicated, so they have their own
        # methods for clarity.
        self.UpdateParameters()
        self.UpdateFunctions()

        self.itemProxy.adjustSize()
        self.itemProxy.setScale(self.program.scale)
        self.UpdateGeometry()

    def UpdateParameters(self):
        # Get the latest compiled program version
        compiled = UIMaster.GetCompiledProgram(self.program)

        # Make sure we have the right number of parameter widget sets in the layout. First, add
        # needed widget sets.
        for i in range(len(self.parameterWidgetSets), len(compiled.parameters)):
            newSet = ParameterWidgetSet()
            self.parameterWidgetSets.append(newSet)
            newSet.inspectorNameLabel.setStyleSheet(
                "background-color: " + (
                    "rgba(0, 0, 0, 0.2)" if i % 2 == 0 else "rgba(0, 0, 0, 0.1)"))
            self.parametersLayout.addWidget(newSet.inspectorNameLabel, i, 0)
            self.parametersLayout.addWidget(newSet.inspectorVisibilityToggle, i, 2)
            self.visibleParametersLayout.addWidget(newSet.itemNameLabel, i, 0)
            newSet.itemNameLabel.setStyleSheet(
                "background-color: " + (
                    "rgba(0, 0, 0, 0.2)" if i % 2 == 0 else "rgba(0, 0, 0, 0.1)"))
            newSet.inspectorVisibilityToggle.setCheckable(True)
            newSet.inspectorVisibilityToggle.toggled.connect(self.RecordChanges)

        # Then, remove excessive widget sets
        for i in range(len(compiled.parameters), len(self.parameterWidgetSets)):
            self.parameterWidgetSets[i - 1].inspectorNameLabel.deleteLater()
            self.parameterWidgetSets[i - 1].inspectorVisibilityToggle.deleteLater()
            self.parameterWidgetSets[i - 1].itemNameLabel.deleteLater()
            self.parameterWidgetSets[i - 1].inspectorValueWidget.deleteLater()
            self.parameterWidgetSets[i - 1].itemValueWidget.deleteLater()
        self.parameterWidgetSets = self.parameterWidgetSets[:len(compiled.parameters)]

        # Update widget sets. Enumerated so that we know where each widget is in the layout in case
        # they need to be replaced.
        for i, (parameterSymbol, parameterWidgetSet) in enumerate(
                zip(compiled.parameters, self.parameterWidgetSets)):
            # Ensure that the value fields match the type given.
            parameterType = compiled.parameters[parameterSymbol].parameterType
            minimum = compiled.parameters[parameterSymbol].minimum
            maximum = compiled.parameters[parameterSymbol].maximum
            if not DoTypesMatch(parameterWidgetSet.inspectorValueWidget.parameterType,
                                parameterType) or parameterWidgetSet.inspectorValueWidget.minimum != minimum or  parameterWidgetSet.inspectorValueWidget.maximum != maximum:
                # If the types don't match (or they haven't been set, i.e. parameterType is None),
                # we need to rebuild the value fields.
                self.parameterWidgetSets[i].inspectorValueWidget.deleteLater()
                self.parameterWidgetSets[i].itemValueWidget.deleteLater()

                # Inspector value field is the master. Changes to the item value field instead
                # change the inspector value field, which is what actually reports the change to
                # the backing program.
                inspectorWidget = ParameterValueWidget(parameterType, minimum, maximum)

                def RecordValueChange(ps=parameterSymbol, w=inspectorWidget):
                    self.program.parameterValues[ps] = w.GetValue()

                inspectorWidget.OnValueChanged.connect(RecordValueChange)
                itemWidget = ParameterValueWidget(parameterType, minimum, maximum)

                def RecordValueChange(ps=parameterSymbol, w=itemWidget):
                    self.program.parameterValues[ps] = w.GetValue()

                itemWidget.OnValueChanged.connect(RecordValueChange)

                # Add them to the layouts.
                self.parameterWidgetSets[i].inspectorValueWidget = inspectorWidget
                self.parameterWidgetSets[i].itemValueWidget = itemWidget
                self.parametersLayout.addWidget(inspectorWidget, i, 1)
                self.visibleParametersLayout.addWidget(itemWidget, i, 1)

            # Set the values to be the current value.
            parameterWidgetSet.inspectorValueWidget.SetValue(
                self.program.parameterValues[parameterSymbol])
            parameterWidgetSet.itemValueWidget.SetValue(
                self.program.parameterValues[parameterSymbol])

            # Set name fields and visibility
            parameterWidgetSet.itemNameLabel.setText(
                compiled.parameters[parameterSymbol].displayName)
            parameterWidgetSet.inspectorNameLabel.setText(
                compiled.parameters[parameterSymbol].displayName)
            parameterWidgetSet.inspectorVisibilityToggle.setIcon(
                self.shownIcon if self.program.parameterVisibility[parameterSymbol] else self.hiddenIcon)
            parameterWidgetSet.inspectorVisibilityToggle.setChecked(
                self.program.parameterVisibility[parameterSymbol])
            parameterWidgetSet.itemNameLabel.setVisible(
                self.program.parameterVisibility[parameterSymbol])
            parameterWidgetSet.itemValueWidget.setVisible(
                self.program.parameterVisibility[parameterSymbol])

    def UpdateFunctions(self):
        # Get the latest compiled program version
        compiled = UIMaster.GetCompiledProgram(self.program)

        # Make sure we have the right number of function widget sets in the layout. First, add
        # needed widget sets.
        def AddFunctionWidgetSet(index: int):
            newSet = FunctionWidgetSet()
            self.functionWidgetSets.append(newSet)
            self.functionsLayout.addWidget(newSet.startButton, index, 0, 1, 6)
            self.functionsLayout.addWidget(newSet.label, index, 0, 1, 5)
            self.functionsLayout.addWidget(newSet.stopButton, index, 6)
            self.functionsLayout.addWidget(newSet.pauseButton, index, 7)
            self.functionsLayout.addWidget(newSet.resumeButton, index, 7)
            newSet.startButton.clicked.connect(lambda: self.StartFunction(index))
            newSet.stopButton.clicked.connect(
                lambda: compiled.programFunctions[compiled.showableFunctions[index]].Stop())
            newSet.pauseButton.clicked.connect(
                lambda: compiled.programFunctions[compiled.showableFunctions[index]].Pause())
            newSet.resumeButton.clicked.connect(
                lambda: compiled.programFunctions[compiled.showableFunctions[index]].Resume())

        for i in range(len(self.functionWidgetSets), len(compiled.showableFunctions)):
            AddFunctionWidgetSet(i)

        # Remove excessive widget sets
        for i in range(len(compiled.showableFunctions), len(self.functionWidgetSets)):
            self.functionWidgetSets[i].Delete()
        self.functionWidgetSets = self.functionWidgetSets[:len(compiled.showableFunctions)]

        # Update widget sets
        for functionSymbol, functionWidgetSet in zip(compiled.showableFunctions,
                                                     self.functionWidgetSets):
            functionWidgetSet.startButton.setText(
                compiled.programFunctions[functionSymbol].functionName)
            functionWidgetSet.label.setText(compiled.programFunctions[functionSymbol].functionName)
            functionWidgetSet.startButton.setVisible(functionSymbol not in compiled.asyncFunctions)
            functionWidgetSet.label.setVisible(functionSymbol in compiled.asyncFunctions)
            functionWidgetSet.stopButton.setVisible(functionSymbol in compiled.asyncFunctions)
            functionWidgetSet.pauseButton.setVisible(functionSymbol in compiled.asyncFunctions and
                                                     not compiled.asyncFunctions[
                                                         functionSymbol].paused)
            functionWidgetSet.resumeButton.setVisible(functionSymbol in compiled.asyncFunctions and
                                                      compiled.asyncFunctions[
                                                          functionSymbol].paused)

    def StartFunction(self, index):
        compiled = UIMaster.GetCompiledProgram(self.program)
        compiled.programFunctions[compiled.showableFunctions[index]]()

    def Duplicate(self):
        newProgram = Program(self.program.script)
        newProgram.name = self.program.name
        newProgram.scale = self.program.scale
        newProgram.parameterValues = self.program.parameterValues.copy()
        newProgram.parameterVisibility = self.program.parameterVisibility.copy()
        newProgram.hideMessages = self.program.hideMessages
        UIMaster.Instance().currentChip.programs.append(newProgram)
        UIMaster.Instance().modified = True
        return ProgramItem(newProgram)

    def SetRect(self, rect: QRectF):
        super().SetRect(QRectF(rect))

        self.itemProxy.adjustSize()
        self.itemProxy.setScale(self.program.scale)
        self.UpdateGeometry()
        self.RecordChanges()

    def OnRemoved(self):
        UIMaster.Instance().currentChip.programs.remove(self.program)
        UIMaster.Instance().RemoveProgram(self.program)
        UIMaster.Instance().modified = True
        return True


# Convenience structure that stores the widgets for a single parameter.
class ParameterWidgetSet:
    def __init__(self):
        self.inspectorValueWidget = ParameterValueWidget()
        self.inspectorNameLabel = QLabel()
        self.inspectorVisibilityToggle = QPushButton("")
        self.inspectorVisibilityToggle.setStyleSheet("""
        QPushButton {
        background-color: rgb(200, 200, 200);
        border: none;
        icon-size: 20px 20px;
        }
        QPushButton:hover {
        background-color: rgb(230, 230, 230);
        }
        QPushButton:pressed {
        background-color: rgb(180, 180, 180);
        }
        """)
        self.inspectorVisibilityToggle.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        self.inspectorVisibilityToggle.setFixedWidth(40)
        self.itemValueWidget = ParameterValueWidget()
        self.itemNameLabel = QLabel()


# Convenience structure that stores the widgets for a single program function.
class FunctionWidgetSet:
    def __init__(self):
        self.startButton = QPushButton()
        self.label = QLabel()
        self.stopButton = QPushButton("Stop")
        self.stopButton.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.stopButton.setStyleSheet("""
        QPushButton {
        border: none;
        background-color: rgb(250, 150, 150);
        }
        QPushButton:hover {
        background-color: rgb(250, 200, 200);
        }
        QPushButton:pressed {
        background-color: rgb(250, 100, 100);
        }""")
        self.resumeButton = QPushButton("Resume")
        self.resumeButton.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.resumeButton.setStyleSheet("""
        QPushButton {
        border: none;
        background-color: rgb(150, 250, 150);
        }
        QPushButton:hover {
        background-color: rgb(200, 250, 200);
        }
        QPushButton:pressed {
        background-color: rgb(150, 250, 150);
        }""")
        self.pauseButton = QPushButton("Pause")
        self.pauseButton.setStyleSheet("""
        QPushButton {
        border: none;
        background-color: rgb(200, 200, 200);
        }
        QPushButton:hover {
        background-color: rgb(250, 250, 250);
        }
        QPushButton:pressed {
        background-color: rgb(150, 150, 150);
        }""")
        self.pauseButton.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.pauseButton.setFixedWidth(50)
        self.resumeButton.setFixedWidth(50)
        self.stopButton.setFixedWidth(50)

    def Delete(self):
        self.pauseButton.deleteLater()
        self.resumeButton.deleteLater()
        self.stopButton.deleteLater()
        self.label.deleteLater()

# Control widget for a UI-editable parameter.
class ParameterValueWidget(QWidget):
    OnValueChanged = Signal()

    def __init__(self, parameterType=None, minimum=None, maximum=None):
        super().__init__()
        self.parameterType = parameterType
        if parameterType is None:
            return
        controlWidget = None
        self.minimum=minimum
        self.maximum=maximum
        if self.parameterType in (int, float):
            controlWidget = QSpinBox() if self.parameterType == int else QDoubleSpinBox()
            if minimum is not None:
                controlWidget.setMinimum(minimum)
            if maximum is not None:
                controlWidget.setMaximum(maximum)
            controlWidget.valueChanged.connect(self.OnChanged)
        elif self.parameterType == str:
            controlWidget = QLineEdit()
            controlWidget.textChanged.connect(self.OnChanged)
        elif self.parameterType in [bool, ucscript.ProgramFunction,
                                    ucscript.Valve] or IsTypeValidOptions(parameterType):
            controlWidget = QComboBox()
            if self.parameterType == bool:
                controlWidget.addItems(["Yes", "No"])
            if IsTypeValidOptions(self.parameterType):
                controlWidget.addItems(list(self.parameterType.options))
            controlWidget.currentIndexChanged.connect(self.OnChanged)
        elif IsTypeValidList(self.parameterType):
            controlWidget = QWidget()
            controlLayout = QVBoxLayout()
            controlLayout.setContentsMargins(0, 0, 0, 0)
            controlWidget.setLayout(controlLayout)

            self.listItemsLayout = QVBoxLayout()
            controlLayout.addLayout(self.listItemsLayout)

            countLayout = QHBoxLayout()
            countLayout.setSpacing(0)
            countLayout.addWidget(QLabel("Count"))
            self.listCountWidget = QSpinBox()
            self.listCountWidget.setMinimum(0)
            self.listCountWidget.setMaximum(100)
            self.listCountWidget.valueChanged.connect(self.OnChanged)
            countLayout.addWidget(self.listCountWidget, stretch=1)
            controlLayout.addLayout(countLayout)

            self.listContents: typing.List[ParameterValueWidget] = []
        controlWidget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self._updating = False
        pLayout = QVBoxLayout()
        pLayout.setContentsMargins(0, 0, 0, 0)
        pLayout.setSpacing(0)
        self.setLayout(pLayout)
        self.controlWidget: typing.Union[
            QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QWidget, None] = controlWidget
        self.layout().addWidget(self.controlWidget)

    def OnChanged(self):
        if self._updating:
            return
        else:
            self.OnValueChanged.emit()

    def GetValue(self):
        if self.parameterType == bool:
            return self.controlWidget.currentText() == "Yes"
        elif self.parameterType == ucscript.Program:
            if 0 <= self.controlWidget.currentIndex() < len(
                    UIMaster.Instance().currentChip.programs):
                return UIMaster.Instance().currentChip.programs[self.controlWidget.currentIndex()]
        elif self.parameterType == ucscript.Valve:
            if 0 <= self.controlWidget.currentIndex() < len(UIMaster.Instance().currentChip.valves):
                return UIMaster.Instance().currentChip.valves[self.controlWidget.currentIndex()]
        elif IsTypeValidOptions(self.parameterType):
            return self.controlWidget.currentText()
        elif self.parameterType in (int, float):
            return self.controlWidget.value()
        elif self.parameterType == str:
            return self.controlWidget.text()
        elif IsTypeValidList(self.parameterType):
            listCount = self.listCountWidget.value()
            extras = listCount - len(self.listContents)
            extras = [NoneValueForType(self.parameterType.listType) for _ in range(extras)]
            return [x.GetValue() for x in self.listContents][:listCount] + extras

    def SetValue(self, value):
        self._updating = True
        if self.parameterType == bool:
            self.controlWidget.setCurrentText("Yes" if value else "No")
        elif self.parameterType in (int, float):
            self.controlWidget.setValue(value)
        elif self.parameterType == str:
            self.controlWidget.setText(value)
        elif IsTypeValidOptions(self.parameterType):
            self.controlWidget.setCurrentText(value)
        elif self.parameterType == ucscript.Program:
            try:
                newI = UIMaster.Instance().currentChip.programs.index(value)
            except ValueError:
                newI = -1
            if len(UIMaster.Instance().currentChip.programs) != self.controlWidget.count():
                self.controlWidget.clear()
                self.controlWidget.addItems(["x" for _ in UIMaster.Instance().currentChip.programs])
            [self.controlWidget.setItemText(i, x.name) for i, x in
             enumerate(UIMaster.Instance().currentChip.programs)]
            self.controlWidget.setCurrentIndex(newI)
        elif self.parameterType == ucscript.Valve:
            try:
                newI = UIMaster.Instance().currentChip.valves.index(value)
            except ValueError:
                newI = -1
            if len(UIMaster.Instance().currentChip.valves) != self.controlWidget.count():
                self.controlWidget.clear()
                self.controlWidget.addItems(["x" for _ in UIMaster.Instance().currentChip.valves])
            [self.controlWidget.setItemText(i, x.name) for i, x in
             enumerate(UIMaster.Instance().currentChip.valves)]
            self.controlWidget.setCurrentIndex(newI)
        elif IsTypeValidList(self.parameterType):
            if self.listCountWidget.value() != len(value):
                self.listCountWidget.setValue(len(value))
            if len(value) != len(self.listContents):
                [x.deleteLater() for x in self.listContents]
                self.listContents = [ParameterValueWidget(self.parameterType.listType) for _ in
                                     range(len(value))]
                [x.OnValueChanged.connect(self.OnChanged) for x in self.listContents]
                [self.listItemsLayout.addWidget(x) for x in self.listContents]
                [x.show() for x in self.listContents]
                self.topLevelWidget().adjustSize()
            [x.SetValue(v) for x, v in zip(self.listContents, value)]
        self._updating = False


class MessageArea(QScrollArea):
    def __init__(self):
        super().__init__()

        scrollContents = QWidget()
        self.setWidget(scrollContents)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.messageLayout = QVBoxLayout()
        self.messageLayout.setAlignment(Qt.AlignTop)
        self.messageLayout.setContentsMargins(0, 0, 0, 0)
        self.messageLayout.setSpacing(0)
        scrollContents.setLayout(self.messageLayout)

        self.verticalScrollBar().rangeChanged.connect(self.ScrollToBottom)
        self.lastMessages = None
        self.labels = []
        self.Update([])

    def ScrollToBottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def Update(self, messages):
        if messages == self.lastMessages:
            return

        [label.deleteLater() for label in self.labels]
        self.labels = []
        self.lastMessages = messages.copy()

        maxWidth = 200
        for i, message in enumerate(self.lastMessages):
            newEntry = QLabel(message.text)
            if message.messageType == Message.MESSAGE:
                bgColor = "#FFFFFF" if i % 2 == 0 else "#CCCCCC"
            else:
                bgColor = "#FFCCCC" if i % 2 == 0 else "#FFAAAA"
            newEntry.setStyleSheet("""
            padding: 5px;
            background-color: """ + bgColor)
            self.labels.append(newEntry)
            self.messageLayout.addWidget(newEntry)
            maxWidth = max(maxWidth, newEntry.sizeHint().width())
        self.setMinimumWidth(maxWidth)
