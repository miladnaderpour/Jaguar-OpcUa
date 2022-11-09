import logging

from asyncua import Node

from OpcuaBase.OpcUaElementType import OpcUaElementType


class OpcUaElement:
    _logger = logging.getLogger('Jaguar-Element')

    Name: str = None
    Extension: str = None
    Group: int
    Zone = ''

    Main: Node = None
    Status: Node = None
    Call: Node = None
    Transfer: Node = None
    PickUP: Node = None
    Confirm: Node = None
    Description: Node = None
    GroupCall: Node = None

    chan: str = ''

    Type: OpcUaElementType

    def __init__(self, name, ext, element_type: OpcUaElementType, group=0, zone=''):
        self.Name = name
        self.Extension = ext
        self.Zone = zone
        self.Group = group
        self.Type = element_type

    def get_nodes(self) -> [Node]:
        return [self.Call, self.PickUP,
                self.Confirm, self.GroupCall]

    def get_pager_nodes(self) -> [Node]:
        return [self.Call]
