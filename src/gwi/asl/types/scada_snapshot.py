from typing import Literal

from gwi.asl.codec import AslType
from gwi.asl.property_format import LeftRightDot, UTCMilliseconds
from gwi.asl.types.channel_reading import ChannelReading
from gwi.asl.types.relay_reading import RelayReading


class ScadaSnapshot(AslType):
    """ASL schema: [scada.snapshot](https://github.com/thegridelectric/gridworks-asl/blob/dev/type_definitions/schemas/scada.snapshot.yaml)"""
    g_node_alias: LeftRightDot
    scada_unix_ms: UTCMilliseconds
    channel_readings: list[ChannelReading]
    relay_readings: list[RelayReading]
    type_name: Literal["scada.snapshot"] = "scada.snapshot"
