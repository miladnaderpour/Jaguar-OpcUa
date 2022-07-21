from typing import Dict

from asyncua import Node

from OpcuaBase.OpcUaPagingZone import OpcUaPagingZone


class OpcUaPaging:
    Status: Node
    Status_Code: Node
    Active_Channels: Node

    Reset: Node

    Live: Node
    Live_Status: Node
    Live_Test: Node

    Broadcasting_Message: Node
    Broadcasting_Message_No: Node
    Broadcasting_Message_Status: Node
    Broadcasting_Message_Message: Node

    Semiautomatic_Paging: Node
    Semiautomatic_Paging_Status: Node
    Semiautomatic_Paging_No_Repetitions: Node
    Semiautomatic_Paging_Delay: Node
    Semiautomatic_Paging_Repetition_Status: Node

    Zones: Dict[str, OpcUaPagingZone]

    def __init__(self):
        self.Zones = {}

    def get_nodes(self):
        return [self.Live,
                self.Live_Test,
                self.Broadcasting_Message,
                self.Semiautomatic_Paging]

    def get_zones(self):
        x = []
        for zone in self.Zones:
            x.append(self.Zones[zone].Node)
        return x
