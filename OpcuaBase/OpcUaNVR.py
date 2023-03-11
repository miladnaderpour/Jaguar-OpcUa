import logging
from asyncua import Node


class OpcUaNVR:
    _logger = logging.getLogger('Jaguar-NVR')

    Tag: str = None
    Identifier: int
    Status: Node = None

    def __init__(self, tag: str, identifier: int):
        self.Tag = tag
        self.Identifier = identifier
