from typing import Literal

from pydantic import StrictInt

from gwi.asl.codec import AslType
from gwi.asl.property_format import SpaceheatName


class ChannelReading(AslType):
    """ASL schema: [channel.reading](https://github.com/thegridelectric/gridworks-asl/blob/dev/type_definitions/schemas/channel.reading.yaml)"""
    name: SpaceheatName
    value: StrictInt
    unit: str
    type_name: Literal["channel.reading"] = "channel.reading"
