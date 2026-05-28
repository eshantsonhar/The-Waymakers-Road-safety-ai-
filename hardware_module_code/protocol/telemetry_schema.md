# RoadSoS Hardware Telemetry Protocol
## Version 1.0

## Packet Schema (JSON)

### Standard Telemetry Packet

Every hardware unit sends this JSON packet over HTTP POST or MQTT.

```json
{
  "device_id": "RPi-PICO2W-001",
  "timestamp": "2026-05-28T12:00:00.000Z",
  "telemetry_version": "1.0",

  "gps": {
    "lat": 12.971598,
    "lon": 77.594562,
    "altitude_m": 920.0,
    "speed_kmh": 45.2,
    "heading_deg": 180.5,
    "accuracy_m": 2.5,
    "satellites": 8,
    "fix_quality": 3,
    "timestamp_utc": "2026-05-28T12:00:00.000Z"
  },

  "accelerometer": {
    "x": 0.12,
    "y": -0.05,
    "z": 9.81,
    "scale": "±2g"
  },

  "gyroscope": {
    "x": 0.002,
    "y": -0.001,
    "z": 0.003,
    "scale": "±250dps"
  },

  "magnetometer": {
    "x": 15.2,
    "y": -8.7,
    "z": -3.1,
    "scale": "±4800uT"
  },

  "imu_temperature_c": 32.5,

  "system": {
    "battery_percent": 85,
    "cpu_temp_c": 42.0,
    "uptime_seconds": 3600,
    "free_memory_kb": 128000,
    "signal_strength_dbm": -75,
    "network_type": "LTE",
    "lte_rssi": -75,
    "firmware_version": "v1.0.0"
  },

  "crash_detection": {
    "crash_flag": false,
    "impact_force_g": 0.0,
    "speed_delta_kmh": 0.0,
    "rollover_detected": false,
    "confidence": 0.0,
    "detection_algorithm": "mpu9250_threshold"
  },

  "status_flags": {
    "sos_active": false,
    "emergency_brake": false,
    "airbag_deployed": false,
    "ignition_on": true,
    "vehicle_stopped": false
  }
}
```

## Binary Protocol (Compact)

For bandwidth-constrained environments, a CBOR/binary alternative.

Field layout (60 bytes fixed-size):
```
Offset  Size  Field
0       1     protocol_version (0x01)
1       8     device_id (uint64)
9       4     timestamp_unix (uint32)
13      4     lat (int32, scaled 1e7)
17      4     lon (int32, scaled 1e7)
21      2     altitude (int16, meters)
23      2     speed (uint16, cm/s)
25      2     heading (uint16, centidegrees)
27      2     accel_x (int16, mg)
29      2     accel_y (int16, mg)
31      2     accel_z (int16, mg)
33      2     gyro_x (int16, mdps)
35      2     gyro_y (int16, mdps)
37      2     gyro_z (int16, mdps)
39      2     mag_x (int16, mGauss)
41      2     mag_y (int16, mGauss)
43      2     mag_z (int16, mGauss)
45      1     battery_pct (uint8)
46      1     signal_strength_dbm (int8)
47      1     flags (bitmask)
48      2     crash_impact_g (uint16, cG)
50      2     speed_delta (uint16, cm/s)
52      1     satellites (uint8)
53      1     fix_quality (uint8)
54      4     checksum (uint32)
```

## HTTP Endpoint

```
POST /api/telemetry/hardware
Content-Type: application/json

[telemetry packet JSON]
```

## MQTT Topic

```
roadsos/telemetry/{device_id}
```

## Backend Integration

The backend telemetry handler `/api/telemetry/hardware`:

1. Validates the packet schema
2. Stores raw telemetry in in-memory buffer (last 1000 per device)
3. Runs crash detection algorithm on accelerometer data
4. If crash detected:
   - Creates incident in the same pipeline as demo simulator
   - Triggers ambulance dispatch via existing incident engine
   - Broadcasts via WebSocket
5. Updates device position on the map

This ensures hardware telemetry feeds the exact same pipeline as mobile simulation.