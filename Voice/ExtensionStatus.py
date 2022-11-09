from enum import Enum


class ExtensionStatus(Enum):
    OnHook = 1
    Up = 2
    Ringing = 4
    OnHold = 8
    UnReachable = 16

