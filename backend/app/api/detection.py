"""
Accident Detection API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.engines.accident_detection import detection_engine, SensorReading
from app.config import settings

router = APIRouter(prefix="/api/detection", tags=["Accident Detection"])


class SensorPayload(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    timestamp: Optional[float] = Field(default=None)
    # Accelerometer
    accel_x: float = Field(default=0.0, description="Accelerometer X axis (m/s²)")
    accel_y: float = Field(default=0.0)
    accel_z: float = Field(default=9.81)
    # Gyroscope
    gyro_x: float = Field(default=0.0, description="Gyroscope X axis (deg/s)")
    gyro_y: float = Field(default=0.0)
    gyro_z: float = Field(default=0.0)
    # GPS
    latitude: float = Field(..., description="GPS latitude")
    longitude: float = Field(..., description="GPS longitude")
    speed_kmh: float = Field(default=0.0, description="Current speed in km/h")
    heading: float = Field(default=0.0, description="Compass heading in degrees")
    # Sound
    sound_db: float = Field(default=40.0, description="Ambient sound level in dB")


class DetectionResponse(BaseModel):
    crash_probability_score: float
    severity: str
    confidence_level: str
    event_classification: str
    is_crash: bool
    is_suspected: bool
    impact_force_g: float
    speed_delta_kmh: float
    rollover_detected: bool
    contributing_signals: list
    sensor_snapshot: dict
    timestamp: str
    action_required: str


@router.post("/analyze", response_model=DetectionResponse)
async def analyze_sensor_data(payload: SensorPayload):
    """
    Analyze sensor data and return crash detection result.
    
    This is the core detection endpoint. Send sensor readings from a vehicle
    device and receive a crash probability score, severity estimate, and
    event classification.
    """
    import time

    reading = SensorReading(
        timestamp=payload.timestamp or time.time(),
        accel_x=payload.accel_x,
        accel_y=payload.accel_y,
        accel_z=payload.accel_z,
        gyro_x=payload.gyro_x,
        gyro_y=payload.gyro_y,
        gyro_z=payload.gyro_z,
        latitude=payload.latitude,
        longitude=payload.longitude,
        speed_kmh=payload.speed_kmh,
        heading=payload.heading,
        sound_db=payload.sound_db,
        device_id=payload.device_id,
    )

    result = detection_engine.process_reading(reading)

    # Determine action
    if result.is_crash:
        action = "DISPATCH_EMERGENCY"
    elif result.is_suspected:
        action = "REQUEST_CONFIRMATION"
    else:
        action = "CONTINUE_MONITORING"

    return DetectionResponse(
        crash_probability_score=result.crash_probability_score,
        severity=result.severity,
        confidence_level=result.confidence_level,
        event_classification=result.event_classification,
        is_crash=result.is_crash,
        is_suspected=result.is_suspected,
        impact_force_g=result.impact_force_g,
        speed_delta_kmh=result.speed_delta_kmh,
        rollover_detected=result.rollover_detected,
        contributing_signals=result.contributing_signals,
        sensor_snapshot=result.sensor_snapshot,
        timestamp=datetime.utcnow().isoformat(),
        action_required=action,
    )


@router.post("/simulate/{scenario}")
async def simulate_scenario(scenario: str):
    """
    Simulate a specific crash scenario and return detection results.
    
    Scenarios: NORMAL_BRAKING, POTHOLE, SPEED_BREAKER, MINOR_COLLISION,
               MODERATE_CRASH, SEVERE_CRASH, ROLLOVER
    """
    from app.demo.simulator import demo_simulator

    valid_scenarios = ["NORMAL_BRAKING", "POTHOLE", "SPEED_BREAKER",
                       "MINOR_COLLISION", "MODERATE_CRASH", "SEVERE_CRASH", "ROLLOVER"]

    if scenario.upper() not in valid_scenarios:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario. Choose from: {valid_scenarios}"
        )

    readings = demo_simulator.generate_sensor_stream(scenario.upper())
    results = []

    for reading_data in readings:
        import time
        reading = SensorReading(
            timestamp=reading_data["timestamp"],
            accel_x=reading_data["accel_x"],
            accel_y=reading_data["accel_y"],
            accel_z=reading_data["accel_z"],
            gyro_x=reading_data["gyro_x"],
            gyro_y=reading_data["gyro_y"],
            gyro_z=reading_data["gyro_z"],
            speed_kmh=reading_data["speed_kmh"],
            sound_db=reading_data["sound_db"],
            latitude=12.9716,
            longitude=77.5946,
            device_id="DEMO_DEVICE",
        )
        result = detection_engine.process_reading(reading)
        results.append({
            "reading_index": len(results),
            "event_label": reading_data.get("event", "UNKNOWN"),
            "crash_probability_score": result.crash_probability_score,
            "event_classification": result.event_classification,
            "severity": result.severity,
            "is_crash": result.is_crash,
        })

    return {
        "scenario": scenario.upper(),
        "total_readings": len(results),
        "crash_detected": any(r["is_crash"] for r in results),
        "max_probability": max(r["crash_probability_score"] for r in results),
        "readings": results,
    }


@router.get("/thresholds")
async def get_detection_thresholds():
    """Return current detection threshold configuration."""
    return {
        "crash_confirm_threshold": settings.CRASH_CONFIRM_THRESHOLD,
        "crash_suspect_threshold": settings.CRASH_SUSPECT_THRESHOLD,
        "sound_intensity_threshold_db": settings.SOUND_INTENSITY_THRESHOLD_DB,
        "sound_score_boost": settings.SOUND_SCORE_BOOST,
        "sliding_window_size": 3,
        "severity_levels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "event_classifications": [
            "CRASH", "ROLLOVER_CRASH", "HIGH_IMPACT_CRASH",
            "SUSPECTED_CRASH", "NORMAL_BRAKING", "POTHOLE",
            "SPEED_BREAKER", "NORMAL"
        ],
    }
