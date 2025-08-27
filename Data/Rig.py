from typing import Dict
from serial.tools.list_ports import comports
from typing import List, Optional
from serial import Serial
from serial.tools.list_ports_common import ListPortInfo


class Rig:
    def __init__(self):
        self.solenoidStates: Dict[int, bool] = {}
        self.allDevices: List[Device] = []

    def RescanForDevices(self):
        portInfos = RescanPorts()

        for device in self.allDevices:
            match = next((p for p in portInfos if p.hwid == device.portInfo.hwid),
                         None)
            if match is not None:
                device.portInfo = match
                device.available = True
                if device.enabled:
                    device.Connect()
            else:
                device.available = False
                device.Disconnect()

        for portInfo in portInfos:
            if portInfo.hwid not in [d.portInfo.hwid for d in
                                     self.allDevices] or portInfo.hwid == "":
                newDevice = Device()
                newDevice.portInfo = portInfo
                newDevice.available = True
                self.allDevices.append(newDevice)

    def Disconnect(self):
        for device in self.allDevices:
            device.Disconnect()

    def SetSolenoidState(self, number: int, state: bool):
        self.solenoidStates[number] = state

    def GetSolenoidState(self, number: int):
        if number not in self.solenoidStates:
            self.solenoidStates[number] = False
        return self.solenoidStates[number]

    def FlushStates(self):
        for device in self.allDevices:
            device.SetSolenoids(self.solenoidStates)
        # for device in self.allDevices:
        #     device.Flush()

    def GetConnectedSolenoidNumbers(self):
        numbers = []
        for d in self.allDevices:
            if d.enabled and d.IsConnected():
                for n in range(d.startNumber, d.startNumber + 24):
                    if n not in numbers:
                        numbers.append(n)
        return sorted(numbers)


class Device:
    def __init__(self):
        self.portInfo: Optional[ListPortInfo] = None
        self.startNumber = 0
        self.polarities = [False, False, False]
        self.enabled = False
        self.available = False
        self.serialPort: Optional[Serial] = None
        self.solenoidStates = [False for _ in range(24)]

    def IsConnected(self):
        return self.serialPort is not None and self.serialPort.is_open

    def __getstate__(self):
        d = self.__dict__.copy()
        d['serialPort'] = None
        d['available'] = False
        return d

    def __setstate__(self, state):
        self.__dict__ = state

    def SetSolenoids(self, solenoidStates: Dict[int, bool]):
        if not self.enabled or not self.IsConnected():
            return

        for i in range(self.startNumber, self.startNumber + 24):
            if i in solenoidStates:
                self.solenoidStates[i - self.startNumber] = solenoidStates[i]

        polarizedStates = [state != self.polarities[int(i / 8)] for (i, state) in
                           enumerate(self.solenoidStates)]
        aState = ConvertPinStatesToBytes(polarizedStates[0:8])
        bState = ConvertPinStatesToBytes(polarizedStates[8:16])
        cState = ConvertPinStatesToBytes(polarizedStates[16:24])
        self.Write(b'A' + aState)
        self.Write(b'B' + bState)
        self.Write(b'C' + cState)

    def Write(self, data):
        self.serialPort.write(data)

    def Flush(self):
        if not self.enabled or not self.IsConnected():
            return
        self.serialPort.flush()

    def Connect(self):
        if self.IsConnected():
            return
        self.serialPort = Serial(self.portInfo.device, baudrate=115200, timeout=0, write_timeout=0)
        self.serialPort.write(b'!A' + bytes([0]))
        self.serialPort.write(b'!B' + bytes([0]))
        self.serialPort.write(b'!C' + bytes([0]))
        self.serialPort.flush()

    def Disconnect(self):
        if self.IsConnected():
            self.serialPort.close()
        self.serialPort = None

    def Summary(self):
        return """Name: {}
        Device: {}
        Serial Number: {}
        Location: {}
        Manufacturer: {}
        Product: {}
        Interface: {}
        """.format(self.portInfo.name,
                   self.portInfo.device,
                   self.portInfo.serial_number,
                   self.portInfo.location,
                   self.portInfo.manufacturer,
                   self.portInfo.product,
                   self.portInfo.interface
                   ).replace("    ", "\t").replace("\t", "")


def ConvertPinStatesToBytes(state: List[bool]):
    number = 0
    for i in range(8):
        if state[i]:
            number += 1 << i
    return bytes([number])


def RescanPorts():
    return comports()


class DummyDevice(Device):
    n = 0

    class DummyPortInfo:
        def __init__(self):
            self.name = "Dummy"
            self.device = "DEVICE"
            self.serial_number = "XXXXXX"
            self.location = "USB0"
            self.manufacturer = "A dummy."
            self.description = "Some info."
            self.product = "Dummy product."
            self.interface = "USB"
            self.hwid = "What goes here?"

    def __init__(self):
        super().__init__()
        self.portInfo = DummyDevice.DummyPortInfo()
        self.available = True
        self.enabled = True
        self.connected = True
        self.startNumber = DummyDevice.n
        DummyDevice.n += 24

    def IsConnected(self):
        return self.connected

    def Connect(self):
        print("Connecting")
        self.connected = True

    def Flush(self):
        if not self.connected:
            print("ERROR: Not connected!")
        print("Flushing")

    def Disconnect(self):
        print("Disconnecting")
        self.connected = False

    def Write(self, data):
        if not self.connected:
            print("ERROR: Not connected!")
        print(data)
