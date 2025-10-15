from typing import Literal

from pydantic import StrictInt

from gwi.asl.codec import AslType


class Power(AslType):
    """ASL schema: [power](https://github.com/thegridelectric/gridworks-asl/blob/dev/type_definitions/schemas/power.yaml)"""
    watts: StrictInt
    type_name: Literal["power"] = "power"
