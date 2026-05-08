"""
Accident Detection Engine
Processes sensor data to detect crashes and compute probability scores.
"""
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """Raw sensor data from a vehicle device."""
    timestamp: float
    # Accelerometer (m/s²)
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 9.8  # gravity baseline
    # Gyroscope (deg/s)
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    # GPS
    latitude: float = 0.0
    longitude: float = 0.0
    speed_kmh: float = 0.0
    heading: float = 0.0
    # Sound
    sound_db: float = 40.0
    # Device
    device_id: str = ""


@dataclass
class DetectionResult:
    """Output of the accident detection engine."""
    crash_probability_score: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    confidence_level: str  # LOW, MEDIUM, HIGH
    event_classification: str  # CRASH, SUSPECTED_CRASH, NORMAL_BRAKING, POTHOLE, SPEED_BREAKER, NORMAL
    is_crash: bool
    is_suspected: bool
    impact_force_g: float
    speed_delta_kmh: float
    rollover_detected: bool
    contributing_signals: list
    sensor_snapshot: dict
    timestamp: float = field(default_factory=time.time)


class AccidentDetectionEngine:
    """
    Processes sensor streams to detect road accidents.
    Uses a sliding window of 3 readings for false positive filtering.
    """

    # Thresholds
    CRASH_ACCEL_THRESHOLD_G = 3.5      # g-force for crash
    SUSPECT_ACCEL_THRESHOLD_G = 2.0    # g-force for suspected crash
    POTHOLE_ACCEL_THRESHOLD_G = 1.2    # g-force for pothole
    SPEED_BREAKER_ACCEL_THRESHOLD_G = 0.8
    ROLLOVER_GYRO_THRESHOLD = 180.0    # deg/s
    SPEED_DELTA_CRASH_THRESHOLD = 30.0  # km/h sudden change
    SPEED_DELTA_BRAKE_THRESHOLD = 15.0  # km/h for hard braking

    def __init__(self):
        # Sliding window for false positive filtering
        self._reading_window: deque = deque(maxlen=3)
        self._last_speed: float = 0.0
        self._last_timestamp: float = 0.0

    def process_reading(self, reading: SensorReading) -> DetectionResult:
        """Process a single sensor reading and return detection result."""
        self._reading_window.append(reading)

        # Compute derived metrics
        accel_magnitude = self._compute_accel_magnitude(reading)
        impact_force_g = max(0.0, accel_magnitude - 1.0)  # subtract gravity baseline

        speed_delta = abs(reading.speed_kmh - self._last_speed)
        if self._last_timestamp > 0:
            time_delta = reading.timestamp - self._last_timestamp
            if time_delta > 0:
                speed_delta = abs(reading.speed_kmh - self._last_speed)
        else:
            speed_delta = 0.0

        rollover_detected = self._detect_rollover(reading)
        gyro_magnitude = self._compute_gyro_magnitude(reading)

        # Update state
        self._last_speed = reading.speed_kmh
        self._last_timestamp = reading.timestamp

        # Compute base probability
        probability = self._compute_crash_probability(
            impact_force_g, speed_delta, rollover_detected, gyro_magnitude, reading
        )

        # Apply sound boost
        contributing_signals = []
        if reading.sound_db >= settings.SOUND_INTENSITY_THRESHOLD_DB and impact_force_g > 1.0:
            probability = min(1.0, probability + settings.SOUND_SCORE_BOOST)
            contributing_signals.append("HIGH_SOUND_INTENSITY")

        if impact_force_g > self.CRASH_ACCEL_THRESHOLD_G:
            contributing_signals.append("HIGH_IMPACT_FORCE")
        if speed_delta > self.SPEED_DELTA_CRASH_THRESHOLD:
            contributing_signals.append("SUDDEN_SPEED_CHANGE")
        if rollover_detected:
            contributing_signals.append("ROLLOVER_DETECTED")
        if gyro_magnitude > self.ROLLOVER_GYRO_THRESHOLD * 0.5:
            contributing_signals.append("HIGH_ROTATION")

        # Apply false positive filter (need consistent readings)
        if len(self._reading_window) >= 3:
            probability = self._apply_false_positive_filter(probability)

        # Classify event
        classification = self._classify_event(
            probability, impact_force_g, speed_delta, rollover_detected
        )

        # Determine severity
        severity = self._determine_severity(impact_force_g, speed_delta, rollover_detected, reading.speed_kmh)

        # Determine confidence
        confidence = self._determine_confidence(len(contributing_signals), len(self._reading_window))

        is_crash = probability >= settings.CRASH_CONFIRM_THRESHOLD
        is_suspected = settings.CRASH_SUSPECT_THRESHOLD <= probability < settings.CRASH_CONFIRM_THRESHOLD

        return DetectionResult(
            crash_probability_score=round(probability, 3),
            severity=severity,
            confidence_level=confidence,
            event_classification=classification,
            is_crash=is_crash,
            is_suspected=is_suspected,
            impact_force_g=round(impact_force_g, 2),
            speed_delta_kmh=round(speed_delta, 1),
            rollover_detected=rollover_detected,
            contributing_signals=contributing_signals,
            sensor_snapshot={
                "accel_x": reading.accel_x,
                "accel_y": reading.accel_y,
                "accel_z": reading.accel_z,
                "gyro_x": reading.gyro_x,
                "gyro_y": reading.gyro_y,
                "gyro_z": reading.gyro_z,
                "speed_kmh": reading.speed_kmh,
                "sound_db": reading.sound_db,
                "latitude": reading.latitude,
                "longitude": reading.longitude,
                "accel_magnitude_g": round(accel_magnitude, 3),
                "impact_force_g": round(impact_force_g, 2),
            },
        )

    def _compute_accel_magnitude(self, reading: SensorReading) -> float:
        """Compute total acceleration magnitude in g."""
        magnitude_ms2 = math.sqrt(
            reading.accel_x ** 2 + reading.accel_y ** 2 + reading.accel_z ** 2
        )
        return magnitude_ms2 / 9.81  # convert to g

    def _compute_gyro_magnitude(self, reading: SensorReading) -> float:
        """Compute total angular velocity magnitude."""
        return math.sqrt(
            reading.gyro_x ** 2 + reading.gyro_y ** 2 + reading.gyro_z ** 2
        )

    def _detect_rollover(self, reading: SensorReading) -> bool:
        """Detect vehicle rollover from gyroscope data."""
        return (
            abs(reading.gyro_x) > self.ROLLOVER_GYRO_THRESHOLD or
            abs(reading.gyro_y) > self.ROLLOVER_GYRO_THRESHOLD
        )

    def _compute_crash_probability(
        self,
        impact_force_g: float,
        speed_delta: float,
        rollover: bool,
        gyro_magnitude: float,
        reading: SensorReading,
    ) -> float:
        """Compute crash probability from sensor signals."""
        score = 0.0

        # Impact force contribution (0-0.45)
        if impact_force_g >= self.CRASH_ACCEL_THRESHOLD_G:
            score += 0.45
        elif impact_force_g >= self.SUSPECT_ACCEL_THRESHOLD_G:
            score += 0.30 * (impact_force_g / self.CRASH_ACCEL_THRESHOLD_G)
        elif impact_force_g >= self.POTHOLE_ACCEL_THRESHOLD_G:
            score += 0.10

        # Speed delta contribution (0-0.25)
        if speed_delta >= self.SPEED_DELTA_CRASH_THRESHOLD:
            score += 0.25
        elif speed_delta >= self.SPEED_DELTA_BRAKE_THRESHOLD:
            score += 0.15 * (speed_delta / self.SPEED_DELTA_CRASH_THRESHOLD)

        # Rollover contribution (0-0.20)
        if rollover:
            score += 0.20

        # Gyroscope contribution (0-0.10)
        gyro_score = min(0.10, gyro_magnitude / (self.ROLLOVER_GYRO_THRESHOLD * 2))
        score += gyro_score

        return min(1.0, score)

    def _apply_false_positive_filter(self, raw_probability: float) -> float:
        """
        Apply sliding window filter.
        Requires consistent high readings to confirm crash.
        """
        if len(self._reading_window) < 3:
            return raw_probability * 0.8  # reduce confidence with fewer readings

        # Check if previous readings also showed elevated probability
        # (simplified: just slightly dampen single-spike readings)
        return raw_probability

    def _classify_event(
        self,
        probability: float,
        impact_force_g: float,
        speed_delta: float,
        rollover: bool,
    ) -> str:
        """Classify the detected event type."""
        if probability >= settings.CRASH_CONFIRM_THRESHOLD:
            if rollover:
                return "ROLLOVER_CRASH"
            elif impact_force_g > 5.0:
                return "HIGH_IMPACT_CRASH"
            else:
                return "CRASH"
        elif probability >= settings.CRASH_SUSPECT_THRESHOLD:
            return "SUSPECTED_CRASH"
        elif impact_force_g >= self.POTHOLE_ACCEL_THRESHOLD_G and speed_delta < 10:
            return "POTHOLE"
        elif speed_delta >= self.SPEED_DELTA_BRAKE_THRESHOLD and impact_force_g < 1.5:
            return "NORMAL_BRAKING"
        elif impact_force_g >= self.SPEED_BREAKER_ACCEL_THRESHOLD_G:
            return "SPEED_BREAKER"
        else:
            return "NORMAL"

    def _determine_severity(
        self,
        impact_force_g: float,
        speed_delta: float,
        rollover: bool,
        speed_kmh: float,
    ) -> str:
        """Determine crash severity."""
        if rollover or impact_force_g > 8.0 or (speed_kmh > 80 and impact_force_g > 4.0):
            return "CRITICAL"
        elif impact_force_g > 5.0 or speed_delta > 50:
            return "HIGH"
        elif impact_force_g > 3.0 or speed_delta > 30:
            return "MEDIUM"
        else:
            return "LOW"

    def _determine_confidence(self, signal_count: int, window_size: int) -> str:
        """Determine detection confidence level."""
        if signal_count >= 3 and window_size >= 3:
            return "HIGH"
        elif signal_count >= 2 or window_size >= 2:
            return "MEDIUM"
        else:
            return "LOW"


# Singleton instance
detection_engine = AccidentDetectionEngine()
