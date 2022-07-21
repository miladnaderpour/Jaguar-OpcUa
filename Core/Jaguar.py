import asyncio
import logging
from typing import Dict

from asyncua import ua, Node
from asyncua.common import subscription
from asyncua.ua import DataChangeNotification, VariantType

from OpcServer.JaguarOpcUaServer import JaguarOpcUaServer
from OpcuaBase import OpcUaElementType
from OpcuaBase.OpcElementFactory import OpcElementFactory
from OpcuaBase.OpcUaElement import OpcUaElement
from OpcuaBase.OpcUaPaging import OpcUaPaging
from OpcuaBase.OpcUaParameter import OpcUaParameter
from OpcuaBase.OpcUaSubcription import OpcUaSubscriptionHandler
from Voice.ExtensionStatus import ExtensionStatus
from Voice.SoftSwitchServer import SoftSwitchServer


def get_element_name(label: str) -> [str, str]:
    idx = label.rindex('-')
    if idx < len(label):
        return [label[0:idx], label[idx + 1:]]
    return label


class Jaguar:

    def __init__(self):
        self.loop = None
        self._logger = logging.getLogger('Jaguar')
        self._opcUaServer = JaguarOpcUaServer()
        self._softSwitchServer = SoftSwitchServer()
        self.elements: Dict[str, OpcUaElement]
        self.elements_subscription: subscription
        self.elements_subscription_handler: OpcUaSubscriptionHandler
        self.parameters: Dict[str, OpcUaParameter]
        self.parameters_subscription: subscription
        self.parameters_subscription_handler: OpcUaSubscriptionHandler
        self.semaphore = asyncio.Semaphore(2)
        self.paging: OpcUaPaging
        self.paging_subscription: subscription
        self.paging_subscription_handler: OpcUaSubscriptionHandler
        self.paging_zone_subscription: subscription
        self.paging_zone_subscription_handler: OpcUaSubscriptionHandler

    async def _init_elements(self):
        self._logger.info('create opcua elements')
        factory = OpcElementFactory(self._opcUaServer)
        self.elements = await factory.get_elements()
        self._logger.info('opcua elements created')
        self._logger.info('create opcua parameters')
        self.parameters = await factory.get_parameters()
        self._logger.info('create opcua paging elements')
        self.paging = await factory.get_paging()

    async def _create_subscriptions(self):

        self._logger.info('create event subscriptions ...')
        self.elements_subscription_handler = OpcUaSubscriptionHandler()
        self.elements_subscription = await self._opcUaServer \
            .create_data_subscription(self.elements_subscription_handler)

        self._logger.info('create Paging subscriptions ...')
        self.paging_subscription_handler = OpcUaSubscriptionHandler()
        self.paging_subscription = await self._opcUaServer \
            .create_data_subscription(self.paging_subscription_handler)

        self._logger.info('create Parameters subscriptions ...')
        self.parameters_subscription_handler = OpcUaSubscriptionHandler()
        self.parameters_subscription = await self._opcUaServer \
            .create_data_subscription(self.parameters_subscription_handler)

        self._logger.info('create paging zone subscriptions ...')
        self.paging_zone_subscription_handler = OpcUaSubscriptionHandler()
        self.paging_zone_subscription = await self._opcUaServer \
            .create_data_subscription(self.paging_zone_subscription_handler)

    async def _init_subscription(self):

        for el in self.elements:
            await self.elements_subscription.subscribe_data_change(self.elements[el].get_nodes())
        self._logger.info('Wait to Subscription Completed')

        await asyncio.sleep(2)

        await self._init_paging_subscription()

        await asyncio.sleep(2)

        await self._init_parameters_subscription()

        await asyncio.sleep(2)

        await self._bind_dispatch_callbacks()

    async def _init_paging_subscription(self):

        await self.paging_subscription.subscribe_data_change(self.paging.get_nodes())
        await self.paging_zone_subscription.subscribe_data_change(self.paging.get_zones())

    async def _init_parameters_subscription(self):

        for pr in self.parameters:
            await self.parameters_subscription.subscribe_data_change(self.parameters[pr].Value)

    async def on_element_data_changed(self, node: Node, val, data: DataChangeNotification):
        bname = await node.read_browse_name()
        node_name = str(bname.Name)
        [element, item] = get_element_name(node_name)
        self._logger.info('Element %s  %s data is changed to %s', element, item, val)
        await self._handle_element_change(element, item, node, val)

    async def on_paging_data_changed(self, node: Node, val, data: DataChangeNotification):
        bname = await node.read_browse_name()
        self._logger.info('Paging %s changed ')
        match bname.Name:
            case 'Paging-Live':
                if val:
                    await self._handle_paging_live(node, val)
            case 'Paging-Live-Test':
                if val:
                    await self._handle_paging_live_test(node, val)
            case 'Broadcasting_Message':
                await self._handle_paging_message_broadcasting(node, val)
            case 'Semiautomatic_Paging':
                await self._handle_paging_semiautomatic(node, val)

    async def on_parameter_data_changed(self, node: Node, val, data: DataChangeNotification):
        bname = await node.read_browse_name()
        self._logger.info('Parameter %s changed to %s ', bname.Name, val)
        await self._handle_parameter_change(bname.Name, node, val)

    async def on_paging_zone_selection_changed(self, node: Node, val, data: DataChangeNotification):
        bname = await node.read_browse_name()
        name = bname.Name
        self._logger.info('Paging Zone %s changed to %s', name, val)
        if name in self.paging.Zones:
            zone = self.paging.Zones[name]
            zone.Active = val
        self._logger.info('Zone %s Active is  %s', name, self.paging.Zones[name].Active)

    async def _bind_dispatch_callbacks(self):
        self._logger.info('Bind Subscription Callback Methods')
        self.elements_subscription_handler.on_data_changed(self.on_element_data_changed)
        self.paging_subscription_handler.on_data_changed(self.on_paging_data_changed)
        self.parameters_subscription_handler.on_data_changed(self.on_parameter_data_changed)
        self.paging_zone_subscription_handler.on_data_changed(self.on_paging_zone_selection_changed)

    async def _init_opcua(self):
        self._logger.info('init OPCUA server...')
        await self._opcUaServer.init_server()
        await self._init_elements()
        await self._create_subscriptions()
        self._logger.info('Wait For OPCUA server to Warmup')
        for i in range(1, 5):
            self._logger.info('progress %d ...', i * 20)
            await asyncio.sleep(1)
        await self._init_subscription()

    async def _init_softswitch(self):
        self._logger.info('init soft switch connector...')
        self._softSwitchServer.init_server()

    async def _change_element_status(self, ext, value, chanel):
        await self.semaphore.acquire()
        el = next((x for x in self.elements if self.elements[x].Extension == ext), None)
        if el is not None:
            self._logger.info('change Element %s value to %s (Chanel ID: %s)' % (self.elements[el].Name, value,
                                                                                 chanel))
            await self.elements[el].Status.set_value(value, ua.VariantType.Byte)
            self.elements[el].chan = chanel
        self.semaphore.release()
        return False

    async def _change_paging_status(self, event: str, num: str, channel: str):

        match event:
            case 'Start':
                await self.paging.Status.set_value('Paging', VariantType.String)
                await self.paging.Status_Code.set_value(2, VariantType.Byte)
            case 'End':
                await self.paging.Active_Channels.set_value(0, VariantType.Int16)
                await self.paging.Status.set_value('Ready...', VariantType.String)
                await self.paging.Status_Code.set_value(1, VariantType.Byte)
            case 'Join':
                await self.paging.Active_Channels.set_value(int(num), VariantType.Int16)
            case 'Leave':
                await self.paging.Active_Channels.set_value(int(num), VariantType.Int16)

    async def extension_status_changed(self, channel, status: ExtensionStatus, chanel):
        self._logger.info('%s state changed to : %s' % (channel, str(status)))
        await self._change_element_status(channel, status.value, chanel)

    async def paging_status_changed(self, event: str, num: str, channel: str):
        self._logger.info('paging state changed to : %s  num of channels=%s', event, num)
        await self._change_paging_status(event, num, channel)

    async def _handle_data_change_call(self, extension: str, node: Node):
        self._logger.info('Request for call origination to station %s', extension)
        await self._softSwitchServer.originate(extension)
        await node.set_value(0, VariantType.Int16)

    async def _handle_data_change_transfer(self, el: OpcUaElement, node: Node):
        self._logger.info('Request for call transfer from station %s', el.chan)
        transfer = await el.Transfer.get_value()
        self._logger.info('Transfer to station %s', transfer)
        await self._softSwitchServer.redirect(el.chan, transfer)
        await node.set_value(False, ua.VariantType.Boolean)

    async def _handle_element_change(self, name: str, item: str, node: Node, val):
        self._logger.info('Processing data changed event for %s element %s', name, item)
        # await self.semaphore.acquire()
        if name in self.elements:
            self._logger.info('Element has found (%s)', name)
            match item:
                case 'CALL':
                    if val == 1:
                        self._logger.info('Try Calling to Station %s', name)
                        await self._handle_data_change_call(self.elements[name].Extension, node)
                case 'CONFIRM':
                    if val:
                        self._logger.info('Try Transferring Call %s -> %s %s', name, type(val), val)
                        await self._handle_data_change_transfer(self.elements[name], node)
        # self.semaphore.release()

    async def _handle_parameter_change(self, name: str, node: Node, val):
        self._logger.info('Process data for Parameter %s and value %s', name, val)
        if name in self.parameters:
            self._logger.info('Parameter has found (%s)', name)
            self._logger.info('Change parameter value to %s', val)
            await self._softSwitchServer.setvar(name, val)

    def _get_active_zones_extensions(self):
        ext = []
        for z in self.paging.Zones:
            if self.paging.Zones[z].Active:
                for zs in self.paging.Zones[z].Elements:
                    if zs in self.elements and zs not in ext:
                        ext.append(self.elements[zs].Extension)
        self._logger.info('Create selected extensions array : %s', ext)
        return ext

    def _get_master_operator(self):
        for q in self.elements:
            if self.elements[q].Zone == 'MST':
                return self.elements[q].Extension
        return None

    async def _start_paging_live(self):
        self._logger.info('Request for Live paging...')
        mst = self._get_master_operator()
        if mst is None:
            self._logger.info('Master not found !')
            return
        self._logger.info('Master Extension is %s', mst)
        ext = self._get_active_zones_extensions()
        await self._softSwitchServer.paging_live(ext)
        await self._softSwitchServer.paging_live_master(mst)
        await self.paging.Live_Status.set_value(True, VariantType.Boolean)
        await self.paging.Status.set_value('Live', VariantType.String)

    async def _stop_paging_live(self):
        self._logger.info('Request for stopping Live paging...')
        await self._softSwitchServer.paging_stop_live()
        await self.paging.Live_Status.set_value(False, VariantType.Boolean)
        await self.paging.Status.set_value('Ready', VariantType.String)

    async def _handle_paging_live(self, node: Node, val):
        if val:
            await self._start_paging_live()
        else:
            await self._stop_paging_live()

    async def _handle_paging_live_test(self, node: Node, val):
        self._logger.info('Request for Test Live paging...')
        await self._softSwitchServer.paging_live_test()
        await node.set_value(False, VariantType.Boolean)

    async def _handle_paging_message_broadcasting(self, node: Node, val):
        self._logger.info('Request for message broadcasting...')
        await node.set_value(False, VariantType.Boolean)
        await asyncio.sleep(2)

    async def _handle_paging_semiautomatic(self, node: Node, val):
        self._logger.info('request for start semi-automatic paging...')
        await node.set_value(False, VariantType.Boolean)
        await asyncio.sleep(2)

    async def _init_events(self):
        self._softSwitchServer.on_extension_status_changed(self.extension_status_changed)
        self._softSwitchServer.on_conference_status_changed(self.paging_status_changed)

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
