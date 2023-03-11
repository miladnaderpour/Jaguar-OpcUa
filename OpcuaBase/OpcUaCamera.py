import logging

from asyncua import Node


class OpcUaCamera:
    _logger = logging.getLogger('Jaguar-Camera')

    Tag: str = None
    Nvr: str = None
    Channel: int
    Identifier: int
    Main: Node = None
    Status: Node = None
    Popup: Node = None
    Value: Node = None

    def __init__(self, tag: str, identifier: int, nvr: str, channel: int):
        self.Tag = tag
        self.Identifier = identifier
        self.Nvr = nvr
        self.Channel = channel

    def get_nodes(self) -> [Node]:
        return [self.Popup]
