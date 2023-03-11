import logging
from typing import Dict, List
from asyncua import Node


def compare(new: int, old: int):
    result = []
    xr = old ^ new
    for x in range(0, 8):
        bitmask = pow(2, x)
        c = xr & bitmask
        if c == bitmask:
            if new & bitmask == bitmask:
                result.append([int(x), True])
            else:
                result.append([int(x), False])
    return result


class OpcUaPopupCmd:
    _logger = logging.getLogger('Jaguar-Camera')
    Name: str
    Node: Node
    BitMap: Dict[int, str]
    LastState: int = 0

    def __init__(self, name: str):
        self.Name = name
        self.BitMap = {}

    async def GetActiveTags(self) -> List[str]:
        tags: List[str] = []
        val = await self.Node.get_value()
        self._logger.info('%s Command Value is %s', self.Name, val)
        res = compare(val, self.LastState)
        self._logger.info('%s Command Compare Result count %s', self.Name, len(res))
        for [b, f] in res:
            bit = int(b)
            self._logger.info('%s Command Compare : Bit %s Set To %s', self.Name, bit, f)
            if bit in self.BitMap:
                self._logger.info('%s Command : Bit %s is %s', self.Name, bit, self.BitMap[bit])
                if f:
                    tags.append(self.BitMap[bit])
            else:
                self._logger.info('%s Command : Bit %s Not found in BitMap', self.Name, bit)
        self.LastState = val
        return tags

    def PrintBitmap(self):
        for t in self.BitMap:
            self._logger.info('%s Bit %s Is Set To %s', self.Name, t, self.BitMap[t])
