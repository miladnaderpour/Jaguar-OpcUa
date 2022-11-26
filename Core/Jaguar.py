import asyncio
import datetime
import logging
from typing import Dict, List

from asyncua import ua, Node
from asyncua.common import subscription
from asyncua.ua import DataChangeNotification, VariantType

from Core.WebSocketServer import WebSocketServer
from OpcServer.JaguarOpcUaServer import JaguarOpcUaServer
from OpcuaBase.OpcElementFactory import OpcElementFactory
from OpcuaBase.OpcUaCalling import OpcUaCalling
from OpcuaBase.OpcUaElement import OpcUaElement
from OpcuaBase.OpcUaElementGroupStatus import OpcUaElementGroupStatus
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
        self._socketServer = WebSocketServer()
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
        self.elements_status_group: OpcUaElementGroupStatus
        self.calling: OpcUaCalling
        self.calling_subscription: subscription
        self.calling_subscription_handler: OpcUaSubscriptionHandler

    async def _init_elements(self):
        self._logger.info('create opcua elements')
        factory = OpcElementFactory(self._opcUaServer)
        self.elements = await factory.get_elements()
        self._logger.info('opcua elements created')
        self._logger.info('create opcua parameters')
        self.parameters = await factory.get_parameters()
        self._logger.info('create opcua paging elements')
        self.paging = await factory.get_paging()
        self._logger.info('create opcua calling elements')
        self.calling = await factory.get_calling()
        self._logger.info('create opcua status groups')
        self.elements_status_group = await factory.get_elements_status_group()

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

        self._logger.info('Create Calling subscriptions ...')
        self.calling_subscription_handler = OpcUaSubscriptionHandler()
        self.calling_subscription = await self._opcUaServer.create_data_subscription(self.calling_subscription_handler)

    async def _init_subscription(self):

        for el in self.elements:
            await self.elements_subscription.subscribe_data_change(self.elements[el].get_nodes())
        self._logger.info('Wait to Subscription Completed')

        await asyncio.sleep(2)

        await self._init_paging_subscription()

        await asyncio.sleep(2)

        await self._init_calling_subscription()

        await asyncio.sleep(2)

        await self._init_parameters_subscription()

        await asyncio.sleep(2)

        await self._bind_dispatch_callbacks()

    async def _init_paging_subscription(self):

        await self.paging_subscription.subscribe_data_change(self.paging.get_nodes())
        await self.paging_zone_subscription.subscribe_data_change(self.paging.get_zones())

    async def _init_calling_subscription(self):

        await self.calling_subscription.subscribe_data_change(self.calling.get_nodes())

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
        self._logger.info('Paging %s changed (value=%s)', bname.Name, val)
        match bname.Name:
            case 'Paging-Live':
                await self._handle_paging_live(node, val)
            case 'Paging-Live-Test':
                if val:
                    await self._handle_paging_live_test(node, val)
            case 'Broadcasting-Message':
                await self._handle_paging_message_broadcasting(node, val)
            case 'Broadcasting-Message-No':
                await self._change_paging_change_pre_record_message()
            case 'Semiautomatic-Paging':
                await self._handle_paging_semiautomatic(node, val)
            case 'Automatic-Paging':
                await self._handle_paging_automatic(node, val)
            case 'Automatic-Paging-Pause':
                await self._handle_paging_automatic_Pause(node, val)

    async def on_calling_data_changed(self, node: Node, val, data: DataChangeNotification):
        bname = await node.read_browse_name()
        self._logger.info('Calling %s changed (value=%s)', bname.Name, val)
        match bname.Name:
            case 'Call-PreRecord-Message':
                await self._handle_calling_change(val)
            case 'Call-PreRecord-Message-No':
                await self._handle_calling_message_change()
            case 'Call-CallGroup-Calling':
                await self._handle_calling_call_group_changed(val)
            case 'Call-CallGroup-Reset':
                await self._handle_calling_call_group_reset_changed(val)

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
        self.calling_subscription_handler.on_data_changed(self.on_calling_data_changed)
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

    async def _change_element_group_status(self, ext, value):
        match value:
            case 2:
                await self.elements_status_group.set_extension_status(ext, True)
            case 4:
                await self.elements_status_group.set_extension_status(ext, True)
            case _:
                await self.elements_status_group.set_extension_status(ext, False)

    async def _change_element_status(self, ext, value, chanel):
        await self.semaphore.acquire()
        el = next((x for x in self.elements if self.elements[x].Extension == ext), None)
        if el is not None:
            self._logger.info('change Element %s value to %s (Chanel ID: %s)' % (self.elements[el].Name, value,
                                                                                 chanel))
            await self.elements[el].Status.set_value(value, ua.VariantType.Byte)
            await self._change_element_group_status(ext, value)
            self.elements[el].chan = chanel
        self.semaphore.release()
        return False

    async def _change_paging_status(self, event: str, num: str, conference: str, channel: str):

        match event:
            case 'Start':
                self._logger.info('Paging Group %s Started - Num:%s , Channel:%s', conference, num, channel)
                await self.paging.update_status()
            case 'End':
                self._logger.info('Paging Group %s Finished - Num:%s , Channel:%s', conference, num, channel)
                await self.paging.Active_Channels.set_value(0, VariantType.Int16)
                await self.paging.reset_new_status()
                await self.paging.update_status()
            case 'Join':
                self._logger.info('%s Joined To Paging Group %s - Num:%s , ', channel, conference, num)
                await self.paging.Active_Channels.set_value(int(num), VariantType.Int16)
            case 'Leave':
                self._logger.info('%s Leaved Paging Group %s - Num:%s', channel, conference, num)
                await self.paging.Active_Channels.set_value(int(num), VariantType.Int16)
                if channel == 'Paging-autoapp':
                    self._logger.info('Application Channel %s Finished', channel)
                    asyncio.create_task(self.broadcast_automatic_broadcast_message(int(conference)))
                elif channel == 'Paging-app':
                    self._logger.info('Application Channel %s Finished', channel)
                    asyncio.create_task(self.broadcast_broadcast_message_finished())

    async def extension_status_changed(self, channel, status: ExtensionStatus, chanel):
        self._logger.info('%s state changed to : %s', channel, str(status))
        await self._change_element_status(channel, status.value, chanel)

    async def paging_status_changed(self, event: str, num: str, conference: str, channel: str):
        self._logger.info('paging state changed to : %s  num of channels=%s', event, num)
        await self._change_paging_status(event, num, conference, channel)

    async def queue_caller_status_changed(self, caller: str, channel: str, position: str, status):
        self._logger.info('Queue Caller %s state changed to : %s --- Channel %s Position: %s', caller, str(status),
                          channel, position)
        await self._change_element_status(caller, status.value, channel)

    async def _handle_data_change_call(self, extension: str, node: Node):
        self._logger.info('Request for call origination to station %s', extension)
        await self._softSwitchServer.originate(extension)
        await node.set_value(False, VariantType.Boolean)

    async def _handle_data_change_transfer(self, el: OpcUaElement, node: Node):
        self._logger.info('Request for call transfer from station %s', el.chan)
        transfer = await el.Transfer.get_value()
        self._logger.info('Transfer to station %s', transfer)
        await self._softSwitchServer.redirect(el.chan, transfer)
        await node.set_value(False, ua.VariantType.Boolean)

    async def _handle_data_change_call_group(self, el: OpcUaElement, node: Node):
        status = await node.get_value()
        self._logger.info('Change call group  for station %s is %s', el.Name, status)
        await el.CallGroupStatus.set_value(status, VariantType.Boolean)
        el.CallGroupSelected = status

    async def _handle_data_change_call_pickup(self, el: OpcUaElement, node: Node):
        status = await node.get_value()
        self._logger.info('Pick UP station %s Call %s', el.Name, status)
        if status:
            mst = self._get_master_operator()
            self._logger.info('Get Master Operator ((%s))', mst)
            await self._softSwitchServer.pickup(el.chan, mst)
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
                case 'PICKUP':
                    if val:
                        self._logger.info('Try PICKUP Station %s CALL', name)
                        await self._handle_data_change_call_pickup(self.elements[name], node)
                case 'CallGroup':
                    self._logger.info('Set CallGroup Station %s', name)
                    await self._handle_data_change_call_group(self.elements[name], node)
        # self.semaphore.release()

    async def _handle_parameter_change(self, name: str, node: Node, val):
        self._logger.info('Process data for Parameter %s and value %s', name, val)
        if name in self.parameters:
            self._logger.info('Parameter has found (%s)', name)
            self._logger.info('Change parameter value to %s', val)
            await self._softSwitchServer.setvar(name, val)

    async def _handle_calling_change(self, val):
        self._logger.info('Calling announcement changed!')
        await self.calling.set_announcement(val)
        if val:
            await self._softSwitchServer.setvar('Stations_Pre_Recorded_Message_ON', 'True')
            await self.calling.Call_PreRecord_Message_Status.set_value(True, VariantType.Boolean)
        else:
            await self._softSwitchServer.setvar('Stations_Pre_Recorded_Message_ON', 'False')
            await self.calling.Call_PreRecord_Message_Status.set_value(False, VariantType.Boolean)

    async def _handle_calling_message_change(self, ):
        self._logger.info('Calling announcement changed!')
        await self.calling.set_announcement_message()
        await self._softSwitchServer.setvar('Stations_Pre_Recorded_Message', self.calling.Call_APP_Message_FileName)

    def _get_active_call_group_extensions(self):
        ext = []
        names = []
        for z in self.elements:
            if self.elements[z].CallGroupSelected:
                ext.append(self.elements[z])
                names.append(self.elements[z].Name)
        self._logger.info('Create selected extensions array : %s', names)
        return ext

    async def _handle_calling_call_group_changed(self, val):
        self._logger.info('Calling Call Group changed!')
        ext = self._get_active_call_group_extensions()
        names = []
        for n in ext:
            names.append(n.Extension)
        if val:
            self._logger.info('Calling Call Group changed to %s', val)
            self._logger.info('selected extensions : %s', names)
            await self._softSwitchServer.callGroup(names)
            await self.calling.Call_CallGroup_Status.set_value(True, VariantType.Boolean)
        else:
            self._logger.info('Calling Call Group changed to %s', val)
            self._logger.info('selected extensions : %s', names)
            await self.calling.Call_CallGroup_Status.set_value(False, VariantType.Boolean)

    async def _handle_calling_call_group_reset_changed(self, val):
        self._logger.info('Calling Call Group Reset!')
        ext = self._get_active_call_group_extensions()
        if val:
            self._logger.info('Calling Reset Call Group changed to %s', val)
            await self.calling.Call_CallGroup_Reset.set_value(False, VariantType.Boolean)
            for z in ext:
                z.CallGroupSelected = False
                await z.CallGroup.set_value(False, VariantType.Boolean)
                self._logger.info('Calling Reset Ext: %s', z.Name)

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

    async def broadcast_manual_stop_other_modes(self):
        self._logger.info('Stop Other broadcasting Modes')
        if self.paging.Paging_APP_Semi_Automatic_Status:
            await self.broadcast_semiauto_stop()
            await asyncio.sleep(2)
        if self.paging.Paging_APP_Automatic_Status:
            await self.broadcast_automatic_pause(True)
            await asyncio.sleep(2)

    async def broadcast_live_start(self):
        self._logger.info('Request for Live paging...')
        self.paging.Paging_APP_Live_New_Status = True
        await self.broadcast_manual_stop_other_modes()
        mst = self._get_master_operator()
        if mst is None:
            self._logger.info('Master not found !')
            return
        self._logger.info('Master Extension is %s', mst)
        ext = self._get_active_zones_extensions()
        await self._softSwitchServer.paging_activate_pager(ext, 999)
        await self._softSwitchServer.paging_active_master(mst, 999)

    async def broadcast_live_stop(self):
        self._logger.info('Request for stopping Live paging...')
        self.paging.Paging_APP_Live_New_Status = False
        await self._softSwitchServer.paging_deactivate_pager(999)
        if self.paging.Paging_APP_Automatic_Status:
            await self.broadcast_automatic_pause(False)

    async def broadcast_broadcast_message(self, is_admin: bool = False):
        filename = self.paging.Paging_APP_Broadcast_FileName
        self._logger.info(f'paging file: {filename}')
        await asyncio.sleep(1)
        await self._softSwitchServer.paging_broadcast_message(999, filename, is_admin)

    async def broadcast_broadcast_message_finished(self):
        if self.paging.Paging_APP_Broadcast_Status:
            await self.broadcast_manual_clearing()
        else:
            await self.broadcast_semiauto_clearing()

    async def broadcast_manual_broadcasting_on_live(self):
        self._logger.info('Request for starting message broadcasting on live...')
        await self.broadcast_broadcast_message()

    async def broadcast_manual_clearing(self):
        self._logger.info('Manual broadcasting - Clearing')
        self.paging.Paging_APP_Broadcast_New_Status = False
        if not self.paging.Paging_APP_Live_Status:
            await self._softSwitchServer.paging_deactivate_pager(999)

    async def broadcast_manual_start(self):
        self._logger.info('Request for starting message broadcasting...')
        self._logger.info('message broadcasting - Live Status:%s', self.paging.Paging_APP_Live_Status)
        self.paging.Paging_APP_Broadcast_New_Status = True
        if self.paging.Paging_APP_Live_Status:
            await self.broadcast_manual_broadcasting_on_live()
            return
        await self.broadcast_manual_stop_other_modes()
        mst = self._get_master_operator()
        ext = self._get_active_zones_extensions()
        await self._softSwitchServer.paging_activate_pager(ext, 999)
        await self._softSwitchServer.paging_activate_pager([mst], 999)
        await self.broadcast_broadcast_message(True)

    async def broadcast_manual_stop(self):
        self._logger.info('Request for stopping message broadcasting...')
        self.paging.Paging_APP_Broadcast_New_Status = False
        if not self.paging.Paging_APP_Live_Status:
            await self._softSwitchServer.paging_deactivate_pager(999)

    async def _change_paging_change_pre_record_message(self):
        self._logger.info('Changing Pre recorded message!')
        await self.paging.set_pre_recorded_message()

    async def broadcast_semiauto_clearing(self):
        q = self.paging.Semiautomatic_Paging_Remain - 1
        self.paging.Semiautomatic_Paging_Remain = q
        await self.paging.Semiautomatic_Paging_Repetition_Status.set_value(str(q), VariantType.String)
        if self.paging.Semiautomatic_Paging_Keep_Alive and self.paging.Semiautomatic_Paging_Remain > 0:
            self._logger.info('SemiAuto broadcasting - Broadcast Message - No %s',
                              self.paging.Semiautomatic_Paging_Remain)
            self._logger.info('SemiAuto broadcasting - Delay %ss', self.paging.Semiautomatic_Paging_Delay_Time)
            await asyncio.sleep(self.paging.Semiautomatic_Paging_Delay_Time)
            await self.broadcast_broadcast_message()
        else:
            self._logger.info('SemiAuto broadcasting - Clearing')
            self.paging.Paging_APP_Semi_Automatic_New_Status = False
            self.paging.Semiautomatic_Paging_Keep_Alive = False
            await self._softSwitchServer.paging_deactivate_pager(999)

    async def broadcast_semiauto_start(self):
        self._logger.info('Request for starting message Semi Auto broadcasting...')
        if not self.paging.Paging_APP_Automatic_Status and not self.paging.Paging_APP_Live_Status \
                and not self.paging.Paging_APP_Broadcast_Status:
            self.paging.Paging_APP_Semi_Automatic_New_Status = True
            c = await self.paging.Semiautomatic_Paging_No_Repetitions.get_value()
            d = await self.paging.Semiautomatic_Paging_Delay.get_value()
            self.paging.Semiautomatic_Paging_Remain = c
            self.paging.Semiautomatic_Paging_Delay_Time = d
            self.paging.Semiautomatic_Paging_Keep_Alive = True
            await self.paging.Semiautomatic_Paging_Repetition_Status.set_value(str(c), VariantType.String)
            mst = self._get_master_operator()
            ext = self._get_active_zones_extensions()
            await self._softSwitchServer.paging_activate_pager(ext, 999)
            await self._softSwitchServer.paging_activate_pager([mst], 999)
            filename = self.paging.Paging_APP_Broadcast_FileName
            self._logger.info('Start Semi Auto broadcasting message %s for %s times each %ss', filename, c, d)
            asyncio.create_task(self.broadcast_broadcast_message(False))
        else:
            await self.paging.Semiautomatic_Paging.set_value(False, VariantType.Boolean)

    async def broadcast_semiauto_stop(self):
        if not self.paging.Paging_APP_Automatic_Status and not self.paging.Paging_APP_Live_Status \
                and not self.paging.Paging_APP_Broadcast_Status:
            self._logger.info('Request for stopping message Semi Auto broadcasting...')
            self.paging.Paging_APP_Semi_Automatic_New_Status = False
            self.paging.Semiautomatic_Paging_Keep_Alive = False
            await self._softSwitchServer.paging_deactivate_pager(999)

    async def broadcast_automatic_broadcast_message(self, grp: int):
        if self.paging.Automatic_Paging_Keep_Alive and not self.paging.Automatic_Paging_Pause:
            self._logger.info('Automatic broadcasting - Broadcast Message - Group %s', grp)
            msg = self.paging.Automatic_Paging_Messages[grp]
            self._logger.info('Message: %s - Filename: %s', msg.Title, msg.FileName)
            await self._softSwitchServer.paging_automatic_message(grp, msg.FileName)

    async def broadcast_automatic_get_active(self):
        self._logger.info('Get Active Pagers....')
        self.paging.Automatic_Paging_Active_Pagers = {}
        for c in self.paging.Automatic_Paging_Commands:
            g = await self.paging.Automatic_Paging_Commands[c].GetAutoMaticPagers()
            for p in g:
                m = await g[p].Message.get_value()
                if m not in self.paging.Automatic_Paging_Active_Pagers:
                    self._logger.info('New Group :: CMD:%s , Ext:%s - Msg:%s', c, g[p].Extension, m)
                    self.paging.Automatic_Paging_Active_Pagers[m] = [g[p].Extension]
                else:
                    self.paging.Automatic_Paging_Active_Pagers[m].append(g[p].Extension)
                    self._logger.info('Add Item :: CMD:%s , Ext:%s - Msg:%s', c, g[p].Extension, m)

    async def broadcast_automatic_activate_group_pagers(self, grp, members):
        self._logger.info('Automatic broadcasting For %s', grp)
        self._logger.info('Automatic broadcasting Members %s', members)
        await self._softSwitchServer.paging_activate_pager(members, grp)
        asyncio.create_task(self.broadcast_automatic_broadcast_message(grp))

    async def broadcast_automatic(self):
        self._logger.info('Automatic broadcasting Activating')
        grp_activated = {}
        while self.paging.Automatic_Paging_Keep_Alive and not self.paging.Automatic_Paging_Pause:
            await self.broadcast_automatic_get_active()
            for grp in self.paging.Automatic_Paging_Active_Pagers:
                self._logger.info(
                    'Activating Group:%s - Pagers:%s', grp, self.paging.Automatic_Paging_Active_Pagers[grp])
                grp_activated[grp] = grp
                asyncio.create_task(
                    self.broadcast_automatic_activate_group_pagers(
                        grp, self.paging.Automatic_Paging_Active_Pagers[grp]))
            while self.paging.Automatic_Paging_Keep_Alive and not self.paging.Automatic_Paging_Pause:
                self._logger.info('Keep Alive Automatic paging')
                await asyncio.sleep(2)
            for g in grp_activated:
                self._logger.info('Stop Automatic broadcasting For %s', g)
                await self._softSwitchServer.paging_deactivate_pager(g)
            while self.paging.Automatic_Paging_Keep_Alive and self.paging.Automatic_Paging_Pause:
                self._logger.info('Automatic paging - Pause')
                await asyncio.sleep(5)
        self._logger.info('Automatic broadcasting Deactivated')

    async def broadcast_automatic_start(self):
        self._logger.info('Starting Automatic broadcasting...')
        self.paging.Paging_APP_Automatic_New_Status = True
        self.paging.Automatic_Paging_Pause = False
        self.paging.Automatic_Paging_Keep_Alive = True
        await self.paging.Automatic_Paging_Status.set_value(True, VariantType.Boolean)
        self.paging.Automatic_Paging_Task = asyncio.create_task(self.broadcast_automatic())

    async def broadcast_automatic_stop(self):
        self._logger.info('Request for stopping message Automatic broadcasting...')
        self.paging.Paging_APP_Automatic_New_Status = False
        self.paging.Automatic_Paging_Keep_Alive = False
        await self.paging.Automatic_Paging_Status.set_value(False, VariantType.Boolean)
        self._logger.info(f'Stop Automatic broadcasting Finished')

    async def broadcast_automatic_pause(self, val: bool):
        if val and self.paging.Automatic_Paging_Keep_Alive:
            self._logger.info('Request for pausing Automatic broadcasting...')
            self.paging.Automatic_Paging_Pause = True
        elif self.paging.Automatic_Paging_Keep_Alive:
            self._logger.info('Request for resume Automatic broadcasting...')
            self.paging.Automatic_Paging_Pause = False
        else:
            self._logger.info(f'Automatic broadcasting is not alive')

    async def _handle_paging_live(self, node: Node, val):
        if val:
            await self.broadcast_live_start()
        else:
            await self.broadcast_live_stop()

    async def _handle_paging_live_test(self, node: Node, val):
        self._logger.info('Request for Test Live paging...')
        await self._softSwitchServer.paging_live_test()
        await node.set_value(False, VariantType.Boolean)

    async def _handle_paging_message_broadcasting(self, node: Node, val):
        if val:
            await self.broadcast_manual_start()
        else:
            await self.broadcast_manual_stop()

    async def _handle_paging_semiautomatic(self, node: Node, val):
        if val:
            self._logger.info('request for start semi-automatic paging...')
            await self.broadcast_semiauto_start()
        else:
            await self.broadcast_semiauto_stop()

    async def _handle_paging_automatic(self, node: Node, val):
        self._logger.info('automatic paging changed to %s', val)
        if val:
            await self.broadcast_automatic_start()
        else:
            await self.broadcast_automatic_stop()

    async def _handle_paging_automatic_Pause(self, node: Node, val):
        self._logger.info('automatic paging pause changed to %s', val)
        await self.broadcast_automatic_pause(val)

    async def _init_events(self):
        self._softSwitchServer.on_extension_status_changed(self.extension_status_changed)
        self._softSwitchServer.on_conference_status_changed(self.paging_status_changed)
        self._softSwitchServer.on_queue_caller_status_changed(self.queue_caller_status_changed)

    def _start_services(self):
        self._opcua_task = asyncio.create_task(self._opcUaServer.start())
        self._soft_switch_task = asyncio.create_task(self._softSwitchServer.start())
        self._socket_task = asyncio.create_task(self._socketServer.run())

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
        await self._socket_task
