import logging

from asyncua import Node, ua
from asyncua.ua import VariantType


class OpcUaParameter:

    _logger = logging.getLogger('Jaguar-Parameter')

    Value: Node = None
    Name: str = None
    Type: ua.VariantType.String

    def __init__(self, name, parameter_type: VariantType.String):
        self.Name = name
        self.Type = parameter_type
