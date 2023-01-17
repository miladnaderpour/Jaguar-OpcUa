import logging
from typing import Dict
from asyncua import Node


class OpcUaPopupCmd:
    _logger = logging.getLogger('Jaguar-Camera')
    Name: str
    Node: Node
    BitMap: Dict[int, str]

    def __init__(self, name: str):
        self.Name = name
        self.BitMap = {}
