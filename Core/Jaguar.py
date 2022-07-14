import asyncio
import logging
from typing import Dict

from asyncua import ua, Node
from asyncua.ua import DataChangeNotification

from OpcServer.JaguarOpcUaServer import JaguarOpcUaServer
from OpcuaBase.OpcElementFactory import OpcElementFactory
from OpcuaBase.OpcUaElement import OpcUaElement
from OpcuaBase.OpcUaParameter import OpcUaParameter
from Voice.ExtensionStatus import ExtensionStatus
from Voice.SoftSwitchServer import SoftSwitchServer


class Jaguar:

    def __init__(self):
        self.loop = None
        self._logger = logging.getLogger('Jaguar')
        self._opcUaServer = JaguarOpcUaServer()
        self._softSwitchServer = SoftSwitchServer()
        self.elements: Dict[str, OpcUaElement]
        self.parameters: Dict[str, OpcUaParameter]
        self.semaphore = asyncio.Semaphore(2)

    async def _init_elements(self):
        self._logger.info('create opcua elements')
        factory = OpcElementFactory(self._opcUaServer)
        self.elements = await factory.get_elements()
        self._logger.info('opcua elements created')
        self._logger.info('create opcua parameters')
        self.parameters = await factory.get_parameters()

    async def _init_elements_subscription(self):
        self._logger.info('Subscribe elements events')
        for el in self.elements:
            await self._opcUaServer.Subscription.subscribe_data_change(self.elements[el].get_nodes())
        self._logger.info('Wait to Subscription Completed')
        await asyncio.sleep(2)
        for pr in self.parameters:
            await self._opcUaServer.Subscription.subscribe_data_change(self.parameters[pr].Value)
        await asyncio.sleep(2)
        self._create_data_subscription()

    def _create_data_subscription(self):
        self._logger.info('Create Subscription Handler')
        self._opcUaServer.on_data_changed(self.on_data_changed_dispatch)

    async def _init_opcua(self):
        self._logger.info('init OPCUA server...')
        await self._opcUaServer.init_server()
        await self._init_elements()
        self._logger.info('Wait For OPCUA server to Warmup')
        for i in range(1, 5):
            self._logger.info('progress %d ...', i * 20)
            await asyncio.sleep(1)
        await self._init_elements_subscription()

    async def _init_softswitch(self):
        self._logger.info('init soft switch connector...')
        self._softSwitchServer.init_server()

    async def _change_element_status(self, ext, value, chanel):
        await self.semaphore.acquire()
        if ext in self.elements:
            self._logger.info('change Element %s value to %s (Chanel ID: %s)' % (self.elements[ext].Name, value,
                                                                                 chanel))
            await self.elements[ext].Status.set_value(value, ua.VariantType.Byte)
            self.elements[ext].chan = chanel
        self.semaphore.release()
        return False

    async def extension_status_changed(self, channel, status: ExtensionStatus, chanel):
        self._logger.info('%s state changed to : %s' % (channel, str(status)))
        await self._change_element_status(channel, status.value, chanel)

    async def _handle_data_change_call(self, name: str, node: Node):
        self._logger.info('Request for call origination to station %s', name)
        await self._softSwitchServer.originate(name)
        await node.set_value(0, ua.VariantType.Int16)

    async def _handle_data_change_transfer(self, el: OpcUaElement, node: Node):
        self._logger.info('Request for call transfer from station %s', el.chan)
        transfer = await el.Transfer.get_value()
        self._logger.info('Transfer to station %s', transfer)
        await self._softSwitchServer.redirect(el.chan, transfer)
        await node.set_value(False, ua.VariantType.Boolean)

    async def _handle_data_change(self, name: str, el_type: str, node: Node, val):
        self._logger.info('Process data for element %s and vartype %s', name, el_type)
        # await self.semaphore.acquire()
        if name in self.elements:
            self._logger.info('Element has found (%s)', name)
            match el_type:
                case 'CALL':
                    if val == 1:
                        self._logger.info('Try Calling to Station %s', name)
                        await self._handle_data_change_call(name, node)
                case 'CONFIRM':
                    if val:
                        self._logger.info('Try Transferring Call %s -> %s %s', name, type(val), val)
                        await self._handle_data_change_transfer(self.elements[name], node)
        # self.semaphore.release()

    async def _handle_parameter_change(self, name: str, node: Node, val):
        self._logger.info('Process data for Parameter %s and value %s', name, val)
        # await self.semaphore.acquire()
        if name in self.parameters:
            self._logger.info('Parameter has found (%s)', name)
            self._logger.info('Change parameter value to %s', val)
            await self._softSwitchServer.setvar(name, val)
            # match el_type:
            #     case 'CALL':
            #         if val == 1:
            #             self._logger.info('Try Calling to Station %s', name)
            #             await self._handle_data_change_call(name, node)
            #     case 'CONFIRM':
            #         if val:
            #             self._logger.info('Try Transferring Call %s -> %s %s', name, type(val), val)
            #             await self._handle_data_change_transfer(self.elements[name], node)
        # self.semaphore.release()

    async def on_data_changed_dispatch(self, node: Node, val, data: DataChangeNotification):
        idf = node.nodeid.Identifier
        bname = await node.read_browse_name()
        parent = await node.get_parent()
        pname = await parent.read_browse_name()
        self._logger.info('Parent Name is %s', pname)
        if pname.Name == 'Parameters':
            self._logger.info('Data Changed Dispatch For Parameter %s', bname.Name)
            await self._handle_parameter_change(bname.Name, node, val)
        else:
            ar = str(bname.Name).split("-")
            self._logger.info('Data Changed Dispatch Node(%d) %s', idf, bname.Name)
            await self._handle_data_change(ar[2], ar[3], node, val)

    async def _init_events(self):
        self._softSwitchServer.on_extension_status_changed(self.extension_status_changed)

    def _start_services(self):
        self._opcua_task = asyncio.create_task(self._opcUaServer.start())
        self._soft_switch_task = asyncio.create_task(self._softSwitchServer.start())

    async def start(self):
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        self.loop = asyncio.get_event_loop()
        await self._init_opcua()
        await self._init_softswitch()
        self._start_services()
        await self._init_events()
        await self._soft_switch_task
        await self._opcua_task
