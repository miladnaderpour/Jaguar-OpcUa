from typing import List

from asyncua import Node


class OpcUaPagingZone:
    Name: str = None
    chan: str = ''
    Location = ''
    Zone = ''
    Group: int
    Node: Node = None
    Elements: List[str] = None
    Active: bool

    def __init__(self, name: str, location: str, group: int = 0, zone='', elements=None):
        if elements is not None:
            self.Elements = elements
        self.Name = name
        self.Location = location
        self.Zone = zone
        self.Group = group
        self.Active = False
