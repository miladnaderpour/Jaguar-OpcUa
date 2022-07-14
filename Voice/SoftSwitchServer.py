import asyncio
import configparser
import logging
import string
from panoramisk import Manager, Message
from Voice.ExtensionStatus import ExtensionStatus


def on_connect(mngr: Manager):
    logging.info(
        'Connected to %s:%s AMI socket successfully' %
        (mngr.config['host'], mngr.config['port'])
    )


def on_login(mngr: Manager):
    logging.info(
        'Connected user:%s to AMI %s:%s successfully' %
        (mngr.config['username'], mngr.config['host'], mngr.config['port'])
    )


def on_disconnect(mngr: Manager, exc: Exception):
    logging.info(
        'Disconnect user:%s from AMI %s:%s' %
        (mngr.config['username'], mngr.config['host'], mngr.config['port'])
    )
    logging.debug(str(exc))


async def on_startup(mngr: Manager):
    await asyncio.sleep(0.1)
    logging.info('Something action...')


async def on_shutdown(mngr: Manager):
    await asyncio.sleep(0.1)
    logging.info(
        'Shutdown AMI connection on %s:%s' % (mngr.config['host'], mngr.config['port'])
    )


def get_channel_extension(channel: str):
    return channel.split("/")[1].split("-")[0]


class SoftSwitchServer:
    _logger = logging.getLogger('Jaguar-SoftSwitchServer')
    _manager: Manager = None

    def __init__(self):
        self.loop = asyncio.get_event_loop()
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
        self._on_status_changed_subscribers = set()

    def init_server(self):
        self._host = self._server_config['host']
        self._port = self._server_config['port']
        self._user = self._server_config['user']
        self._secret = self._server_config['secret']
        self._logger.info(f'Asterisk Manager {self._host}:{self._port} ({self._user}:{self._secret})')
        self._manager = Manager(host=self._host, port=self._port,
                                username=self._user, secret=self._secret)
        self.__init_events()

    async def universal_callback(self, manager: Manager, message: Message):
        if message.Event == 'PeerStatus':
            self._logger.info('%s state changed to : %s' % (message.Peer, message.PeerStatus))
            await self._extension_peer_status_changed_dispatch(str(message.Peer).split("/")[1],
                                                               message.PeerStatus)
        elif message.Event == 'Newstate':
            self._logger.info(message)
            self._logger.info('%s state changed to : %s' % (message.Channel, message.ChannelStateDesc))
            await self._extension_status_changed_dispatch(get_channel_extension(message.Channel),
                                                          message.ChannelStateDesc, message.Channel)
        elif message.Event == 'Hangup':
            self._logger.info(message)
            self._logger.info('%s state changed to : Hang up (%s)' % (message.Channel, message.Cause))
            await self._extension_status_changed_dispatch(get_channel_extension(message.Channel), 'Hangup', '')

        elif message.Event == 'DialState':
            self._logger.info('DialState: %s' % message)

        elif message.Event == 'ContactListComplete':
            self._logger.info(message)

        elif message.Event == 'ContactList':
            self._logger.info('%s is %s (ip:%s)' % (message.Endpoint, message.Status, message.ViaAddr))

    def __init_events(self):
        self._manager.on_connect = on_connect
        self._manager.on_disconnect = on_disconnect
        self._manager.on_login = on_login
        # self._manager.register_event('Hangup*', hangup_callback)
        # self._manager.register_event('NewChannel*', new_channel_callback)
        self._manager.register_event('*', self.universal_callback)

    async def start(self):
        await self._manager.connect()
        while self._alive:
            await asyncio.sleep(1)

    async def originate(self, ext: string):
        self._logger.info('originating call to %s' % ext)
        action = {
            'Action': 'Originate',
            'Channel': 'PJSIP/%s' % ext,
            'WaitTime': 2,
            'CallerID': '',
            'Exten': '1',
            'Timeout ': 2,
            'Context': 'OnHold-Call',
            'Priority': 1,
            'Async': True
        }
        a: Message = await self._manager.send_action(action, False)
        self._logger.info('action status: %s' % str(a.success))
        self._logger.info('action id is: %s' % a.action_id)
        self._logger.info('end of originating call to %s' % ext)

    async def redirect(self, channel: string, to):
        self._logger.info('redirecting  channel  %s to %s', channel, to)
        action = {
            'Action': 'Redirect',
            'Channel': channel,
            'WaitTime': 2,
            'CallerID': '',
            'Exten': '%s' % to,
            'Timeout ': 2,
            'Context': 'Transfer-Call',
            'Priority': 1,
            'Async': True
        }
        a: Message = await self._manager.send_action(action, False)
        self._logger.info('action status: %s' % str(a.success))
        self._logger.info('end of redirecting channel %s' % channel)

    async def setvar(self, name, value):
        self._logger.info('Setting Global Variable %s to %s', name, value)
        action = {
            'Action': 'Setvar',
            'Variable': name,
            'Value': value,
        }
        a: Message = await self._manager.send_action(action, False)
        self._logger.info('action status: %s' % str(a.success))

    async def get_contacts(self):
        self._logger.info('get contact status')
        a: Message = await self._manager.send_action({'Action': 'PJSIPShowContacts'}, False)
        self._logger.info('get contact status : %s' % str(a.success))

    def on_extension_status_changed(self, call_back):
        self._on_status_changed_subscribers.add(call_back)

    async def _extension_status_changed_dispatch(self, channel: string, state, chanel):
        match state:
            case 'Up':
                status = ExtensionStatus.Up
            case 'Ringing':
                status = ExtensionStatus.Ringing
            case 'Hangup':
                status = ExtensionStatus.OnHook
            case _:
                status = ExtensionStatus.OnHook

        for callback in self._on_status_changed_subscribers:
            await callback(channel, status, chanel)

    async def _extension_peer_status_changed_dispatch(self, channel: string, state):
        match state:
            case 'Reachable':
                status = ExtensionStatus.OnHook
            case 'Unreachable':
                status = ExtensionStatus.UnReachable
            case _:
                status = ExtensionStatus.UnReachable

        for callback in self._on_status_changed_subscribers:
            await callback(channel, status, '')
