import asyncio
import configparser
import logging
import string

from asterisk.ami import AMIClient, AMIClientAdapter


class AmiConnector:
    _ami: AMIClient = None
    _logger = logging.getLogger('Jaguar-AMI-Connector')

    def __init__(self):
        self._secret = None
        self._user = None
        self._host = None
        self._port = None
        self._config = configparser.ConfigParser()
        self._config.optionxform = str
        self._config.read('Asterisk.conf')
        # Server Config
        self._server_config = self._config['SERVER']
        # Basic Configuration
        self._alive = True

    def init_server(self):
        self._host = self._server_config['host']
        self._port = self._server_config['port']
        self._user = self._server_config['user']
        self._secret = self._server_config['secret']
        self._logger.info(f'init Asterisk Manager - {self._host}:{self._port} ({self._user}:{self._secret})')
        self._ami = AMIClient(self._host, int(self._port))
        self._ami.login(self._user, self._secret)

    async def start(self):
        self._logger.info(f'Login to Asterisk Manager - {self._host}:{self._port} ({self._user}:{self._secret})')
        self._ami.login(self._user, self._secret)
        while self._alive:
            await asyncio.sleep(1)

    async def originate(self, ext: string):
        self._logger.info('originating call to %s' % ext)
        adapter = AMIClientAdapter(self._ami)
        f = adapter.Originate(
            Channel='PJSIP/3001',
            Exten='25655',
            Priority=1,
            Context='Internal-Main',
            CallerID='welcome')
        self._logger.info(f)
