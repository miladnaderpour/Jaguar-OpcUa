import logging
from typing import Dict

from asyncua import Node
from asyncua.ua import VariantType


class ElementStatus:
    Extension: str
    Group: str
    Index: int
    Current_Value: bool

    def __init__(self, extension: str, group: str, index: int):
        self.Extension = extension
        self.Group = group
        self.Index = index
        self.Current_Value = False


class GroupStatus:
    Group: str
    Node: Node
    Current_Value: int

    def __init__(self, group: str, node: Node):
        self.Group = group
        self.Node = node
        self.Current_Value = 0


def _calculate_new_value(node_value: int, index: int, val: bool) -> int:
    r = pow(2, index)
    rs = node_value & r
    if val & rs != r:
        return node_value ^ r
    elif not val & rs != 0:
        return node_value ^ r
    else:
        return node_value


async def _update_group_status(group_status: GroupStatus, element_status: ElementStatus, value: bool):
    gv = _calculate_new_value(group_status.Current_Value, element_status.Index, value)
    await group_status.Node.set_value(gv, VariantType.Byte)
    group_status.Current_Value = gv
    element_status.Current_Value = value


class OpcUaElementGroupStatus:
    Status_Group: Dict[str, GroupStatus]
    Elements: Dict[str, ElementStatus]
    Identifier: int

    def __init__(self):
        self._logger = logging.getLogger('Jaguar-ElementGroupStatus')
        self.Status_Group = {}
        self.Elements = {}
        self.Identifier = 7700

    def add_group(self, group: str, node: Node):
        self._logger.info('Add Status Group %s to OpcUaElementGroupStatus')
        if group not in self.Status_Group:
            self.Status_Group[group] = GroupStatus(group, node)
            self.Identifier += 1

    def add(self, extension: str, group: str, index: int):
        self._logger.info('Add extension %s to Group %s with index %s', extension, group, index)
        if extension not in self.Elements:
            self.Elements[extension] = ElementStatus(extension, group, index)

    async def set_extension_status(self, extension: str, value: bool):
        self._logger.info('Set extension %s Status to %s', extension, value)
        if extension in self.Elements:
            el = self.Elements[extension]
            grp = self.Status_Group[el.Group]
            self._logger.info('extension %s and Group %s are found!', extension, grp.Group)
            self._logger.info('value is  %s, Current_Value is %s', value, el.Current_Value)
            if value != el.Current_Value and el.Group in self.Status_Group:
                self._logger.info('Group %s value need Change to current = %s', grp.Group, grp.Current_Value)
                await _update_group_status(grp, el, value)
                self._logger.info('Group %s new Value is changed to %s', grp.Group, grp.Current_Value)
            else:
                self._logger.info('extension %s not Found!', extension)
