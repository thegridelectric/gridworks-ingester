"""
Test suite for ASL types
Demonstrates creating and serializing telemetry messages for the persistence pipeline
"""
import json
import time
from datetime import datetime
import uuid

import pytest

from gwi.asl.enums import RelayClosedOrOpen
from gwi.asl.types import (
    ChannelReading,
    Power,
    RelayReading,
    ScadaSnapshot,
    ScadaSnapshotEvent,
)

def test_create_power_message():
    """
    Example of creating a power message for fire-and-forget delivery.
    These are designed to be sent asynchronously on change with frequent
    checking so that the power is very accurate
    """
    
    # Create a simple power reading
    # Positive = consuming from grid, Negative = generating to grid
    power_msg = Power(
        watts=1523  # Currently consuming 1.523 kW from grid
    )
    
    print("\n=== Fire-and-Forget Power Message Flow ===")
    print("-" * 50)
    
    # Step 1: MEP SCADA posts to local gwupload
    print("\n1. MEP SCADA → gridworks-upload (HTTP POST on LAN):")
    print("\n   Endpoint pattern: /{local-actor-name}/{type-name}")
    print("   POST http://localhost:8000/primary-scada/power")
    print("   Content-Type: application/json")
    print(f"\n   {power_msg.to_dict()}")
    print("\n   → Returns: 200 OK (message queued for upload)")
    
    # Step 2: gwupload sends to cloud ingester via MQTT
    scada_alias = "w.isone.ma.lily.scada"
    from_alias_for_topic = scada_alias.replace(".", "-")
    type_name_for_topic = power_msg.type_name.replace(".", "-")
    topic = f"gw/{from_alias_for_topic}/to/ingester/{type_name_for_topic}"
    
    print("\n2. gridworks-upload → ingester (MQTT on cloud broker):")
    print(f"   Topic: {topic}")
    print("   QoS: 0 (fire-and-forget)")
    print(f"\n   Payload: {power_msg.to_dict()}")
    
    print("\n" + "-" * 50)
    print("CRITICAL NOTES:")
    print("  • NO event wrapper (not for persistence)")
    print("  • NO acknowledgment expected")
    print("  • NO retry on failure")
    print("  • NO timestamp - the time is `NOW`")
    print("  • Stale power data is worse than no data")
    
    wire_bytes = power_msg.to_bytes()
    print(f"\nWire size: {len(wire_bytes)} bytes (kept small for frequent sending)")
    

def test_create_scada_snapshot():
    """
    Example of creating a SCADA snapshot with temperature and relay readings.
    This is what MEP's SCADA compiles every 30 seconds from all sensors.
    """
    
    # Create temperature channel readings
    # Note: CelsiusTimes100 means actual temp * 100 (for fixed-point precision)
    # So 4523 = 45.23°C
    hp_ewt = ChannelReading(
        name="hp-ewt",  # Heat pump entering water temperature
        value=4523,      # 45.23°C
        unit="CelsiusTimes100"
    )
    
    hp_lwt = ChannelReading(
        name="hp-lwt",  # Heat pump leaving water temperature  
        value=3812,      # 38.12°C
        unit="CelsiusTimes100"
    )
    
    # Create relay state readings
    relay1 = RelayReading(
        name="r1",
        value=RelayClosedOrOpen.RelayClosed  # Relay contact is closed (conducting)
    )
    
    relay2 = RelayReading(
        name="r2", 
        value=RelayClosedOrOpen.RelayOpen  # Relay contact is open (not conducting)
    )
    
    # Create the snapshot
    # This represents the SCADA's "best known state" at this moment
    snapshot = ScadaSnapshot(
        g_node_alias="w.isone.ma.lily.scada",  # MEP's position in grid topology
        scada_unix_ms=int(time.time() * 1000),  # Current time in milliseconds
        channel_readings=[hp_ewt, hp_lwt],
        relay_readings=[relay1, relay2]
    )
    
    print("\n=== SCADA Snapshot Creation ===")
    print("-" * 50)
    
    # Show the snapshot details with formatted timestamp
    dt = datetime.fromtimestamp(snapshot.scada_unix_ms / 1000)
    ms = snapshot.scada_unix_ms % 1000
    formatted_time = dt.strftime("%a %b %d %Y %H:%M:%S") + f".{ms:03d}"
    # Show the snapshot details
    print(f"\nGNodeAlias: {snapshot.g_node_alias}")
    print(f"Timestamp: {snapshot.scada_unix_ms} ms ({formatted_time})")
    print(f"\nChannel Readings ({len(snapshot.channel_readings)}):")
    for reading in snapshot.channel_readings:
        print(f"  - {reading.name}: {reading.value} ({reading.unit})")
    print(f"\nRelay States ({len(snapshot.relay_readings)}):")
    for relay in snapshot.relay_readings:
        print(f"  - {relay.name}: {relay.value}")
    
    # Show the API endpoint
    print("\n" + "-" * 50)

    print("\nJSON Payload:")
    print(json.dumps(snapshot.to_dict(), indent=2))
    

    print("To send to gridworks-upload:")
    print("\n  POST http://localhost:8000/primary-scada/scada-snapshot")
    print("  Content-Type: application/json")
    print(f"  Body: {len(snapshot.to_bytes())} bytes")


    
    print("\nNote: Snapshot contains SCADA's 'best known state'")
    print("Individual readings may have been collected at different times")


