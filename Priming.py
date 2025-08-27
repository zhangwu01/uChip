from ucscript import *

class Chip: 
    def __init__(self):
        self.reagentValves = [FindValve("R"+str(i+1)) for i in range(8)]
        self.vehicleValves = [FindValve("V"+str(i+1)) for i in range(8)]
        self.sampleValve = FindValve("Sample")
        self.oilValve = FindValve("Oil")
        self.keepValve = FindValve("Keep")
        self.discardValve = FindValve("Discard")
        self.allValves = self.reagentValves+self.vehicleValves+[self.sampleValve,self.oilValve,self.keepValve,self.discardValve]

@display("Full Seal")
def FullSeal():
    chip = Chip()
    [valve.Close() for valve in chip.allValves]

@display("Close All Inlets")
def CloseAllInlets():
    chip = Chip()
    [valve.Close() for valve in chip.allValves]
    chip.discardValve.Open()


@display("Debubble")
def Debubble():
    chip = Chip()
    [valve.Close() for valve in chip.allValves]
    chip.discardValve.Open()
    [valve.Open() for valve in chip.vehicleValves]
    yield WaitForSeconds(2)
    chip.discardValve.Close()

@display("Oil Calibration")
def OilCalibration():
    chip = Chip()
    [valve.Close() for valve in chip.allValves]
    chip.sampleValve.Open()
    chip.oilValve.Open()
    chip.discardValve.Open()

@display("Droplet Calibration")
def DropletCalibration():
    chip = Chip()
    [valve.Close() for valve in chip.allValves]
    [valve.Open() for valve in chip.vehicleValves]
    chip.sampleValve.Open()
    chip.oilValve.Open()
    chip.discardValve.Open()
