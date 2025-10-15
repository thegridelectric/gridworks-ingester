from typing import Literal

from gwi.asl.codec import AslType
from gwi.asl.enums import RelayClosedOrOpen
from gwi.asl.property_format import SpaceheatName


class RelayReading(AslType):
    """ASL schema: [rco.relay.reading](https://github.com/thegridelectric/gridworks-asl/blob/dev/type_definitions/schemas/rco.relay.reading.yaml)"""
    name: SpaceheatName
    value: RelayClosedOrOpen
    type_name: Literal["rco.relay.reading"] = "rco.relay.reading"
