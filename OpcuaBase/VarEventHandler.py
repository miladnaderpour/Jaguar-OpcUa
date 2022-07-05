import logging


class VerEventHandler(object):
    _logger = logging.getLogger('asyncua')

    def datachange_notification(self, node, val, data):
        print('NewState:' + str(val))

    def event_notification(self, event):
        print("Python: New event", event)
