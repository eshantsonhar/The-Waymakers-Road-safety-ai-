"""
NEO-M8N GPS Driver (Python Abstraction)
=========================================
Parses NMEA sentences from NEO-M8N GPS module via serial.
Supports both real hardware and simulation modes.

Protocol:
- $GPRMC: Recommended Minimum (position, speed, course)
- $GPGGA: Fix data (altitude, satellites, HDOP)
"""

import time
import math
import random
import threading
from typing import Optional, Callable
from collections import deque


class GPSReading:
    """Represents a single GPS position reading."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        altitude_m: float = 0.0,
        speed_kmh: float = 0.0,
        heading_deg: float = 0.0,
        accuracy_m: float = 5.0,
        satellites: int = 0,
        fix_quality: int = 0,
        timestamp: Optional[float] = None,
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude_m = altitude_m
        self.speed_kmh = speed_kmh
        self.heading_deg = heading_deg
        self.accuracy_m = accuracy_m
        self.satellites = satellites
        self.fix_quality = fix_quality  # 0=no fix, 1=GPS, 2=DGPS
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "lat": round(self.latitude, 6),
            "lon": round(self.longitude, 6),
            "altitude_m": round(self.altitude_m, 1),
            "speed_kmh": round(self.speed_kmh, 1),
            "heading_deg": round(self.heading_deg, 1),
            "accuracy_m": round(self.accuracy_m, 1),
            "satellites": self.satellites,
            "fix_quality": self.fix_quality,
            "timestamp": self.timestamp,
        }

    def has_fix(self) -> bool:
        return self.fix_quality > 0 and self.satellites >= 4

    def distance_to(self, other: 'GPSReading') -> float:
        """Haversine distance in meters."""
        R = 6371000.0
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GPSDriver:
    """
    GPS driver for NEO-M8N module.
    Supports real serial port or simulation mode.
    """

    # Bangalore circuit for simulation
    BANGALORE_CIRCUIT = [
        (12.9716, 77.5946),  # MG Road
        (12.9757, 77.6011),  # MG Road east
        (12.9719, 77.6069),  # Brigade Road
        (12.9700, 77.6100),  # Residency Road
        (12.9670, 77.6140),  # Richmond Road
        (12.9650, 77.6180),  # Shoolay Circle
        (12.9600, 77.6200),  # Kanteerava
        (12.9550, 77.6180),  # Town Hall
        (12.9500, 77.6150),  # Lalbagh
        (12.9550, 77.6100),  # Lalbagh Road
        (12.9600, 77.6050),  # Double Road
        (12.9650, 77.6000),  # Shoolay
        (12.9680, 77.5960),  # St Patrick's
    ]

    def __init__(
        self,
        simulation_mode: bool = True,
        serial_port: str = "/dev/ttyAMA0",
        baud_rate: int = 9600,
        on_reading: Optional[Callable[[GPSReading], None]] = None,
    ):
        self.simulation_mode = simulation_mode
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.on_reading = on_reading
        self._serial = None
        self._running = False
        self._thread = None
        self._last_reading: Optional[GPSReading] = None

        # Simulation state
        self._sim_idx = 0
        self._sim_progress = 0.0
        self._sim_speed = 30.0  # km/h
        self._sim_heading = 0.0

    def initialize(self) -> bool:
        """Initialize GPS module."""
        if self.simulation_mode:
            self._running = True
            print(f"[GPS] Simulation mode initialized")
            print(f"[GPS] Bangalore circuit: {len(self.BANGALORE_CIRCUIT)} waypoints")
            return True

        try:
            import serial
            self._serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1.0,
            )
            self._running = True
            print(f"[GPS] Hardware GPS on {self.serial_port} initialized")
            return True
        except ImportError:
            print("[GPS] pyserial not available, falling back to simulation")
            self.simulation_mode = True
            self._running = True
            return True
        except Exception as e:
            print(f"[GPS] Hardware init failed: {e}, using simulation")
            self.simulation_mode = True
            self._running = True
            return True

    def start_streaming(self, interval_ms: int = 1000):
        """Start background thread that reads GPS at interval."""
        if self._thread and self._thread.is_alive():
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._stream_loop,
            args=(interval_ms / 1000.0,),
            daemon=True,
        )
        self._thread.start()
        print(f"[GPS] Streaming started ({interval_ms}ms interval)")

    def stop_streaming(self):
        """Stop background GPS reading."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def read(self) -> Optional[GPSReading]:
        """Read one GPS position."""
        if not self._running:
            return None

        if self.simulation_mode:
            return self._simulate_reading()

        return self._parse_nmea_serial()

    def get_last_reading(self) -> Optional[GPSReading]:
        return self._last_reading

    def _stream_loop(self, interval_seconds: float):
        """Background loop for continuous GPS reading."""
        while self._running:
            reading = self.read()
            if reading:
                self._last_reading = reading
                if self.on_reading:
                    self.on_reading(reading)
            time.sleep(interval_seconds)

    def _simulate_reading(self) -> GPSReading:
        """Generate a simulated GPS position along Bangalore circuit."""
        idx = self._sim_idx
        next_idx = (idx + 1) % len(self.BANGALORE_CIRCUIT)
        p1 = self.BANGALORE_CIRCUIT[idx]
        p2 = self.BANGALORE_CIRCUIT[next_idx]

        # Advance along route
        speed_factor = self._sim_speed * 0.00001
        self._sim_progress += speed_factor
        if self._sim_progress >= 1.0:
            self._sim_progress = 0.0
            self._sim_idx = next_idx

        # Interpolate
        lat = p1[0] + (p2[0] - p1[0]) * self._sim_progress
        lon = p1[1] + (p2[1] - p1[1]) * self._sim_progress

        # Add GPS jitter
        lat += random.gauss(0, 0.000005)
        lon += random.gauss(0, 0.000005)

        # Compute heading
        dlat = p2[0] - p1[0]
        dlon = p2[1] - p1[1]
        heading = (math.degrees(math.atan2(dlon, dlat)) + 360) % 360

        # Simulate varying conditions
        satellites = random.randint(6, 12)
        fix_quality = 1 if satellites >= 4 else 0
        accuracy = max(2.0, 10.0 - satellites + random.gauss(0, 1))
        speed_var = self._sim_speed + random.gauss(0, 2)

        return GPSReading(
            latitude=lat,
            longitude=lon,
            altitude_m=920.0 + random.gauss(0, 5),
            speed_kmh=max(0, speed_var),
            heading_deg=heading,
            accuracy_m=accuracy,
            satellites=satellites,
            fix_quality=fix_quality,
        )

    def _parse_nmea_serial(self) -> Optional[GPSReading]:
        """Read and parse NMEA sentences from serial port."""
        if not self._serial or not self._serial.is_open:
            return None

        try:
            lat = lon = alt = speed = heading = 0.0
            satellites = fix_quality = 0
            accuracy = 50.0
            has_pos = False

            timeout = time.time() + 1.0
            while time.time() < timeout:
                line = self._serial.readline().decode('ascii', errors='ignore').strip()
                if not line:
                    continue

                if line.startswith('$GPRMC'):
                    parts = line.split(',')
                    if len(parts) >= 8 and parts[2] == 'A':  # Active fix
                        # Parse position
                        lat_raw = float(parts[3]) if parts[3] else 0.0
                        ns = parts[4]
                        lon_raw = float(parts[5]) if parts[5] else 0.0
                        ew = parts[6]
                        speed_knots = float(parts[7]) if parts[7] else 0.0
                        course = float(parts[8]) if len(parts) > 8 and parts[8] else 0.0

                        # Convert NMEA to decimal
                        lat_deg = int(lat_raw / 100)
                        lat_min = lat_raw - (lat_deg * 100)
                        lat = lat_deg + lat_min / 60.0
                        if ns == 'S':
                            lat = -lat

                        lon_deg = int(lon_raw / 100)
                        lon_min = lon_raw - (lon_deg * 100)
                        lon = lon_deg + lon_min / 60.0
                        if ew == 'W':
                            lon = -lon

                        speed = speed_knots * 1.852  # knots to km/h
                        heading = course
                        has_pos = True

                elif line.startswith('$GPGGA'):
                    parts = line.split(',')
                    if len(parts) >= 9:
                        fix_quality = int(parts[6]) if parts[6] else 0
                        satellites = int(parts[7]) if parts[7] else 0
                        hdop = float(parts[8]) if parts[8] else 99.0
                        alt = float(parts[9]) if len(parts) > 9 and parts[9] else 0.0
                        accuracy = hdop * 5.0  # HDOP to meters

                if has_pos:
                    return GPSReading(
                        latitude=lat, longitude=lon,
                        altitude_m=alt, speed_kmh=speed,
                        heading_deg=heading, accuracy_m=accuracy,
                        satellites=satellites, fix_quality=fix_quality,
                    )

            return None

        except Exception as e:
            print(f"[GPS] Parse error: {e}")
            return None

    def close(self):
        """Clean up serial resources."""
        self.stop_streaming()
        if self._serial and self._serial.is_open:
            self._serial.close()