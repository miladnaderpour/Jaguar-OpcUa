import logging

from asyncua import Node


class OpcUaElement:
    _logger = logging.getLogger('Jaguar-Element')

    Main: Node = None
    Status: Node = None
    Call: Node = None
    Transfer: Node = None
    PickUP: Node = None
    Confirm: Node = None
    Name: str = None
    chan: str = ''

    def __init__(self, name):
        self.Name = name

    def get_nodes(self) -> [Node]:
        return [self.Call, self.PickUP,
                self.Confirm]
