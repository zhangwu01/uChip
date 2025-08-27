from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, \
    QListWidget, QListWidgetItem, QSpinBox, QComboBox, QHBoxLayout, QSizePolicy
from PySide6.QtCore import QTimer, QSize, Qt
from typing import Optional, List
from Data.Rig import Device
from UI.UIMaster import UIMaster
import time
import math


class RigView(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("Rig")

        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)

        self.solenoidsLayout = QGridLayout()
        self._lastNumbers = []

        mainLayout.addWidget(QLabel("<b>Solenoid Control</b>"))
        mainLayout.addWidget(BorderSpacer(False))
        mainLayout.addLayout(self.solenoidsLayout)
        self.noneConnectedLabel = QLabel("No solenoids available.")
        mainLayout.addWidget(self.noneConnectedLabel)

        mainLayout.addStretch(1)

        deviceListAndInfoLayout = QVBoxLayout()
        mainLayout.addLayout(deviceListAndInfoLayout, 0)

        self.devicesList = QListWidget()
        self.devicesList.currentRowChanged.connect(self.NewDeviceSelected)
        self.portInfoLabel = QLabel()
        self.portInfoLabel.setAlignment(Qt.AlignTop)
        self.portInfoLabel.setWordWrap(True)
        self.portInfoLabel.setMinimumWidth(200)
        deviceListAndInfoLayout.addWidget(QLabel("<b>Available Devices</b>"))
        deviceListAndInfoLayout.addWidget(BorderSpacer(False))
        dl = QHBoxLayout()
        dl.addWidget(self.devicesList, 1)
        dl.addWidget(self.portInfoLabel, 0)
        deviceListAndInfoLayout.addLayout(dl)

        self.startNumberBox = QSpinBox()
        self.startNumberBox.valueChanged.connect(self.PushUIToDevice)
        self.startNumberBox.setMaximum(1000)
        self.startNumberBox.setMinimum(0)
        self.invertA = ChoiceBox()
        self.invertB = ChoiceBox()
        self.invertC = ChoiceBox()
        self.enabledBox = ChoiceBox()

        [x.currentTextChanged.connect(self.PushUIToDevice) for x in
         [self.invertA, self.invertB, self.invertC, self.enabledBox]]

        deviceInfoLayout = QGridLayout()
        deviceListAndInfoLayout.addLayout(deviceInfoLayout)
        deviceInfoLayout.addWidget(QLabel("Enabled"), 0, 0)
        deviceInfoLayout.addWidget(self.enabledBox, 0, 1)
        deviceInfoLayout.addWidget(QLabel("Start Number"), 1, 0)
        deviceInfoLayout.addWidget(self.startNumberBox, 1, 1)
        deviceInfoLayout.addWidget(QLabel("Invert 0-7"), 2, 0)
        deviceInfoLayout.addWidget(self.invertA, 2, 1)
        deviceInfoLayout.addWidget(QLabel("Invert 8-15"), 3, 0)
        deviceInfoLayout.addWidget(self.invertB, 3, 1)
        deviceInfoLayout.addWidget(QLabel("Invert 16-23"), 4, 0)
        deviceInfoLayout.addWidget(self.invertC, 4, 1)

        self.blinkButton = QPushButton("Blink Solenoids")
        self.blinkButton.clicked.connect(self.Blink)

        deviceListAndInfoLayout.addWidget(self.blinkButton)
        self.selectedDevice: Optional[Device] = None
        self.lastDevicesList: List[Device] = []

        self.updateTimer = QTimer(self)
        self.updateTimer.timeout.connect(self.Update)
        self.updateTimer.start(30)

        self.Update()

        self.PushDeviceToUI()

    def Update(self):
        self.UpdateDeviceList()
        self.UpdateSolenoids()

    def PushUIToDevice(self):
        self.selectedDevice.enabled = self.enabledBox.IsTrue()
        self.selectedDevice.polarities = [self.invertA.IsTrue(), self.invertB.IsTrue(),
                                          self.invertC.IsTrue()]
        self.selectedDevice.startNumber = self.startNumberBox.value()
        if self.selectedDevice.enabled and not self.selectedDevice.IsConnected():
            self.selectedDevice.Connect()
        elif not self.selectedDevice.enabled and self.selectedDevice.IsConnected():
            self.selectedDevice.Disconnect()
        UIMaster.Instance().rig.FlushStates()
        self.PushDeviceToUI()

    def Blink(self):
        for i in range(5):
            state = (i % 2) == 0
            self.selectedDevice.SetSolenoids({i: state for i in
                                              range(self.selectedDevice.startNumber,
                                                    self.selectedDevice.startNumber + 24)})
            time.sleep(0.25)
        UIMaster.Instance().rig.FlushStates()

    def PushDeviceToUI(self):
        [x.setEnabled(self.selectedDevice is not None) for x in
         [self.enabledBox, self.invertA, self.invertB, self.invertC, self.startNumberBox]]
        [x.blockSignals(True) for x in
         [self.enabledBox, self.invertA, self.invertB, self.invertC, self.startNumberBox]]
        self.blinkButton.setEnabled(
            self.selectedDevice is not None and self.selectedDevice.IsConnected())
        if self.selectedDevice is None:
            self.portInfoLabel.setText("No device selected")
            return
        self.enabledBox.SetTrue(self.selectedDevice.enabled)
        [x.SetTrue(y) for x, y in
         zip([self.invertA, self.invertB, self.invertC], self.selectedDevice.polarities)]
        self.startNumberBox.setValue(self.selectedDevice.startNumber)
        [x.blockSignals(False) for x in
         [self.enabledBox, self.invertA, self.invertB, self.invertC, self.startNumberBox]]

        self.portInfoLabel.setText(self.selectedDevice.Summary())

    def UpdateDeviceList(self):
        devices = [d for d in UIMaster.Instance().rig.allDevices if d.available]
        if devices == self.lastDevicesList:
            return
        self.lastDevicesList = devices.copy()
        self.devicesList.clear()
        for d in UIMaster.Instance().rig.allDevices:
            if d.available:
                i = QListWidgetItem(d.portInfo.name + " (" + d.portInfo.device + ")")
                self.devicesList.addItem(i)
                if self.selectedDevice == d:
                    self.devicesList.setCurrentItem(i)

    def NewDeviceSelected(self):
        self.selectedDevice = self.lastDevicesList[self.devicesList.currentRow()]
        self.PushDeviceToUI()

    def UpdateSolenoids(self):
        numbers = UIMaster.Instance().rig.GetConnectedSolenoidNumbers()
        if numbers == self._lastNumbers:
            return
        self._lastNumbers = numbers

        for i in reversed(range(self.solenoidsLayout.count())):
            w = self.solenoidsLayout.itemAt(i).widget()
            if w is not None:
                w.deleteLater()

        for i, n in enumerate(numbers):
            row = int(i / 8)
            column = i % 8
            self.solenoidsLayout.addWidget(SolenoidButton(n), row, column)

        nRows = math.ceil(len(numbers) / 8)
        for rowNumber in range(nRows):
            numbersInRow = numbers[rowNumber * 8:(rowNumber + 1) * 8]
            self.solenoidsLayout.addWidget(BorderSpacer(True), rowNumber, 8)
            self.solenoidsLayout.addWidget(SetAllButton("ON", numbersInRow, True), rowNumber, 9)
            self.solenoidsLayout.addWidget(SetAllButton("OFF", numbersInRow, False), rowNumber, 10)

        if len(numbers) > 0:
            self.solenoidsLayout.addWidget(SetAllButton("ALL ON", numbers, True, False),
                                           nRows + 1, 0, 1, 5)
            self.solenoidsLayout.addWidget(SetAllButton("ALL OFF", numbers, False, False),
                                           nRows + 1, 5, 1, 6)
        self.noneConnectedLabel.setVisible(len(numbers) == 0)


class ChoiceBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.addItem("YES")
        self.addItem("NO")

    def IsTrue(self):
        return self.currentText() == "YES"

    def SetTrue(self, isTrue: bool):
        self.setCurrentText("YES" if isTrue else "NO")


class BorderSpacer(QLabel):
    def __init__(self, vertical):
        super().__init__()
        self.setStyleSheet("""background-color: #999999""")
        if vertical:
            self.setFixedWidth(1)
        else:
            self.setFixedHeight(1)


solenoidOnStyle = """
QPushButton {
background-color: #ebb734; 
border: 1px solid black;
}
QPushButton::hover {
background-color: #bd932a;
}
QPushButton::pressed {
background-color: #a17d23;
}
"""

solenoidOffStyle = """
QPushButton {
background-color: white; 
border: 1px solid black;
}
QPushButton::hover {
background-color: #EEEEEE;
}
QPushButton::pressed {
background-color: #DDDDDD;
}
"""


class SolenoidButton(QPushButton):
    def __init__(self, n):
        super().__init__()
        self.number = n
        self.setText(str(n))
        self.clicked.connect(self.ToggleState)
        self.checkTimer = QTimer(self)
        self.checkTimer.timeout.connect(self.UpdateDisplay)
        self.checkTimer.start(100)

        self._displayState = None

        self.UpdateDisplay()

    def sizeHint(self) -> QSize:
        return QSize(30, 30)

    def minimumSizeHint(self) -> QSize:
        return QSize(30, 30)

    def resizeEvent(self, event) -> None:
        self.setMinimumHeight(self.width())
        super().resizeEvent(event)

    def ToggleState(self):
        r = UIMaster.Instance().rig
        r.SetSolenoidState(self.number, not r.GetSolenoidState(self.number))
        self.UpdateDisplay()

    def UpdateDisplay(self):
        s = UIMaster.Instance().rig.GetSolenoidState(self.number)
        if s == self._displayState:
            return
        self._displayState = s
        if UIMaster.Instance().rig.GetSolenoidState(self.number):
            self.setStyleSheet(solenoidOnStyle)
        else:
            self.setStyleSheet(solenoidOffStyle)


class SetAllButton(QPushButton):
    def __init__(self, text, n, stateToSet, scale=True):
        super().__init__()
        self.scale = scale
        self.numbers = n
        self.stateToSet = stateToSet
        if stateToSet:
            self.setText(text)
            self.setStyleSheet(solenoidOnStyle)
        else:
            self.setText(text)
            self.setStyleSheet(solenoidOffStyle)
        self.pressed.connect(self.Perform)

    def sizeHint(self) -> QSize:
        return QSize(30, 30)

    def minimumSizeHint(self) -> QSize:
        return QSize(30, 30)

    def resizeEvent(self, event) -> None:
        if self.scale:
            self.setMinimumHeight(self.width())
        super().resizeEvent(event)

    def Perform(self):
        r = UIMaster.Instance().rig
        for i in self.numbers:
            r.SetSolenoidState(i, self.stateToSet)
