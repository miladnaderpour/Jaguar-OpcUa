import logging
from asyncio import Task
from typing import Dict, List

from asyncua import Node
from asyncua.ua import VariantType

from OpcuaBase.OpcUaPagingAutomatic import OpcUaPagingAutomaticCommand
from OpcuaBase.OpcUaPagingZone import OpcUaPagingZone
from OpcuaBase.OpcUaPreRecordedMessage import OpcUaPreRecordedMessage


class OpcUaPaging:
    Status: Node
    Status_Code: Node
    Active_Channels: Node

    Reset: Node

    Live: Node
    Live_Status: Node
    Live_Test: Node

    Broadcasting_Message: Node
    Broadcasting_Message_No: Node
    Broadcasting_Message_Status: Node
    Broadcasting_Message_Message: Node

    Semiautomatic_Paging: Node
    Semiautomatic_Paging_Status: Node
    Semiautomatic_Paging_No_Repetitions: Node
    Semiautomatic_Paging_Delay: Node
    Semiautomatic_Paging_Repetition_Status: Node
    Semiautomatic_Paging_Keep_Alive: bool
    Semiautomatic_Paging_Remain: int
    Semiautomatic_Paging_Delay_Time: int

    Automatic_Paging: Node
    Automatic_Paging_Status: Node
    Automatic_Paging_Pause: Node
    Automatic_Paging_Commands: Dict[str, OpcUaPagingAutomaticCommand]
    Automatic_Paging_Messages: Dict[int, OpcUaPreRecordedMessage]
    Automatic_Paging_Active_Pagers: Dict[int, List[str]]
    Automatic_Paging_Task: Task
    Automatic_Paging_Keep_Alive: bool
    Automatic_Paging_Pause: bool

    PreRecordedMessages: Dict[int, OpcUaPreRecordedMessage]

    Zones: Dict[str, OpcUaPagingZone]

    Paging_APP_Status: int = 1
    Paging_APP_General_Pager_Group: bool = False
    Paging_APP_Live_Status: bool = False
    Paging_APP_Broadcast_Status: bool = False
    Paging_APP_Semi_Automatic_Status: bool = False
    Paging_APP_Automatic_Status: bool = False

    Paging_APP_Live_Start_Request: bool = False
    Paging_APP_Live_Stop_Request: bool = False

    Paging_APP_Broadcast_Start_Request: bool = False
    Paging_APP_Broadcast_Stop_Request: bool = False

    Paging_APP_Semi_Automatic_Start_Request: bool = False
    Paging_APP_Semi_Automatic_Stop_Request: bool = False

    Paging_APP_Automatic_Start_Request: bool = False
    Paging_APP_Automatic_Stop_Request: bool = False

    Paging_APP_Broadcast_FileName: str = ''

    def __init__(self):
        self.Zones = {}
        self.PreRecordedMessages = {}
        self.Automatic_Paging_Commands = {}
        self.Automatic_Paging_Messages = {}
        self._logger = logging.getLogger('Jaguar-Paging')

    def get_nodes(self):
        return [self.Live,
                self.Live_Test,
                self.Broadcasting_Message,
                self.Semiautomatic_Paging,
                self.Broadcasting_Message_No,
                self.Automatic_Paging,
                self.Automatic_Paging_Pause]

    def get_zones(self):
        x = []
        for zone in self.Zones:
            x.append(self.Zones[zone].Node)
        return x

    def _reset_requests(self):
        self._logger.info('Reset Paging Requests')
        self.Paging_APP_Live_Start_Request = False
        self.Paging_APP_Live_Stop_Request = False
        self.Paging_APP_Broadcast_Start_Request = False
        self.Paging_APP_Broadcast_Stop_Request = False
        self.Paging_APP_Semi_Automatic_Start_Request = False
        self.Paging_APP_Semi_Automatic_Stop_Request = False
        self.log_status()

    async def update_status(self) -> bool:
        self._logger.info('Updating Status')
        self.log_status()
        if self.Paging_APP_Live_Start_Request or self.Paging_APP_Live_Stop_Request:
            self._logger.info('Updating Status - Live')
            await self._on_broadcast_live_mode_request()
        elif self.Paging_APP_Broadcast_Start_Request or self.Paging_APP_Broadcast_Stop_Request:
            self._logger.info('Updating Status - Manual')
            await self._on_broadcast_manual_mode_request()
        elif self.Paging_APP_Semi_Automatic_Start_Request or self.Paging_APP_Semi_Automatic_Stop_Request:
            self._logger.info('Updating Status - Semi-Auto')
            await self._on_broadcast_semi_automatic_mode_request()

        if self.Paging_APP_Automatic_Start_Request or self.Paging_APP_Automatic_Stop_Request:
            self._logger.info('Updating Status - Auto')
            await self._on_broadcast_automatic_mode_request()

        return True

    async def _on_broadcast_live_mode_request(self):
        if not self.Paging_APP_Live_Status and self.Paging_APP_Live_Start_Request:
            self._logger.info('Updating Paging Status to Live Broadcasting')
            await self._set_live_status(True)
            await self._set_broadcasting_status(False)
            await self._set_semi_automatic_status(False)
        elif self.Paging_APP_Live_Status and self.Paging_APP_Live_Stop_Request:
            await self._set_live_status(False)
        await self._update_paging_status()
        self._reset_requests()

    async def _on_broadcast_manual_mode_request(self):
        if not self.Paging_APP_Live_Status:
            if not self.Paging_APP_Broadcast_Status and self.Paging_APP_Broadcast_Start_Request:
                self._logger.info('Updating Paging Status to Manual Broadcasting Message')
                await self._set_broadcasting_status(True)
                await self._set_semi_automatic_status(False)
            elif self.Paging_APP_Broadcast_Status and self.Paging_APP_Broadcast_Stop_Request:
                await self._set_broadcasting_status(False)
        self._reset_requests()
        await self._update_paging_status()

    async def _on_broadcast_semi_automatic_mode_request(self):
        if not self.Paging_APP_Live_Status and not self.Paging_APP_Broadcast_Status:
            if not self.Paging_APP_Semi_Automatic_Status and self.Paging_APP_Semi_Automatic_Start_Request:
                self._logger.info('Updating Paging Status to Semi-Auto Broadcasting Message')
                await self._set_semi_automatic_status(True)
            elif self.Paging_APP_Semi_Automatic_Status and self.Paging_APP_Semi_Automatic_Stop_Request:
                await self._set_semi_automatic_status(False)
        await self._update_paging_status()
        self._reset_requests()

    async def _on_broadcast_automatic_mode_request(self):
        if not self.Paging_APP_Automatic_Status and self.Paging_APP_Automatic_Start_Request:
            self._logger.info('Updating Paging Status to Automatic Broadcasting Message')
            await self._set_automatic_status(True)
        elif self.Paging_APP_Automatic_Status and self.Paging_APP_Automatic_Stop_Request:
            await self._set_automatic_status(False)
        await self._update_paging_status()
        self.Paging_APP_Automatic_Start_Request = False
        self.Paging_APP_Automatic_Stop_Request = False

    async def _update_paging_status(self):
        if self.Paging_APP_Live_Status:
            await self._set_paging_status(2, 'Live Paging')
        elif self.Paging_APP_Broadcast_Status:
            await self._set_paging_status(3, 'Broadcasting Message')
        elif self.Paging_APP_Semi_Automatic_Status:
            await self._set_paging_status(4, 'Semi Automatic Broadcasting')
        elif self.Paging_APP_Automatic_Status:
            await self._set_paging_status(5, 'Automatic Broadcasting')
        else:
            await self._set_paging_status(1, 'Ready')

    async def _set_paging_status(self, status: int, msg: str):
        if status != self.Paging_APP_Status:
            self.Paging_APP_Status = status
            await self.Status.set_value(msg, VariantType.String)
            await self.Status_Code.set_value(status, VariantType.Byte)

    async def _set_live_status(self, status: bool):
        self._logger.info('Set Live Status - APP_Live_Status :%s Status:%s', self.Paging_APP_Live_Status, status)
        self.Paging_APP_Live_Status = status
        await self.Live_Status.set_value(status, VariantType.Boolean)
        await self.Live.set_value(status, VariantType.Boolean)
        self.Paging_APP_Live_Start_Request = False
        self.Paging_APP_Live_Stop_Request = False

    async def _set_broadcasting_status(self, status: bool):
        self._logger.info('Set Broadcast Status - APP_Broadcasting :%s Status:%s', self.Paging_APP_Broadcast_Status,
                          status)
        if self.Paging_APP_Broadcast_Status != status:
            self.Paging_APP_Broadcast_Status = status
            await self.Broadcasting_Message_Status.set_value(status, VariantType.Boolean)
            await self.Broadcasting_Message.set_value(status, VariantType.Boolean)

    async def _set_semi_automatic_status(self, status: bool):
        if self.Paging_APP_Semi_Automatic_Status != status:
            self.Paging_APP_Semi_Automatic_Status = status
            await self.Semiautomatic_Paging_Status.set_value(status, VariantType.Boolean)
            await self.Semiautomatic_Paging.set_value(status, VariantType.Boolean)

    async def _set_automatic_status(self, status: bool):
        self._logger.info('Set Automatic Paging Status - Paging_APP_Automatic_Status :%s Status:%s',
                          self.Paging_APP_Automatic_Status, status)
        if self.Paging_APP_Automatic_Status != status:
            self.Paging_APP_Automatic_Status = status
            await self.Automatic_Paging_Status.set_value(status, VariantType.Boolean)

    async def set_pre_recorded_message(self):
        mm = await self.Broadcasting_Message_No.get_value()
        if mm in self.PreRecordedMessages.keys():
            msg = self.PreRecordedMessages[mm]
            await self.Broadcasting_Message_Message.set_value(msg.Title, VariantType.String)
            self.Paging_APP_Broadcast_FileName = msg.FileName

    def log_status(self):
        self._logger.info('Paging_APP_Status = %s', self.Paging_APP_Status)
        self._logger.info('Live Broadcast Status = %s ---- Start = %s , Stop = %s', self.Paging_APP_Live_Status,
                          self.Paging_APP_Live_Start_Request, self.Paging_APP_Live_Stop_Request)
        self._logger.info('Manual Broadcast Status = %s ---- Start = %s , Stop = %s', self.Paging_APP_Broadcast_Status,
                          self.Paging_APP_Broadcast_Start_Request, self.Paging_APP_Broadcast_Stop_Request)
        self._logger.info('Semi-Automatic Broadcast Status = %s ---- Start = %s , Stop = %s',
                          self.Paging_APP_Semi_Automatic_Status, self.Paging_APP_Semi_Automatic_Start_Request,
                          self.Paging_APP_Semi_Automatic_Stop_Request)
        self._logger.info('Automatic Broadcast Status = %s ---- Start = %s , Stop = %s',
                          self.Paging_APP_Automatic_Status, self.Paging_APP_Automatic_Start_Request,
                          self.Paging_APP_Automatic_Stop_Request)
