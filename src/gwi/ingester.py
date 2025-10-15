"""GridWorks Ingester - receives files and puts them in S3 & postgres"""

import asyncio
import json
from typing import Any, Optional, cast

import structlog
from gwproactor import App, AppInterface
from gwproactor.actors.actor import PrimeActor
from gwproto import Message
from gwproto.messages import EventBase as GwprotoEventBase
from gwproactor.message import MQTTReceiptPayload

from gwi.config import IngesterSettings
from gwi.asl.codec import AslCodec
from gwi.asl.types import MultichannelSnapshotEvent
from gwi.storage import PostgresStorage, S3Storage, LocalStorage

logger = structlog.get_logger()


class GridWorksIngester(PrimeActor):
    """
    Minimal gwproactor actor that bridges to ASL codec for processing.
    Maintains link state with uploader while using clean ASL types internally.
    """
    
    def __init__(self, name: str, services: AppInterface):
        super().__init__(name, services)
        self.codec = AslCodec()
        self.settings = cast(IngesterSettings, self.services.settings)
        
        # Storage backends
        self.postgres: Optional[PostgresStorage] = None
        self.s3: Optional[S3Storage] = None
        self.local: Optional[LocalStorage] = None
        
        # Statistics
        self.messages_received = 0
        self.messages_processed = 0
        self.messages_failed = 0
        
    async def start(self) -> None:
        """Initialize storage backends"""
        await super().start()
        
        try:
            if self.settings.postgres_enabled:
                self.postgres = PostgresStorage(self.settings)
                await self.postgres.initialize()
                logger.info("PostgreSQL storage initialized")
                
            if self.settings.s3_enabled:
                self.s3 = S3Storage(self.settings)
                await self.s3.initialize()
                logger.info("S3 storage initialized")
                
            if self.settings.local_storage_enabled:
                self.local = LocalStorage(self.settings)
                await self.local.initialize()
                logger.info("Local storage initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            raise
    
    def process_mqtt_message(
        self, 
        message: Message[MQTTReceiptPayload], 
        decoded: Message[Any]
    ) -> None:
        """
        Bridge point from gwproactor to ASL codec.
        This is where we extract and convert the message.
        """
        self.messages_received += 1
        
        topic = message.Payload.message.topic
        logger.debug(f"Received message on topic: {topic}")
         # Parse topic: gw/from-alias/to/dst/type-name
        try:
            # Check if it's an event we care about
            if not isinstance(decoded.Payload, GwprotoEventBase):
                logger.debug(f"Ignoring non-event message: {type(decoded.Payload)}")
                return
                
            # Extract the type name to determine handling
            type_name = getattr(decoded.Payload, 'TypeName', None)
            
            if type_name == "multichannel.snapshot.event":
                # Bridge to ASL: Convert gwproto message to ASL type
                # Get the raw bytes from the original MQTT message
                raw_payload = message.Payload.payload
                
                # Deserialize using ASL codec
                try:
                    asl_event = self.codec.from_dict(
                        json.loads(raw_payload)
                    )
                    
                    if isinstance(asl_event, MultichannelSnapshotEvent):
                        # Process with our storage logic
                        asyncio.create_task(
                            self._store_snapshot_event(asl_event, topic)
                        )
                        self.messages_processed += 1
                    else:
                        logger.warning(f"Unexpected ASL type: {type(asl_event)}")
                        
                except Exception as e:
                    logger.error(f"ASL codec error: {e}", payload=raw_payload[:200])
                    self.messages_failed += 1
                    
            else:
                logger.debug(f"Ignoring event type: {type_name}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.messages_failed += 1
    
    async def _store_snapshot_event(
        self, 
        event: MultichannelSnapshotEvent,
        topic: str
    ) -> None:
        """
        Store the snapshot event to all configured backends.
        Uses ASL types, not gwproto types.
        """
        try:
            # Extract data from ASL event
            snapshot_data = {
                "gnode_alias": event.g_node_alias,
                "hw_uid": event.multichannel_snapshot.hw_uid,
                "timestamp_ms": event.time_created_ms,
                "channels": {
                    name: {
                        "value": value,
                        "unit": unit
                    }
                    for name, value, unit in zip(
                        event.multichannel_snapshot.channel_name_list,
                        event.multichannel_snapshot.measurement_list,
                        event.multichannel_snapshot.unit_list
                    )
                },
                "message_id": event.message_id,
                "topic": topic
            }
            
            # Store in parallel to all backends
            tasks = []
            if self.postgres:
                tasks.append(self.postgres.store(snapshot_data))
            if self.s3:
                tasks.append(self.s3.store(snapshot_data))
            if self.local:
                tasks.append(self.local.store(snapshot_data))
                
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Storage backend {i} failed: {result}")
                        
            logger.info(
                f"Stored snapshot from {event.g_node_alias}",
                channels=len(event.multichannel_snapshot.channel_name_list),
                timestamp=event.time_created_ms
            )
            
        except Exception as e:
            logger.error(f"Failed to store snapshot event: {e}")
    
    async def stop(self) -> None:
        """Cleanup storage connections"""
        logger.info(
            f"Ingester stats - Received: {self.messages_received}, "
            f"Processed: {self.messages_processed}, "
            f"Failed: {self.messages_failed}"
        )
        
        if self.postgres:
            await self.postgres.close()
        if self.s3:
            await self.s3.close()
        if self.local:
            await self.local.close()
            
        await super().stop()


class GridWorksIngesterApp(App):
    """
    Minimal App wrapper for the ingester.
    Just enough to satisfy gwproactor requirements.
    """
    
    @classmethod
    def prime_actor_type(cls) -> type[GridWorksIngester]:
        return GridWorksIngester
    
    @classmethod
    def app_settings_type(cls) -> type[IngesterSettings]:
        return IngesterSettings