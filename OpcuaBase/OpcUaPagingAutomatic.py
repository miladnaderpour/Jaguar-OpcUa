import logging
from typing import Dict

from asyncua import Node


class OpcUaPagingAutomaticMessage:
    Name: str
    Extension: str
    Index: int
    CMD: str

    Message: Node = None

    def __init__(self, name: str, extension: str, index: int, message: Node):
        self.Name = name
        self.Extension = extension
        self.Index = index
        self.Message = message


def _get_active_index(val: int):
    b = []
    for x in range(0, 8):
        r = pow(2, x)
        rs = val & r
        if rs == r:
            b.append(x)
    return b


class OpcUaPagingAutomaticCommand:
    Name: str
    CMD: Node
    Message: Dict[int, OpcUaPagingAutomaticMessage]

    def __init__(self, name: str, cmd: Node):
        self._logger = logging.getLogger('Jaguar-Automatic-Command')
        self.Name = name
        self.Messages = {}
        self.CMD = cmd

    def Add(self, index: int, name: str, extension: str,  message: Node):
        self._logger.info(' ---- Add ---- Name:%s , Ext:%s, Bit:%s ', name, extension, index)
        self.Messages[index] = OpcUaPagingAutomaticMessage(name, extension, index, message)

    async def GetAutoMaticPagers(self):
        x: Dict[int, OpcUaPagingAutomaticMessage] = {}
        vl = await self.CMD.get_value()
        indexes = _get_active_index(vl)
        for p in indexes:
            if p in self.Messages.keys():
                x[p] = self.Messages[p]
        for m in x:
            msg = await x[m].Message.get_value()
            self._logger.info(' ---- ---- CMD:%s , Bit:%i, MSG:%s', self.Name, m, msg)
        return x
