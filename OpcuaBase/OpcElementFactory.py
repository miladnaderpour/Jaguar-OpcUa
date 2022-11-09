import configparser
import logging
import re
from typing import Dict, Any, List

from asyncua import ua, Node
from asyncua.ua import VariantType

from OpcServer.JaguarOpcUaServer import JaguarOpcUaServer
from OpcuaBase.OpcUaCalling import OpcUaCalling
from OpcuaBase.OpcUaElement import OpcUaElement
from OpcuaBase.OpcUaElementGroupStatus import OpcUaElementGroupStatus
from OpcuaBase.OpcUaElementType import OpcUaElementType
from OpcuaBase.OpcUaPaging import OpcUaPaging
from OpcuaBase.OpcUaPagingZone import OpcUaPagingZone
from OpcuaBase.OpcUaParameter import OpcUaParameter
from OpcuaBase.OpcUaPreRecordedMessage import OpcUaPreRecordedMessage


def get_element_config(config: str) -> [str, str, str]:
    sp = str(config).split(',')
    if len(sp) == 3:
        return [sp[0], sp[1], sp[2]]
    return [config, 0, '']


def get_zone_location(config: str) -> [str, str, str, List[str]]:
    elm: List[str] = []
    rs = re.search(r'(?P<location>\w*),(?P<zone>\w*),(?P<group>\w*)(,\[(?P<element>(?:[^,\]]+,?)+)])?', config)
    if rs.group('element') is not None:
        els = rs.group('element').split(',')
        for x in els:
            elm.append(x)
    return [rs.group('location'), rs.group('zone'), rs.group('group'), elm]


def get_pre_record_filename(config: str) -> [str, str]:
    sp = str(config).split(',')
    if len(sp) == 2:
        return [sp[0], sp[1]]
    return ['Not Define', '']


