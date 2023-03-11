import asyncio
import configparser
import json
import logging
from typing import Dict

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.legacy.server import WebSocketServerProtocol


def _get_message(typ: str, action: str, data: str):
    msg = {
        "Type": typ,
        "Action": action,
        "Data": data
    }
    return msg


class WebSocketServer:
    _logger = logging.getLogger('Jaguar-WebSocket')

    Subscribers: Dict[str, WebSocketServerProtocol]
    _alive = True

    def __init__(self):
        self.Subscribers = {}
        self._config = configparser.ConfigParser()
        self._config.optionxform = str
        self._config.read('Jaguar.conf')

    async def _data_received_handler(self, socket: WebSocketServerProtocol):
        client_ip = socket.remote_address[0]
        self.Subscribers[client_ip] = socket
        self._logger.info('Client: %s connected' % client_ip)
        while True:
            try:
                message = await socket.recv()
                await socket.send(message)
            except ConnectionClosed:
                message = None
            if message is None:
                break
        self._logger.warning('Client: %s disconnected' % client_ip)

    async def run(self):
        server_config = self._config['SERVER']
        self._logger.info('Start socket server on *:%s ' % 4567)
        async with websockets.serve(self._data_received_handler, "", 4567):
            await asyncio.Future()  # run forever

    async def broadcast(self, typ: str, action: str, data: str):
        self._logger.info("Broadcast %s - %s  Data:%s", typ, action, data)
        websockets.broadcast(self.Subscribers.values(), json.dumps(_get_message(typ, action, data)))
