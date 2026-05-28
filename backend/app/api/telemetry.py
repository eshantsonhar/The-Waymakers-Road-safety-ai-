"""
Hardware & Mobile Telemetry Ingestion API
==========================================
Unified endpoint for consuming telemetry from:
1. Mobile sensor simulator (frontend)
2. Hardware module (RPi Pico 2W + SIM7600E-H)
3. Hardware laptop simulator

All sources use the same schema and trigger the same incident pipeline.
"""

import uuid
import math
import logging
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from app.websocket.manager import ws_manager, WSEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])


# ── Pydantic Models ──────────────────────────────────────────────────────────

class GPSData(BaseModel):
    lat: float
    lon: float
    altitude_m: float = 0.0
    speed_kmh: float = 0.0
    heading_deg: float = 0.0
    accuracy_m: float = 5.0
    satellites: int = 0
    fix_quality: int = 0


class AccelerometerData(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 9.81
    scale: str = "±2g"


class GyroscopeData(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    scale: str = "±250dps"


class SystemData(BaseModel):
    battery_percent: int = 85
    cpu_temp_c: float = 42.0
    uptime_seconds: int = 0
    free_memory_kb: int = 128000
    signal_strength_dbm: int = -75
    network_type: str = "LTE"
    firmware_version: str = "v1.0.0"


class CrashDetectionData(BaseModel):
    crash_flag: bool = False
    impact_force_g: float = 0.0
    speed_delta_kmh: float = 0.0
    rollover_detected: bool = False
    confidence: float = 0.0
    detection_algorithm: str = "threshold"


class StatusFlagsData(BaseModel):
    sos_active: bool = False
    emergency_brake: bool = False
    airbag_deployed: bool = False
    ignition_on: bool = True
    vehicle_stopped: bool = False


class TelemetryPacket(BaseModel):
    device_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    telemetry_version: str = "1.0"
    gps: Optional[GPSData] = None
    accelerometer: Optional[AccelerometerData] = None
    gyroscope: Optional[GyroscopeData] = None
    magnetometer: Optional[dict] = None
    imu_temperature_c: Optional[float] = None
    system: Optional[SystemData] = None
    crash_detection: Optional[CrashDetectionData] = None
    status_flags: Optional[StatusFlagsData] = None


# ── In-memory telemetry buffer ──────────────────────────────────────────────

_telemetry_buffer: Dict[str, List[dict]] = {}
_MAX_BUFFER_PER_DEVICE = 1000
_DEVICE_POSITIONS: Dict[str, dict] = {}
_DEVICE_INFO: Dict[str, dict] = {}


# ── Crash Detection Pipeline ────────────────────────────────────────────────

def _compute_severity(impact_g: float) -> str:
    """Map impact force to incident severity."""
    if impact_g >= 8.0:
        return "CRITICAL"
    elif impact_g >= 5.0:
        return "HIGH"
    elif impact_g >= 3.0:
        return "MEDIUM"
    return "LOW"


def _detect_crash_from_telemetry(packet: TelemetryPacket) -> Optional[dict]:
    """
    Run crash detection on a telemetry packet.
    Returns crash details if detected, None otherwise.
    """
    crash = packet.crash_detection
    if not crash:
        return None

    if not crash.crash_flag and not crash.rollover_detected:
        return None

    # Compute severity
    impact = crash.impact_force_g
    severity = _compute_severity(impact)

    # Classification
    if crash.rollover_detected and impact > 5.0:
        classification = "ROLLOVER"
    elif impact >= 6.0:
        classification = "SEVERE_CRASH"
    elif impact >= 3.0:
        classification = "MODERATE_CRASH"
    else:
        classification = "MINOR_COLLISION"

    # Confidence
    confidence = crash.confidence
    if confidence > 0.8:
        confidence_level = "HIGH"
    elif confidence > 0.5:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    return {
        "severity": severity,
        "classification": classification,
        "impact_force_g": impact,
        "speed_delta_kmh": crash.speed_delta_kmh,
        "rollover": crash.rollover_detected,
        "confidence": confidence,
        "confidence_level": confidence_level,
    }


def _create_incident_from_telemetry(packet: TelemetryPacket, crash_info: dict) -> Optional[dict]:
    """
    Create an incident in the same pipeline format as the demo simulator.
    This ensures hardware telemetry feeds the exact same incident pipeline.
    """
    from app.api.incidents import _incidents_store
    from app.api.ambulances import _ambulances_store

    gps = packet.gps
    if not gps:
        logger.warning(f"Telemetry from {packet.device_id}: no GPS data for incident")
        return None

    incident_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Generate incident number
    from app.demo.simulator import demo_simulator
    incident_number = f"HW-INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # Find nearest available ambulance
    nearest_amb = _find_nearest_ambulance(gps.lat, gps.lon)

    incident = {
        "id": incident_id,
        "incident_number": incident_number,
        "latitude": gps.lat,
        "longitude": gps.lon,
        "address": f"Telemetry alert from device {packet.device_id}",
        "district": "Bangalore Urban",
        "severity": crash_info["severity"],
        "status": "DETECTED",
        "crash_probability_score": crash_info["confidence"],
        "confidence_level": crash_info["confidence_level"],
        "event_classification": crash_info["classification"],
        "vehicle_type": "Vehicle",
        "weather_condition": "Clear",
        "is_demo": False,
        "source": f"hardware:{packet.device_id}",
        "detected_at": now,
        "created_at": now,
        "description": f"Hardware crash detected: {crash_info['classification']} ({crash_info['impact_force_g']:.1f}g impact)",
        "timeline": {"detected": now},
        "assigned_ambulance_id": nearest_amb[0] if nearest_amb else None,
        "ambulance_eta_minutes": None,
        "ambulance_distance_km": None,
        "assigned_hospital_id": None,
        "assigned_hospital_name": None,
        "route_source": "hardware_telemetry",
        "version": 1,
    }

    _incidents_store[incident_id] = incident

    # Dispatch ambulance if available
    if nearest_amb:
        amb_id, amb_data = nearest_amb
        amb_data["status"] = "EN_ROUTE_TO_SCENE"
        amb_data["current_incident_id"] = incident_id
        incident["status"] = "DISPATCHING"
        incident["assigned_ambulance_id"] = amb_id

    logger.info(
        f"Hardware incident created: {incident_number} "
        f"({crash_info['severity']}) from device {packet.device_id} "
        f"at ({gps.lat:.4f}, {gps.lon:.4f})"
    )

    return incident


def _find_nearest_ambulance(lat: float, lon: float):
    """Find nearest active ambulance."""
    from app.api.ambulances import _ambulances_store

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    available = [
        (aid, amb) for aid, amb in _ambulances_store.items()
        if amb.get("status") == "AVAILABLE" and amb.get("is_active")
    ]
    if not available:
        return None

    return min(available, key=lambda x: haversine(lat, lon, x[1]["latitude"], x[1]["longitude"]))


# ── API Endpoints ────────────────────────────────────────────────────────────

@router.post("/hardware")
async def ingest_telemetry(packet: TelemetryPacket):
    """
    Unified telemetry ingestion endpoint.
    Accepts telemetry from hardware modules and mobile simulations.
    Runs crash detection, stores telemetry, broadcasts state.
    """
    device_id = packet.device_id
    now = datetime.utcnow().isoformat()

    # 1. Store raw telemetry in buffer
    if device_id not in _telemetry_buffer:
        _telemetry_buffer[device_id] = []
    _telemetry_buffer[device_id].append(packet.model_dump())
    if len(_telemetry_buffer[device_id]) > _MAX_BUFFER_PER_DEVICE:
        _telemetry_buffer[device_id] = _telemetry_buffer[device_id][-_MAX_BUFFER_PER_DEVICE:]

    # 2. Update device position
    if packet.gps:
        _DEVICE_POSITIONS[device_id] = {
            "lat": packet.gps.lat,
            "lon": packet.gps.lon,
            "speed_kmh": packet.gps.speed_kmh,
            "heading_deg": packet.gps.heading_deg,
            "last_update": now,
        }

    # 3. Update device info
    _DEVICE_INFO[device_id] = {
        "device_id": device_id,
        "last_seen": now,
        "packets_received": len(_telemetry_buffer[device_id]),
        "battery": packet.system.battery_percent if packet.system else None,
        "signal": packet.system.signal_strength_dbm if packet.system else None,
    }

    # 4. Run crash detection
    crash_info = _detect_crash_from_telemetry(packet)
    incident_created = False

    if crash_info:
        # Create incident in the same pipeline
        incident = _create_incident_from_telemetry(packet, crash_info)
        if incident:
            incident_created = True

            # Broadcast via WebSocket
            await ws_manager.broadcast_event(
                WSEventType.INCIDENT_CREATED,
                incident,
                channel="incidents",
            )

            # Broadcast hardware alert
            await ws_manager.broadcast_event(
                WSEventType.EMERGENCY_ALERT,
                {
                    "title": f"Hardware Crash Alert - {packet.device_id}",
                    "message": (
                        f"Crash detected: {crash_info['classification']} "
                        f"({crash_info['impact_force_g']:.1f}g) at "
                        f"({packet.gps.lat:.4f}, {packet.gps.lon:.4f})"
                    ),
                    "severity": crash_info["severity"],
                    "source": "hardware_telemetry",
                    "device_id": device_id,
                    "timestamp": now,
                },
                channel="notifications",
            )

            logger.warning(
                f"CRASH DETECTED from hardware {device_id}: "
                f"{crash_info['classification']} ({crash_info['impact_force_g']:.1f}g)"
            )

    # 5. Broadcast device position update
    if packet.gps:
        await ws_manager.broadcast_event(
            WSEventType.HARDWARE_TELEMETRY,
            {
                "device_id": device_id,
                "latitude": packet.gps.lat,
                "longitude": packet.gps.lon,
                "speed_kmh": packet.gps.speed_kmh,
                "heading_deg": packet.gps.heading_deg,
                "crash_detected": crash_info is not None,
                "sos_active": packet.status_flags.sos_active if packet.status_flags else False,
                "battery": packet.system.battery_percent if packet.system else None,
                "signal": packet.system.signal_strength_dbm if packet.system else None,
                "timestamp": now,
            },
            channel="telemetry",
        )

    return {
        "status": "ok",
        "device_id": device_id,
        "crash_detected": crash_info is not None,
        "incident_created": incident_created,
        "timestamp": now,
    }


@router.get("/devices")
async def list_devices():
    """List all telemetry devices that have sent data."""
    return {
        "devices": [
            {
                "device_id": did,
                **_DEVICE_INFO.get(did, {}),
                "position": _DEVICE_POSITIONS.get(did),
                "buffer_size": len(_telemetry_buffer.get(did, [])),
            }
            for did in _DEVICE_INFO
        ],
        "total_devices": len(_DEVICE_INFO),
    }


@router.get("/devices/{device_id}")
async def get_device_telemetry(device_id: str, limit: int = 10):
    """Get recent telemetry data for a device."""
    buffer = _telemetry_buffer.get(device_id, [])
    return {
        "device_id": device_id,
        "info": _DEVICE_INFO.get(device_id),
        "position": _DEVICE_POSITIONS.get(device_id),
        "recent_telemetry": buffer[-limit:],
        "total_packets": len(buffer),
    }


@router.post("/simulate/crash")
async def simulate_crash(
    device_id: str = "RPi-PICO2W-SIM-001",
    lat: float = 12.9716,
    lon: float = 77.5946,
    impact_g: float = 8.5,
):
    """Manually simulate a crash from a hardware device."""
    from app.api.incidents import _incidents_store

    crash_info = {
        "severity": _compute_severity(impact_g),
        "classification": "SEVERE_CRASH" if impact_g >= 6.0 else "MODERATE_CRASH",
        "impact_force_g": impact_g,
        "speed_delta_kmh": impact_g * 5,
        "rollover": impact_g > 7.0,
        "confidence": min(0.95, impact_g / 8.0),
        "confidence_level": "HIGH",
    }

    # Build a minimal telemetry packet
    packet = TelemetryPacket(
        device_id=device_id,
        gps=GPSData(lat=lat, lon=lon, speed_kmh=0),
        crash_detection=CrashDetectionData(
            crash_flag=True,
            impact_force_g=impact_g,
            confidence=crash_info["confidence"],
        ),
    )

    incident = _create_incident_from_telemetry(packet, crash_info)
    if not incident:
        raise HTTPException(status_code=500, detail="Failed to create incident")

    # Broadcast
    await ws_manager.broadcast_event(WSEventType.INCIDENT_CREATED, incident, channel="incidents")
    await ws_manager.broadcast_event(
        WSEventType.EMERGENCY_ALERT,
        {
            "title": f"Simulated Crash - {device_id}",
            "message": f"Impact: {impact_g:.1f}g at ({lat:.4f}, {lon:.4f})",
            "severity": crash_info["severity"],
            "source": "crash_simulation",
            "timestamp": datetime.utcnow().isoformat(),
        },
        channel="notifications",
    )

    return {
        "status": "incident_created",
        "incident_id": incident["id"],
        "incident_number": incident["incident_number"],
        "crash_info": crash_info,
    }


@router.get("/stats")
async def telemetry_stats():
    """Get telemetry system statistics."""
    total_packets = sum(len(buf) for buf in _telemetry_buffer.values())
    return {
        "active_devices": len(_DEVICE_INFO),
        "total_packets_received": total_packets,
        "devices_with_positions": len(_DEVICE_POSITIONS),
        "buffer_capacity_per_device": _MAX_BUFFER_PER_DEVICE,
        "devices": [
            {
                "device_id": did,
                "packets": len(_telemetry_buffer.get(did, [])),
                "position": _DEVICE_POSITIONS.get(did),
            }
            for did in _DEVICE_INFO
        ],
    }