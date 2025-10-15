import uuid
import time

from pydantic import Field
from gwi.asl.codec import AslType
from gwi.asl.property_format import UTCMilliseconds
class EventBase(AslType):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    time_created_ms: UTCMilliseconds = Field(
        default_factory=lambda: int(time.time() * 1000)
    )
    src: str