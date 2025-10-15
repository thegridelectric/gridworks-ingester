from typing import Literal, Self

from pydantic import model_validator

from gwi.asl.codec import AslError
from gwi.asl.types.event_base import EventBase
from gwi.asl.types.scada_snapshot import ScadaSnapshot


class ScadaSnapshotEvent(EventBase):
    """ASL schema: [scada.snapshot](https://github.com/thegridelectric/gridworks-asl/blob/dev/type_definitions/schemas/scada.snapshot.event.yaml)"""
    scada_snapshot: ScadaSnapshot
    type_name: Literal["scada.snapshot.event"] = "scada.snapshot.event"
    
    @model_validator(mode="after")
    def check_axiom_1(self) -> Self:
        """
        Axiom1: Src must equal ScadaSnapshot.GNodeAlias to ensure consistent 
        identification of the source SCADA throughout the message hierarchy.
        """
        if self.src != self.scada_snapshot.g_node_alias:
            raise AslError(
                "Src %s must equal ScadaSnapshot.GNodeAlias %s",
                self.src,
                self.scada_snapshot.g_node_alias)
        return self
    
    @property
    def g_node_alias(self) -> str:
        return self.src
