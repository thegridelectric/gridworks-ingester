# GridWorks Ingester

Cloud-based telemetry persistence service for distributed SCADA system. 

**Status**: Work in Progress

## Overview

The GridWorks Ingester receives telemetry data from field devices via MQTT and provides dual persistence to PostgreSQL (for queries) and S3 (for archival). It's the cloud-side companion to [gridworks-upload](https://github.com/SmoothStoneComputing/gridworks-uploader), implementing the persistence mechanism designed by Andrew Schweitzer at Smooth Stone Computing.

## Architecture

```
MEP SCADA → gridworks-upload → Cloud Message Broker → gridworks-ingester → PostgreSQL + S3
```

The code expects the broker to be an MQTT broker. It can also be a rabbit broker with an MQTT plugin.

### Message Flow

1. **MEP SCADA** posts telemetry to local gridworks-upload every 30 seconds
2. **gridworks-upload** wraps messages as events and publishes to cloud MQTT
3. **gridworks-ingester** receives, acknowledges, and persists all messages
4. Data is stored in both PostgreSQL (normalized) and S3 (raw JSON)

### Supported Message Types

#### Persisted Events (acknowledged and stored)
- `scada.snapshot.event` - Point-in-time telemetry snapshots

#### Fire-and-Forget Messages (stored but not acknowledged)
- `power` - Real-time power readings

## Quick Start

```bash
# Clone repository
git clone [repository-url] gridworks-ingester
cd gridworks-ingester

# Install dependencies
uv sync --all-extras

# Configure environment
cp .env.example .env
# Edit .env with your MQTT broker, PostgreSQL, and S3 credentials

# Run the ingester
uv run gwi run
```

## Configuration

Create a `.env` file with:

```env
# MQTT Broker (cloud-based)
GWI_MQTT_BROKER_HOST=your-broker.amazonaws.com
GWI_MQTT_BROKER_PORT=1883
GWI_MQTT_USERNAME=your-username
GWI_MQTT_PASSWORD=your-password

# PostgreSQL
GWI_POSTGRES_HOST=localhost
GWI_POSTGRES_DATABASE=mep_telemetry
GWI_POSTGRES_USER=postgres
GWI_POSTGRES_PASSWORD=your-password

# S3 Archival
GWI_S3_BUCKET=mep-telemetry
GWI_AWS_ACCESS_KEY_ID=your-key
GWI_AWS_SECRET_ACCESS_KEY=your-secret
```

## ASL Types

The ingester includes an ASL (Application Shared Language) implementation in `src/gwi/asl/` with the specific message types needed for basic telemetry:

- `power` - Real-time power readings  
- `scada.snapshot` and `scada.snapshot.event` - Telemetry snapshots
 - `channel.reading` - Analog measurements
 - `rco.relay.reading` - Relay states

This is an à la carte selection from the [GridWorks ASL Registry](hhttps://schemas.electricity.works), containing only the types required for this application. The implementation provides type-safe message parsing without external dependencies.

See [`src/gwi/asl/README.md`](src/gwi/asl/README.md) for complete ASL documentation and `src/gwi/asl/tests/` for working examples.

## Development

```bash
# Run tests
uv run pytest -v

# Run with debug logging
uv run gwi run --debug

# Check configuration
uv run gwi config
```

## For Integration with your local SCADA

### Sending Messages from SCADA

Your SCADA should POST messages to gridworks-upload's API:

```python
# For persistent telemetry (will be wrapped as event)
POST http://localhost:8000/primary-scada/scada-snapshot
Body: ScadaSnapshot.to_dict()

# For fire-and-forget power readings
POST http://localhost:8000/primary-scada/power
Body: Power.to_dict()
```

For more details go to the [gridworks-uploader docs](https://github.com/SmoothStoneComputing/gridworks-uploader).

### Message Persistence Rules

- **End type name with `.event`** for guaranteed persistence
- **Plain types** (like `power`) are best-effort, no acknowledgment
- Events are retried on failure, plain messages are not

## Architecture Documentation

For complete details on the persistence mechanism, see:
- [GridWorks Persistence Mechanism](https://gridworks.readthedocs.io/en/latest/persistence-mechanism.html)
- [gridworks-proactor](https://github.com/SmoothStoneComputing/gridworks-proactor) (underlying framework)

## Support

- **MEP Team**: Contact Jessica for integration support
- **Architecture**: Contact Andrew at Smooth Stone Computing
- **Issues**: Use GitHub issues for bug reports

## License

Distributed under the terms of the [MIT license][license],
_Gridworks Ingester_ is free and open source software.