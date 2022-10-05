import logging
from typing import Dict

from asyncua import Node
from asyncua.ua import VariantType

from OpcuaBase.OpcUaPreRecordedMessage import OpcUaPreRecordedMessage


class OpcUaCalling:
    Call_PreRecord_Message: Node
    Call_PreRecord_Message_No: Node
    Call_PreRecord_Message_Message: Node
    Call_PreRecord_Message_Status: Node

    Call_Group_Calling: Node
    Call_Group_Calling_Group_No: Node
    Call_Group_Calling_Status: Node

    PreRecordedMessages: Dict[int, OpcUaPreRecordedMessage]

    Call_APP_Message_FileName: str = ''

    def __init__(self):
        self._logger = logging.getLogger('Jaguar-Calling')
        self.PreRecordedMessages = {}

    def get_nodes(self):
        return [self.Call_PreRecord_Message,
                self.Call_PreRecord_Message_No,
                self.Call_Group_Calling,
                self.Call_Group_Calling_Group_No]

    async def set_announcement(self, val):
        await self.Call_PreRecord_Message_Status.set_value(val, VariantType.Boolean)

    async def set_announcement_message(self):
        mm = await self.Call_PreRecord_Message_No.get_value()
        self._logger.info(f'Set ann message to {mm}')
        if mm in self.PreRecordedMessages.keys():
            msg = self.PreRecordedMessages[mm]
            self._logger.info(f'Set ann {msg.Title} file to  {msg.FileName}')
            await self.Call_PreRecord_Message_Message.set_value(msg.Title, VariantType.String)
            self.Call_APP_Message_FileName = msg.FileName
