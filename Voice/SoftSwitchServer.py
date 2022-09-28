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
        self._on_conference_status_changed_subscribers = set()

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
            await self._extension_peer_status_changed_dispatch(message.Endpoint, message.Status)

        elif message.Event == 'ContactListComplete':
            self._logger.info(message)

    def __init_events(self):
        self._manager.on_connect = on_connect
        self._manager.on_disconnect = on_disconnect
        self._manager.on_login = on_login
        self._manager.register_event('*', self.universal_callback)
        self._manager.register_event('Confbridge*', self._conference_status_changed)

    async def start(self):
        await self._manager.connect()
        await self.get_contacts()
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

    async def paging_live(self, extensions: [str]):
        self._logger.info(' start Live Paging...')
        for ext in extensions:
            self._logger.info('Start Pager %s', ext)
            action = {
                'Action': 'Originate',
                'Channel': 'Local/1@Paging-pager',
                'WaitTime': 2,
                'CallerID': 'Paging...',
                'Exten': '1',
                'Timeout ': 2,
                'Context': 'Paging-Start',
                'Priority': 1,
                'Async': True,
                'Variable': 'var1=%s' % ext
            }
            a: Message = await self._manager.send_action(action, False)
            self._logger.info('action status: %s' % str(a.success))
            self._logger.info('action id is: %s' % a.action_id)
            self._logger.info('end of Live Paging')
            await asyncio.sleep(1)

    async def paging_live_master(self, extension):
        self._logger.info(' start Live Paging master...')
        self._logger.info('Start Master Pager %s', extension)
        action = {
            'Action': 'Originate',
            'Channel': 'Local/1@Paging-Master',
            'WaitTime': 2,
            'CallerID': 'Paging...',
            'Exten': '1',
            'Timeout ': 2,
            'Context': 'Paging-Start',
            'Priority': 1,
            'Async': True,
            'Variable': 'var1=%s' % extension
        }
        a: Message = await self._manager.send_action(action, False)
        self._logger.info('action status: %s' % str(a.success))
        self._logger.info('action id is: %s' % a.action_id)
        self._logger.info('end of Live Master Paging')

    async def paging_stop_live(self):
        self._logger.info('Stop Live Paging...')
        action = {
            'Action': 'Command',
            'Command': 'confbridge kick 8 all'
        }
        a: Message = await self._manager.send_action(action, False)
        self._logger.info('action status: %s' % str(a.success))
        self._logger.info('action id is: %s' % a.action_id)
        self._logger.info('end of Stop Live Paging...')

    async def paging_live_test(self):
        self._logger.info(' start Live Paging test ...')
        action = {
            'Action': 'Originate',
            'Channel': 'Local/1@Paging-Test',
            'WaitTime': 15000,
            'CallerID': 'Paging...',
            'Application': 'Playback',
            'Data': 'PreRecordedMessage/Pre-Recorded-4&PreRecordedMessage/Pre-Recorded-3&PreRecordedMessage/Pre'
                    '-Recorded-2&tt-weasels',
            'Async': True
        }
        a: Message = await self._manager.send_action(action, False)
        self._logger.info('action status: %s' % str(a.success))
        self._logger.info('action id is: %s' % a.action_id)
        self._logger.info('end of Live Paging')

    async def broadcast_message(self, message_no: str, is_admin: bool = False):
        self._logger.info(' start broadcast message ...')
        action = {
            'Action': 'Originate',
            'Channel': 'Local/1@Paging-app',
            'WaitTime': 15000,
            'CallerID': 'Paging...',
            'Application': 'Playback',
            'Data': '%s' % message_no,
            'Async': True,
            'Variable': 'is_admin=%s' % is_admin
        }
        a: Message = await self._manager.send_action(action, False)
        self._logger.info('action status: %s' % str(a.success))
        self._logger.info('action id is: %s' % a.action_id)
        self._logger.info('end of message broadcasting')

    async def get_contacts(self):
        self._logger.info('get contact status')
        a: Message = await self._manager.send_action({'Action': 'PJSIPShowContacts'}, False)
        self._logger.info('get contact status : %s' % str(a.success))

    def on_extension_status_changed(self, call_back):
        self._on_status_changed_subscribers.add(call_back)

    def on_conference_status_changed(self, call_back):
        self._on_conference_status_changed_subscribers.add(call_back)

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

    async def _conference_status_changed(self, manager: Manager, message: Message):

        num = message.BridgeNumChannels
        channel = ''
        match message.Event:
            case 'ConfbridgeStart':
                self._logger.info('Conf Bridge Info (Start): Bridge %s Channels: %s Conference:%s',
                                  message.BridgeName, num, message.Conference)
                event = 'Start'
            case 'ConfbridgeEnd':
                self._logger.info('Conf Bridge Info (End): Bridge %s Channels: %s Conference:%s',
                                  message.BridgeName, num, message.Conference)
                event = 'End'
            case 'ConfbridgeJoin':
                channel = get_channel_extension(message.Channel)
                self._logger.info('Conf Bridge Info (Join): channel %s joined to %s Channels: %s Conference:%s - ',
                                  channel, message.BridgeName, num, message.Conference)
                event = 'Join'

            case 'ConfbridgeLeave':
                channel = get_channel_extension(message.Channel)
                self._logger.info('Conf Bridge Info (Join): channel %s joined to %s Channels: %s Conference:%s - ',
                                  channel, message.BridgeName, num, message.Conference)
                event = 'Leave'
            case _:
                event = ''

        for callback in self._on_conference_status_changed_subscribers:
            await callback(event, num, channel)
