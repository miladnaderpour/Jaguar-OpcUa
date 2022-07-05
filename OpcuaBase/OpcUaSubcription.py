import logging

from asyncua import Node


class OpcUaSubscriptionHandler:
    _logger = logging.getLogger('Jaguar-OpcUaSubscriptionHandler')

    def __init__(self):
        self._on_data_changed_subscribers = set()

    async def datachange_notification(self, node: Node, val, data):
        self._logger.debug('datachange_notification %r %s', node, val)
        for callback in self._on_data_changed_subscribers:
            self._logger.debug('call back method  %r ', callback)
            await callback(node, val, data)

    def on_data_changed(self, call_back):
        self._logger.debug('New on_data_changed Subscription')
        self._on_data_changed_subscribers.add(call_back)

    # async def _extension_peer_status_changed_dispatch(self, channel: string, state):
    #     match state:
    #         case 'Reachable':
    #             status = ExtensionStatus.OnHook
    #         case 'Unreachable':
    #             status = ExtensionStatus.UnReachable
    #         case _:
    #             status = ExtensionStatus.UnReachable
    #
    #     for callback in self._on_status_changed_subscribers:
    #         await callback(channel, status)
