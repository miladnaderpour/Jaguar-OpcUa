import logging

from asyncua import Node

from OpcuaBase.OpcUaElementType import OpcUaElementType


class OpcUaElement:
    _logger = logging.getLogger('Jaguar-Element')

    Main: Node = None
    Status: Node = None
    Call: Node = None
    Transfer: Node = None
    PickUP: Node = None
    Confirm: Node = None
    Description: Node = None
    Name: str = None
    chan: str = ''
    Location = ''
    Zone = ''
    Group: int
    Type: OpcUaElementType

    def __init__(self, name, element_type: OpcUaElementType, location, group=0, zone=''):
        self.Name = name
        self.Zone = zone
        self.Group = group
        self.Location = location
        self.Type = element_type

    def get_nodes(self) -> [Node]:
        return [self.Call, self.PickUP,
                self.Confirm]

    def get_pager_nodes(self) -> [Node]:
        return [self.Call]
