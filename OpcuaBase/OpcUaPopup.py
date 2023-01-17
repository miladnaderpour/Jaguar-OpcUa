from typing import Dict

from OpcuaBase.OpcUaCamera import OpcUaCamera
from OpcuaBase.OpcUaPopupCmd import OpcUaPopupCmd


class OpcUaPopup:
    IPCams: Dict[str, OpcUaCamera]
    Commands: Dict[str, OpcUaPopupCmd]

    def __init__(self):
        self.IPCams = {}
        self.Commands = {}
