import asyncio
import logging
import os
import sys

from Core.Jaguar import Jaguar
from OpcServer.JaguarOpcUaServer import JaguarOpcUaServer
from Voice.ExtensionStatus import ExtensionStatus
from Voice.SoftSwitchServer import SoftSwitchServer

sys.path.insert(0, "..")


async def extension_status_changed(channel, status: ExtensionStatus):
    print('%s state changed to : %s' % (channel, str(status)))


async def main():
    _logger = logging.getLogger('Jaguar-Main')
    _opcUaServer = JaguarOpcUaServer()
    _softSwitchServer = SoftSwitchServer()
    # await _opcUaServer.init_server()
    # factory = OpcElementFactory(_opcUaServer)
    # elements = await factory.get_elements()

    # _logger.info('Starting server!')
    # _logger.info('Start OpcUa server ...')
    # opcua_task = asyncio.create_task(_opcUaServer.start())
    # _logger.info('OpcUa started')
    # _logger.info('Start softSwitch server ...')
    # soft_switch_task = asyncio.create_task(_softSwitchServer.start())
    _softSwitchServer.init_server()
    t1 = asyncio.create_task(_softSwitchServer.start())
    _logger.info('wait for softSwitch to be ready')
    await asyncio.sleep(1)
    _softSwitchServer.on_extension_status_changed(extension_status_changed)
    _logger.info('start originating call')
    await asyncio.create_task(_softSwitchServer.originate('PJSIP/3001'))
    await asyncio.create_task(_softSwitchServer.get_contacts())
    await t1

    _logger.info('softSwitch started')

    # await opcua_task
    # await soft_switch_task


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        jaguar = Jaguar()
        asyncio.run(jaguar.start(), debug=True)
    except KeyboardInterrupt:
        print('Interrupted')
        sys.exit(0)


