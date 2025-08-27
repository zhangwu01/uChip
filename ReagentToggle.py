from ucscript import *

valveNumber = Parameter(int)

def SetValves(v, r):
    FindValve("V" + str(valveNumber.Get())).SetOpen(v)
    FindValve("R" + str(valveNumber.Get())).SetOpen(r)

@display
def On():
    SetValves(False, True)

@display
def Off():
    SetValves(True, False)
