import configparser
import logging

from typing import Dict
from asyncua import ua
from OpcServer.JaguarOpcUaServer import JaguarOpcUaServer
from OpcuaBase.OpcUaElement import OpcUaElement


class OpcElementFactory:

    def __init__(self, server: JaguarOpcUaServer):
        self._logger = logging.getLogger('Jaguar-ElementFactory')
        self._config = configparser.ConfigParser()
        self._config.optionxform = str
        self._config.read('Monitor.conf')
        self._server = server

    async def get_elements(self) -> Dict[str, OpcUaElement]:
        elements: Dict[str, OpcUaElement] = {}
        config = self._config['Extension']
        for x in config:
            if config[x] != '0':
                el = await self.create_new_element(x, config[x])
                elements[x] = el
        return elements

    async def create_new_element(self, ext, location) -> OpcUaElement:
        el = OpcUaElement(ext)
        node_id = int(ext) * 10
        el.Main = await self._server.add_folder(f'{location}-TEL-{ext}')
        el.Status = await self._server.add(node_id + 1, el.Main, f'{location}-TEL-{ext}-ST', 1, ua.VariantType.Byte)
        el.Call = await self._server.add(node_id + 2, el.Main, f'{location}-TEL-{ext}-CALL', 0, ua.VariantType.Int16)
        el.Confirm = await self._server.add(node_id + 3, el.Main, f'{location}-TEL-{ext}-CONFIRM', 0,
                                            ua.VariantType.Boolean)
        el.Transfer = await self._server.add(node_id + 4, el.Main, f'{location}-TEL-{ext}-TRANSFER', '0',
                                             ua.VariantType.String)
        el.PickUP = await self._server.add(node_id + 5, el.Main, f'{location}-TEL-{ext}-PICKUP', 0,
                                           ua.VariantType.Boolean)
        return el