def get_parameter_configs(config: str) -> [Any, VariantType, int]:
    sp = str(config).split(',')
    if len(sp) == 3:
        match int(sp[1]):
            case 12:  # string variant type
                return [str(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case 1:  # Boolean variant type
                return [bool(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case 3:  # byte variant type
                return [bytes(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case 4:  # Int16 variant type
                return [int(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case _:
                return [config, VariantType.String, 0]
    return [config, VariantType.String]


def get_status_group_index(config: str) -> (str, int):
    sp = str(config).split(',')
    if len(sp) == 2:
        return sp[0], int(sp[1])
    return '-', -1


class OpcElementFactory:
    Parameters: Dict[str, OpcUaParameter]

    def __init__(self, server: JaguarOpcUaServer):
        self._logger = logging.getLogger('Jaguar-ElementFactory')
        self._config = configparser.ConfigParser()
        self._config.optionxform = str
        self._config.read('Stations.conf')
        self._parameters = configparser.ConfigParser()
        self._parameters.optionxform = str
        self._parameters.read('Parameters.conf')
        self._server = server
        self.Parameters = {}

    async def _create_element(self, parent, name, element_type: OpcUaElementType, config) -> OpcUaElement:

        [ext, group, zone] = get_element_config(config)
        el = OpcUaElement(name, ext, element_type, int(group), zone)
        identifier = int(ext) * 10
        el.Main = await parent.add_folder(self._server.idx, f'{name}')
        el.Status = await self._server.add(identifier + 1, el.Main, f'{name}-ST', 16, VariantType.Byte)
        el.Call = await self._server.add(identifier + 2, el.Main, f'{name}-CALL', 0, VariantType.Boolean)
        el.Confirm = await self._server.add(identifier + 3, el.Main, f'{name}-CONFIRM', 0, VariantType.Boolean)
        el.Transfer = await self._server.add(identifier + 4, el.Main, f'{name}-TRANSFER', '', VariantType.String)
        el.PickUP = await self._server.add(identifier + 5, el.Main, f'{name}-PICKUP', 0, VariantType.Boolean)
        el.Description = await self._server.add(identifier + 6, el.Main, f'{name}-DES', 'Init', VariantType.String)
        el.GroupCall = await self._server.add(identifier + 7, el.Main, f'{name}-GroupCall', 0, VariantType.Boolean)
        return el

    async def _create_elements(self, parent, config, element_type: OpcUaElementType) -> Dict[str, OpcUaElement]:
        elements: Dict[str, OpcUaElement] = {}

        for x in config:
            if config[x] != '0':
                if x not in elements:
                    el = await self._create_element(parent, x, element_type, config[x])
                    elements[x] = el
                else:
                    self._logger.error('Element %s is exist in Dictionary', x)
        return elements

    async def _create_station_elements(self) -> Dict[str, OpcUaElement]:
        config = self._config['Extension']
        parent = await self._server.add_folder('TEL')
        return await self._create_elements(parent, config, OpcUaElementType.SOS)

    async def _create_pager_elements(self) -> Dict[str, OpcUaElement]:
        config = self._config['Pagers']
        parent = await self._server.add_folder('Pagers')
        return await self._create_elements(parent, config, OpcUaElementType.Pager)

    async def _create_operator_elements(self) -> Dict[str, OpcUaElement]:
        config = self._config['Operator']
        parent = await self._server.add_folder('Operator')
        return await self._create_elements(parent, config, OpcUaElementType.Operator)

    async def get_elements(self) -> Dict[str, OpcUaElement]:
        elements = await self._create_station_elements()
        elements.update(await self._create_pager_elements())
        elements.update(await self._create_operator_elements())
        return elements

    async def _create_parameter(self, parent: Node, name, config) -> OpcUaParameter:
        b = get_parameter_configs(config)
        self._logger.info(b)
        [value, typ, identifier] = b
        pr = OpcUaParameter(name, typ)
        pr.Value = await self._server.add(identifier, parent, name, value, typ)
        return pr

    async def get_parameters(self) -> Dict[str, OpcUaParameter]:
        parent = await self._server.add_folder('Parameters')
        config = self._parameters['Parameters']
        for x in config:
            if config[x] != '0':
                if x not in self.Parameters:
                    el = await self._create_parameter(parent, x, config[x])
                    self.Parameters[x] = el
                else:
                    self._logger.error('{x} is exist in Parameters')
        return self.Parameters

    async def _create_zone(self, identifier, name, config, parent: Node) -> OpcUaPagingZone:
        [location, zone, group, elements] = get_zone_location(config)
        self._logger.info('Zone %s : Elements : %s', name, elements)
        el = OpcUaPagingZone(name, location, int(group), zone, elements)
        el.Node = await self._server.add(identifier, parent, f'{name}', False, VariantType.Boolean)
        return el

    async def _create_paging_element(self, parent: Node) -> OpcUaPaging:

        pg = OpcUaPaging()
        pg.Status = await self._server.add(6000, parent, 'Paging-Status', 'Ready...', VariantType.String, False)
        pg.Status_Code = await self._server.add(6001, parent, 'Paging-Status-Code', 1, VariantType.Byte, False)
        pg.Active_Channels = await self._server.add(6006, parent, 'Paging-Active-Channels', 0, VariantType.Int16, False)
        pg.Reset = await self._server.add(6002, parent, 'Paging-Reset', 1, VariantType.Byte, True)

        pg.Live = await self._server.add(6003, parent, 'Paging-Live', False, VariantType.Boolean, True)
        pg.Live_Status = await self._server.add(6004, parent, 'Paging-Live-Status', False, VariantType.Boolean, True)
        pg.Live_Test = await self._server.add(6005, parent, 'Paging-Live-Test', False, VariantType.Boolean, True)

        pg.Broadcasting_Message = await self._server.add(6010, parent, 'Broadcasting-Message', False,
                                                         VariantType.Boolean,
                                                         True)
        pg.Broadcasting_Message_No = await self._server.add(6011, parent, 'Broadcasting-Message-No', 0,
                                                            VariantType.Int16,
                                                            True)
        pg.Broadcasting_Message_Status = await self._server.add(6012, parent, 'Broadcasting-Message-Status', False,
                                                                VariantType.Boolean, True)

        pg.Broadcasting_Message_Message = await self._server.add(6013, parent, 'Broadcasting-Message-Message', '',
                                                                 VariantType.String, True)

        pg.Semiautomatic_Paging = await self._server.add(6020, parent, 'Semiautomatic-Paging', False,
                                                         VariantType.Boolean, True)
        pg.Semiautomatic_Paging_Status = await self._server.add(6021, parent, 'Semiautomatic-Paging-Status', False,
                                                                VariantType.Boolean, True)
        pg.Semiautomatic_Paging_No_Repetitions = await self._server.add(6022, parent,
                                                                        'Semiautomatic-Paging-No-Repetitions',
                                                                        1, VariantType.Int16, True)
        pg.Semiautomatic_Paging_Delay = await self._server.add(6023, parent, 'Semiautomatic-Paging-Delay', 5,
                                                               VariantType.Int16, True)
        pg.Semiautomatic_Paging_Repetition_Status = await self._server.add(6024, parent,
                                                                           'Semiautomatic-Paging-Repetition-Status',
                                                                           'Stand By...', VariantType.String, True)

        return pg

    async def get_paging(self) -> OpcUaPaging:
        config = self._config['Paging Zone']
        config2 = self._config['PreRecordedMessage']
        parent = await self._server.add_folder('Paging')
        pel = await self._create_paging_element(parent)
        identifier = 6100
        for x in config:
            if config[x] != '0':
                if x not in pel.Zones:
                    el = await self._create_zone(identifier, x, config[x], parent)
                    pel.Zones[x] = el
                    identifier += 1
                else:
                    self._logger.error(f'Paging Zone {x} is exist in Dictionary')
        for y in config2:
            if config2[y] != '0':
                index = int(y)
                [title, filename] = get_pre_record_filename(config2[y])
                pel.PreRecordedMessages[index] = OpcUaPreRecordedMessage(index, title, filename)
        return pel

    async def _create_calling_element(self, parent: Node) -> OpcUaCalling:
        pg = OpcUaCalling()
        pg.Call_PreRecord_Message = await self._server.add(7000, parent, 'Call-PreRecord-Message', False,
                                                           VariantType.Boolean,
                                                           True)
        pg.Call_PreRecord_Message_No = await self._server.add(7001, parent, 'Call-PreRecord-Message-No', 1,
                                                              VariantType.Int16, True)
        pg.Call_PreRecord_Message_Message = await self._server.add(7002, parent, 'Call-PreRecord-Message-Message',
                                                                   'Message', VariantType.String, True)
        pg.Call_PreRecord_Message_Status = await self._server.add(7003, parent, 'Call-PreRecord-Message-Status', False,
                                                                  VariantType.Boolean, True)
        pg.Call_Group_Calling = await self._server.add(7010, parent, 'Call-Group-Calling', False, VariantType.Boolean,
                                                       True)
        pg.Call_Group_Calling_Group_No = await self._server.add(7011, parent, 'Call-Group-Calling-Group-No', 1,
                                                                VariantType.Int16, True)
        pg.Call_Group_Calling_Status = await self._server.add(7012, parent, 'Call-Group-Calling-Status', False,
                                                              VariantType.Boolean, True)
        return pg

    async def get_calling(self) -> OpcUaCalling:
        # config = self._config['Calling']
        config2 = self._config['Announcements']
        parent = await self._server.add_folder('Calling')
        pel = await self._create_calling_element(parent)
        for y in config2:
            if config2[y] != '0':
                index = int(y)
                [title, filename] = get_pre_record_filename(config2[y])
                pel.PreRecordedMessages[index] = OpcUaPreRecordedMessage(index, title, filename)
        return pel

    async def _check_group_status(self, el: OpcUaElementGroupStatus, parent: Node, group: str):
        if group not in el.Status_Group:
            self._logger.info('Group %s not exist. Create group %s node', group, group)
            node = await self._server.add(el.Identifier, parent, f'groupST{group}', 0, VariantType.Byte)
            el.add_group(group, node)

    async def _create_element_status(self, extension: str, config: str, status: OpcUaElementGroupStatus, parent: Node):
        (group, index) = get_status_group_index(config)
        if group != '-':
            await self._check_group_status(status, parent, group)
            self._logger.info('Add Extension %s to Group %s with index %s', extension, group, index)
            status.add(extension, group, index)

    async def get_elements_status_group(self) -> OpcUaElementGroupStatus:
        config = self._config['Extensions Status Group']
        parent = await self._server.add_folder('GroupStatus')
        status = OpcUaElementGroupStatus()
        for x in config:
            if config[x] != '0':
                await self._create_element_status(x, config[x], status, parent)
        return status
