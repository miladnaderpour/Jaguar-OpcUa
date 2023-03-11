from typing import Dict, List

from OpcuaBase.OpcUaCamera import OpcUaCamera
from OpcuaBase.OpcUaNVR import OpcUaNVR
from OpcuaBase.OpcUaPopupCmd import OpcUaPopupCmd


class OpcUaPopup:
    IPCams: Dict[str, OpcUaCamera]
    Commands: Dict[str, OpcUaPopupCmd]
    NVRs: Dict[str, OpcUaNVR]

    def __init__(self):
        self.IPCams = {}
        self.Commands = {}
        self.NVRs = {}

    def GetIPCams(self, tags: List[str]) -> List[OpcUaCamera]:
        result = []
        for c in tags:
            if c in self.IPCams.keys():
                v = self.IPCams[c]
                result.append(v)
        return result
