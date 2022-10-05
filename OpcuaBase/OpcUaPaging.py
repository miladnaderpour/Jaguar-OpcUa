import logging
from typing import Dict

from asyncua import Node
from asyncua.ua import VariantType

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

    PreRecordedMessages: Dict[int, OpcUaPreRecordedMessage]

    Zones: Dict[str, OpcUaPagingZone]

    Paging_APP_Status: int = 1
    Paging_APP_Live_Status: bool = False
    Paging_APP_Broadcast_Status: bool = False
    Paging_APP_Semi_Automatic_Status: bool = False

    Paging_APP_Live_New_Status: bool = False
    Paging_APP_Broadcast_New_Status: bool = False
    Paging_APP_Semi_Automatic_New_Status: bool = False

    Paging_APP_Broadcast_FileName: str = ''

    def __init__(self):
        self.Zones = {}
        self.PreRecordedMessages = {}
        self._logger = logging.getLogger('Jaguar-Paging')

    def get_nodes(self):
        return [self.Live,
                self.Live_Test,
                self.Broadcasting_Message,
                self.Semiautomatic_Paging,
                self.Broadcasting_Message_No]

    def get_zones(self):
        x = []
        for zone in self.Zones:
            x.append(self.Zones[zone].Node)
        return x

    async def reset_new_status(self):
        self._logger.info('Reset Paging Status')
        self.Paging_APP_Live_New_Status = False
        self.Paging_APP_Broadcast_New_Status = False
        self.Paging_APP_Semi_Automatic_New_Status = False
        self.log_status()

    async def update_status(self) -> bool:
        self._logger.info('Updating Status')
        self.log_status()
        if self.Paging_APP_Live_New_Status:
            self._logger.info('Updating Paging Status to Live - Broadcast is %s', self.Paging_APP_Broadcast_Status)
            if not self.Paging_APP_Broadcast_Status:
                await self._set_paging_status(2, 'Live Paging')
                await self._set_broadcasting_status(False)
            else:
                await self._set_paging_status(2, 'Broadcasting Message (on Live Paging)')
                await self._set_broadcasting_status(True)
            await self._set_live_status(True)
            await self._set_semi_automatic_status(False)
            self.Paging_APP_Live_New_Status = False
            return True
        elif self.Paging_APP_Broadcast_New_Status:
            self._logger.info('Updating Paging Status to Broadcasting Message')
            await self._set_paging_status(2, 'Broadcasting Message')
            await self._set_live_status(False)
            await self._set_broadcasting_status(True)
            await self._set_semi_automatic_status(False)
            self.Paging_APP_Broadcast_New_Status = False
            return True
        elif self.Paging_APP_Semi_Automatic_New_Status:
            self._logger.info('Updating Paging Status to Semi-Automatic Broadcasting')
            await self._set_paging_status(3, 'Semi Automatic Broadcasting')
            await self._set_live_status(False)
            await self._set_broadcasting_status(False)
            await self._set_semi_automatic_status(True)
            self.Paging_APP_Semi_Automatic_New_Status = False
            return True
        else:
            self._logger.info('Updating Paging Status to Ready...')
            await self._set_paging_status(1, 'Ready...')
            await self._set_live_status(False)
            await self._set_broadcasting_status(False)
            await self._set_semi_automatic_status(False)
            return True

    async def _set_paging_status(self, status: int, msg: str):
        if status != self.Paging_APP_Status:
            self.Paging_APP_Status = status
            await self.Status.set_value(msg, VariantType.String)
            await self.Status_Code.set_value(status, VariantType.Byte)

    async def _set_live_status(self, status: bool):
        self._logger.info('Set Live Status - APP_Live_Status :%s Status:%s', self.Paging_APP_Live_Status, status)
        if self.Paging_APP_Live_Status != status:
            self.Paging_APP_Live_Status = status
            await self.Live_Status.set_value(status, VariantType.Boolean)
            await self.Live.set_value(status, VariantType.Boolean)

    async def _set_broadcasting_status(self, status: bool):
        self._logger.info('Set Live Status - APP_Broadcasting :%s Status:%s', self.Paging_APP_Broadcast_Status, status)
        if self.Paging_APP_Broadcast_Status != status:
            self.Paging_APP_Broadcast_Status = status
            await self.Broadcasting_Message_Status.set_value(status, VariantType.Boolean)
            await self.Broadcasting_Message.set_value(status, VariantType.Boolean)

    async def _set_semi_automatic_status(self, status: bool):
        if self.Paging_APP_Semi_Automatic_Status != status:
            self.Paging_APP_Semi_Automatic_Status = status
            await self.Semiautomatic_Paging_Status.set_value(status, VariantType.Boolean)
            await self.Semiautomatic_Paging.set_value(status, VariantType.Boolean)

    async def set_pre_recorded_message(self):
        mm = await self.Broadcasting_Message_No.get_value()
        if mm in self.PreRecordedMessages.keys():
            msg = self.PreRecordedMessages[mm]
            await self.Broadcasting_Message_Message.set_value(msg.Title, VariantType.String)
            self.Paging_APP_Broadcast_FileName = msg.FileName

    def log_status(self):
        self._logger.info('Paging_APP_Status = %s', self.Paging_APP_Status)
        self._logger.info('Paging_APP_Live_Status = %s New Status=(%s)', self.Paging_APP_Status,
                          self.Paging_APP_Live_New_Status)
        self._logger.info('Paging_APP_Broadcast_Status = %s New Status=(%s)', self.Paging_APP_Broadcast_Status,
                          self.Paging_APP_Broadcast_New_Status)
        self._logger.info('Paging_APP_Semi_Automatic_Status = %s New Status=(%s)',
                          self.Paging_APP_Semi_Automatic_Status,
                          self.Paging_APP_Semi_Automatic_New_Status)
