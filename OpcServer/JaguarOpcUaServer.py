import asyncio
import configparser
import logging

from asyncua import ua, Server
from asyncua.common import Node

from OpcuaBase.OpcUaSubcription import OpcUaSubscriptionHandler


def get_security_policies(config) -> []:
    security_policy = []
    for x in config:
        if config[x] == '1':
            security_policy.append(ua.SecurityPolicyType[x])
    return security_policy


class JaguarOpcUaServer:
    _logger = logging.getLogger('Jaguar-OpcUaServer')

    idx = None

    def __init__(self):
        self._idx = None
        self._config = configparser.ConfigParser()
        self._config.optionxform = str
        self._config.read('Jaguar.conf')
        self._server = Server()
        self._alive = True
        self.Subscription = None
        self._handler = None

    async def init_server(self):

        # Server Config
        server_config = self._config['SERVER']
        self._logger.info('Init server %s' % server_config['endpoint'])

        # Basic Registration And Copyright
        self._server.name = 'Jaguar OPCUA Server'
        self._server.product_uri = 'https://Jaguar.Synapse.io'
        self._server.manufacturer_name = 'Synapse Co'

        # Init Certificates
        self._logger.info('Server Certificates: %s , %s' % (server_config['certificate'], server_config['key']))
        await self._server.load_certificate(server_config['certificate'])
        await self._server.load_private_key(server_config['key'])

        self._server.set_security_policy(get_security_policies(self._config['Security']))
        # self._server.set_security_IDs(["Username"])
        # user_manager = JaguarUserManager()
        # self._server.iserver.set_user_manager(user_manager)

        await self._server.init()

        self._server.set_endpoint(server_config['endpoint'])
        self._idx = await self._server.register_namespace(server_config['uri'])
        await self._server.set_application_uri(server_config['uri'])
        self.idx = self._idx

        # Create Subscription Handler
        self._logger.info('Create Subscription Handler')
        await self._create_data_subscription()

    async def _create_data_subscription(self):
        self._logger.info('Wait For Subscription Handler ...')
        self._handler = OpcUaSubscriptionHandler()
        self.Subscription = await self._server.create_subscription(500, self._handler)

    def on_data_changed(self, callback):
        self._handler.on_data_changed(callback)

    async def start(self):
        async with self._server:
            while self._alive:
                await asyncio.sleep(1)

    def stop(self):
        self._alive = False

    async def add_object(self, name) -> Node:
        return await self._server.nodes.objects.add_object(self._idx, name)

    async def add(self, identifier, node: Node, name, value, var_type: ua.VariantType, writable=True) -> Node:
        nodeid = ua.NodeId(identifier, self._idx)
        var = await node.add_variable(nodeid, name, value, var_type)
        if writable:
            await var.set_writable()
        return var

    async def add_folder(self, name) -> Node:
        return await self._server.nodes.objects.add_folder(self._idx, name)
