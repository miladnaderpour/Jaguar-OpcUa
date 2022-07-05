import logging
import sys
import time
from pprint import pprint
import asyncio
from panoramisk import Manager

from Ami.AmiConnector import AmiConnector

sys.path.insert(0, "..")


async def extension_status(stb):
    # manager = Manager(loop=asyncio.get_event_loop(),
    #                   host='10.2.2.72', port=5038,
    #                   username='Jaguar', secret='!Jaguar!')
    #
    # print(f"stb: {stb} started at {time.strftime('%X')}")
    await asyncio.sleep(stb)
    # await manager.connect()
    # extension = await manager.send_action({'Action': 'Originate', 'Channel': 'PJSIP/3001', 'Context': 'Internal-Main', 'Exten': '25655', 'Priority': 1})
    # pprint(extension)
    # print(f"stb: {stb} finished at {time.strftime('%X')}")
    # # while True:
    # #     await asyncio.sleep(stb)
    print(f"Start Connector - {time.strftime('%X')}")
    # manager.close()
    # amic = AmiConnector()
    # print(f"init server - {time.strftime('%X')}")
    # amic.init_server()
    # a = asyncio.create_task(amic.start())
    # await asyncio.sleep(10)
    # print(f"Originate call... - {time.strftime('%X')}")
    # b = asyncio.create_task(amic.originate('SIP/3001'))
    # print(f"End of origination - {time.strftime('%X')}")
    # await b
    # print(f"End of B - {time.strftime('%X')}")
    # await asyncio.sleep(2)
    # amic._alive = False
    # await a


async def main():
    coro1 = extension_status(3)
    # coro2 = extension_status(2)
    # coro3 = extension_status(5)
    # t1 = asyncio.create_task(coro1)
    # t2 = asyncio.create_task(coro2)
    # t3 = asyncio.create_task(coro3)
    # await t1
    # await t2
    # await t3
    await asyncio.gather(coro1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