def test_create_scada_snapshot_event():
    """
    Example of wrapping a snapshot in an event for reliable persistence.
    This is what gets sent to the cloud broker via gridworks-uploader.
    """
    
    # First create the snapshot (as above)
    snapshot = ScadaSnapshot(
        g_node_alias="w.isone.ma.lily.scada",
        scada_unix_ms=int(time.time() * 1000),
        channel_readings=[
            ChannelReading(name="hp-ewt", value=4523, unit="CelsiusTimes100"),
            ChannelReading(name="hp-lwt", value=3812, unit="CelsiusTimes100")
        ],
        relay_readings=[
            RelayReading(name="r1", value=RelayClosedOrOpen.RelayClosed),
            RelayReading(name="r2", value=RelayClosedOrOpen.RelayOpen)
        ]
    )
    
    # Wrap in event for persistence pipeline
    event = ScadaSnapshotEvent(
        message_id=str(uuid.uuid4()),
        time_created_ms=int(time.time() * 1000),
        src="w.isone.ma.lily.scada",  # MUST match snapshot.g_node_alias
        scada_snapshot=snapshot
    )
    
    # The event will be sent to this MQTT topic:
    # gw/w-isone-ma-lily-scada/to/ingester/scada-snapshot-event
    #
    # Note how dots become hyphens in the topic
    from_alias_for_topic = event.src.replace(".", "-")
    topic = f"gw/{from_alias_for_topic}/to/ingester/scada-snapshot-event"
    print("\n=== MQTT Topic for Persistence ===")
    print(f"Topic: {topic}")
    
    # This message WILL be:
    # - Acknowledged by the ingester
    # - Stored in PostgreSQL 
    # - Archived to S3
    # - Retried if delivery fails


def test_wire_format_differences():
    """
    Demonstrate the difference between Python objects and wire format.
    This is critical for debugging serialization issues.
    """
    
    reading = ChannelReading(
        name="test-sensor",
        value=100,
        unit="Percent"
    )
    
    # Python uses snake_case
    assert hasattr(reading, 'name')
    assert hasattr(reading, 'value')
    assert hasattr(reading, 'unit')
    assert hasattr(reading, 'type_name')
    
    # Wire format uses CamelCase
    wire = reading.to_dict()
    assert 'Name' in wire
    assert 'Value' in wire
    assert 'Unit' in wire
    assert 'TypeName' in wire
    
    # Round-trip works
    reading_copy = ChannelReading.from_dict(wire)
    assert reading_copy == reading
    
    print("\n=== Serialization Round-Trip ===")
    print(f"Original: {reading}")
    print(f"Wire format keys: {list(wire.keys())}")
    print(f"Restored: {reading_copy}")


def test_validation():
    """
    Demonstrate validation rules for MEP types.
    """
    
    # GNodeAlias must be LeftRightDot format
    with pytest.raises(Exception):
        ScadaSnapshot(
            g_node_alias="invalid_underscore_name",  # Will fail validation
            scada_unix_ms=int(time.time() * 1000),
            channel_readings=[],
            relay_readings=[]
        )
    
    # Event src must match snapshot g_node_alias
    snapshot = ScadaSnapshot(
        g_node_alias="w.isone.ma.lily.scada",
        scada_unix_ms=int(time.time() * 1000),
        channel_readings=[],
        relay_readings=[]
    )
    
    with pytest.raises(Exception):
        ScadaSnapshotEvent(
            message_id=str(uuid.uuid4()),
            time_created_ms=int(time.time() * 1000),
            src="different.node.alias",  # Must match snapshot!
            scada_snapshot=snapshot
        )
    
    print("\n=== Validation Rules ===")
    print("✓ GNodeAlias must use dots (not underscores)")
    print("✓ Event src must equal snapshot g_node_alias")
    print("✓ Channel/relay names must follow spaceheat.name format")


if __name__ == "__main__":
    # Run examples
    print("MEP ASL Type Examples\n" + "=" * 50)
    
    # snapshot = test_create_scada_snapshot()
    # event = test_create_scada_snapshot_event()
    power = test_create_power_message()
    
    # test_wire_format_differences()
    # test_validation()
    
    print("\n" + "=" * 50)
    print("Examples complete! This demonstrates:")
    print("1. Fire-and-forget power messages")
    print("2. Creating scada snapshots for persistence")
    print("3. Wire format (CamelCase) vs Python (snake_case)")
    print("4. MQTT topic patterns for cloud broker")