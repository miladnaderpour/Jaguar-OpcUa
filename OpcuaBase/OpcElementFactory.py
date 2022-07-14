import configparser
import logging

from typing import Dict, Any
from asyncua import ua, Node
from asyncua.ua import VariantType

from OpcServer.JaguarOpcUaServer import JaguarOpcUaServer
from OpcuaBase.OpcUaElement import OpcUaElement
from OpcuaBase.OpcUaElementType import OpcUaElementType
from OpcuaBase.OpcUaParameter import OpcUaParameter


def get_location(config: str) -> [str, str, str]:
    sp = str(config).split(',')
    if len(sp) == 3:
        return [sp[0], sp[1], sp[2]]
    return [config, '', 1]


def get_parameter_configs(config: str) -> [Any, VariantType, int]:
    sp = str(config).split(',')
    print(f'sp ------------------> {sp[0]} -{sp[1]} -{sp[2]} ')
    if len(sp) == 3:
        match int(sp[1]):
            case 12:  # string variant type
                return [str(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case 1:  # Boolean variant type
                return [bool(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case 3:  # byte variant type
                return [bytes(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case 4:  # Int16 variant type
                return [bytes(sp[0]), VariantType(int(sp[1])), int(sp[2])]
            case _:
                return [config, VariantType.String, 0]
    return [config, VariantType.String]


class OpcElementFactory:
    Elements: Dict[str, OpcUaElement]
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
        self.Elements = {}
        self.Parameters = {}

    async def _create_element(self, parent, ext, prefix, element_type: OpcUaElementType, config) -> OpcUaElement:

        [location, zone, group] = get_location(config)
        el = OpcUaElement(ext, element_type, location, int(group), zone)
        identifier = int(ext) * 10

        el.Main = await parent.add_folder(self._server.idx, f'{location}-{prefix}-{ext}')

        el.Status = await self._server.add(identifier + 1, el.Main, f'{location}-TEL-{ext}-ST', 0,
                                           ua.VariantType.Byte)
        el.Call = await self._server.add(identifier + 2, el.Main, f'{location}-TEL-{ext}-CALL', 0,
                                         ua.VariantType.Int16)
        el.Confirm = await self._server.add(identifier + 3, el.Main, f'{location}-TEL-{ext}-CONFIRM', 0,
                                            ua.VariantType.Boolean)
        el.Transfer = await self._server.add(identifier + 4, el.Main, f'{location}-TEL-{ext}-TRANSFER', '',
                                             ua.VariantType.String)
        el.PickUP = await self._server.add(identifier + 5, el.Main, f'{location}-TEL-{ext}-PICKUP', 0,
                                           ua.VariantType.Boolean)
        el.Description = await self._server.add(identifier + 6, el.Main, f'{location}-TEL-{ext}-DES', 'Init',
                                                ua.VariantType.String)
        return el

    async def _create_elements(self, parent, config, prefix, element_type: OpcUaElementType):
        for x in config:
            if config[x] != '0':
                if x not in self.Elements:
                    el = await self._create_element(parent, x, prefix, element_type, config[x])
                    self.Elements[x] = el
                else:
                    self._logger.error('Element {x} is exist in Dictionary')

    async def _create_station_elements(self):
        config = self._config['Extension']
        parent = await self._server.add_folder('SOS')
        await self._create_elements(parent, config, 'TEL', OpcUaElementType.SOS)

    async def _create_pager_elements(self):
        config = self._config['Pagers']
        parent = await self._server.add_folder('Pagers')
        await self._create_elements(parent, config, 'PAG', OpcUaElementType.Pager)

    async def _create_operator_elements(self):
        config = self._config['Operator']
        parent = await self._server.add_folder('Operator')
        await self._create_elements(parent, config, 'MNG', OpcUaElementType.Pager)

    async def get_elements(self) -> Dict[str, OpcUaElement]:
        await self._create_station_elements()
        await self._create_pager_elements()
        await self._create_operator_elements()
        return self.Elements

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
