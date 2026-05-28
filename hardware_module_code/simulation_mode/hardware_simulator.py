"""
Hardware Module Laptop Simulator
=================================
Runs the same telemetry pipeline as real hardware on your laptop.
Feeds simulated sensor data into the backend telemetry endpoint.

Usage:
    python simulation_mode/hardware_simulator.py

This connects to:
    http://localhost:8000/api/telemetry/hardware

And streams telemetry packets identical to the embedded C++ firmware.
"""

import sys
import os
import json
import time
import math
import random
import logging
import threading
from datetime import datetime, timezone

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.imu_driver import MPU9250Driver
from sensors.gps_driver import GPSDriver, GPSReading
from network.sim7600_handler import SIM7600Handler, TelemetryPacket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("HardwareSimulator")


class HardwareSimulator:
    """
    Simulates the complete hardware telemetry unit on your laptop.
    Uses simulated IMU and GPS drivers, sends via httpx.
    """

    def __init__(
        self,
        device_id: str = "RPi-PICO2W-SIM-001",
        backend_url: str = "http://localhost:8000/api/telemetry/hardware",
        telemetry_interval_s: float = 1.0,
        sensor_interval_s: float = 0.02,  # 50 Hz
    ):
        self.device_id = device_id
        self.telemetry_interval = telemetry_interval_s
        self.sensor_interval = sensor_interval_s
        self._running = False
        self._thread = None

        # Initialize simulated modules
        self.imu = MPU9250Driver(simulation_mode=True)
        self.gps = GPSDriver(simulation_mode=True)
        self.network = SIM7600Handler(
            simulation_mode=True,
            backend_url=backend_url,
        )

        # Crash simulation state
        self._crash_scheduled: Optional[float] = None
        self._crash_triggered = False
        self._sos_active = False

        # Latest sensor readings
        self._last_imu = None
        self._last_gps = None
        self._crash_state = {
            "crash_flag": False,
            "impact_force_g": 0.0,
            "speed_delta_kmh": 0.0,
            "rollover_detected": False,
            "confidence": 0.0,
        }

    def start(self):
        """Start the simulation."""
        if self._running:
            return

        # Initialize modules
        self.imu.initialize()
        self.gps.initialize()
        self.gps.start_streaming(int(self.sensor_interval * 1000))
        self.network.initialize()

        self._running = True
        self._thread = threading.Thread(target=self._main_loop, daemon=True)
        self._thread.start()
        logger.info(f"Hardware simulator started (device: {self.device_id})")
        logger.info(f"Sending telemetry every {self.telemetry_interval}s to {self.network.backend_url}")

    def stop(self):
        """Stop the simulation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self.gps.stop_streaming()
        self.network.close()
        logger.info("Hardware simulator stopped")

    def schedule_crash(self, delay_seconds: float = 3.0, impact_g: float = 8.5):
        """Schedule a crash event to occur after delay."""
        self._crash_scheduled = time.time() + delay_seconds
        self._crash_impact = impact_g
        logger.warning(f"Crash scheduled in {delay_seconds}s ({impact_g}g impact)")

    def trigger_sos(self):
        """Manually trigger SOS."""
        self._sos_active = True
        logger.warning("SOS triggered")

    def clear_sos(self):
        """Clear SOS."""
        self._sos_active = False

    def _main_loop(self):
        """Main telemetry loop."""
        last_telemetry = 0.0
        imu_history = []  # For crash detection

        while self._running:
            now = time.time()

            # Read sensors at high frequency
            imu_reading = self.imu.read()
            if imu_reading:
                self._last_imu = imu_reading
                imu_history.append(imu_reading)
                if len(imu_history) > 50:
                    imu_history.pop(0)

                # Run crash detection on IMU data
                self._detect_crash(imu_reading, imu_history)

            # Check scheduled crash
            if self._crash_scheduled and now >= self._crash_scheduled:
                self._simulate_crash_event()
                self._crash_scheduled = None

            # Get latest GPS
            self._last_gps = self.gps.get_last_reading()

            # Send telemetry at configured interval
            if now - last_telemetry >= self.telemetry_interval:
                packet = self._build_telemetry_packet()
                success = self.network.send_telemetry(packet)
                if success:
                    logger.debug(
                        f"Telemetry: GPS({self._last_gps.latitude:.4f},"
                        f"{self._last_gps.longitude:.4f}) "
                        f"Spd={self._last_gps.speed_kmh:.0f} "
                        f"Crash={self._crash_state['crash_flag']}"
                    )
                last_telemetry = now

            time.sleep(self.sensor_interval)

    def _detect_crash(self, reading, history: list):
        """Run crash detection algorithm matching embedded code."""
        # Total acceleration magnitude (minus gravity)
        ax = reading.accel_x
        ay = reading.accel_y
        az = reading.accel_z - 1.0
        total_accel = math.sqrt(ax * ax + ay * ay + az * az)

        # Impact detection
        if total_accel >= 4.0:
            self._crash_state["crash_flag"] = True
            self._crash_state["impact_force_g"] = total_accel
            self._crash_state["confidence"] = min(1.0, total_accel / 10.0)

        # Rollover detection
        gravity_angle = reading.gravity_angle_degrees()
        if gravity_angle > 45.0:
            self._crash_state["rollover_detected"] = True
            self._crash_state["confidence"] = max(
                self._crash_state["confidence"], 0.7
            )

        # Speed delta from history
        if len(history) >= 5:
            prev = history[-5]
            dx = reading.accel_x - prev.accel_x
            dy = reading.accel_y - prev.accel_y
            dz = reading.accel_z - prev.accel_z
            delta = math.sqrt(dx * dx + dy * dy + dz * dz)
            if delta > 2.0:
                self._crash_state["speed_delta_kmh"] = delta * 9.81 * 0.1

    def _simulate_crash_event(self):
        """Simulate a crash by overriding sensor values."""
        self._crash_triggered = True
        self._crash_state["crash_flag"] = True
        self._crash_state["impact_force_g"] = self._crash_impact
        self._crash_state["confidence"] = 0.95
        self._sos_active = True
        logger.critical(
            f"*** CRASH EVENT SIMULATED *** "
            f"Impact: {self._crash_impact:.1f}g"
        )

    def _build_telemetry_packet(self) -> TelemetryPacket:
        """Build a standard telemetry packet."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # GPS data
        gps_data = None
        if self._last_gps:
            gps_data = self._last_gps.to_dict()

        # IMU data
        imu_data = None
        if self._last_imu:
            imu_data = {
                "x": round(self._last_imu.accel_x, 4),
                "y": round(self._last_imu.accel_y, 4),
                "z": round(self._last_imu.accel_z, 4),
                "scale": "±2g",
            }
            gyro_data = {
                "x": round(self._last_imu.gyro_x, 4),
                "y": round(self._last_imu.gyro_y, 4),
                "z": round(self._last_imu.gyro_z, 4),
                "scale": "±250dps",
            }
        else:
            imu_data = {"x": 0.0, "y": 0.0, "z": 9.81, "scale": "±2g"}
            gyro_data = {"x": 0.0, "y": 0.0, "z": 0.0, "scale": "±250dps"}

        return TelemetryPacket(
            device_id=self.device_id,
            timestamp=now_iso,
            telemetry_version="1.0",
            gps=gps_data,
            accelerometer=imu_data,
            gyroscope=gyro_data,
            imu_temperature_c=32.5,
            system={
                "battery_percent": random.randint(75, 95),
                "cpu_temp_c": 42.0 + random.gauss(0, 2),
                "uptime_seconds": int(time.time() % 86400),
                "free_memory_kb": 128000,
                "signal_strength_dbm": -75 + random.randint(-10, 5),
                "network_type": "LTE",
                "firmware_version": "v1.0.0",
            },
            crash_detection={
                "crash_flag": self._crash_state["crash_flag"],
                "impact_force_g": round(self._crash_state["impact_force_g"], 1),
                "speed_delta_kmh": round(self._crash_state["speed_delta_kmh"], 1),
                "rollover_detected": self._crash_state["rollover_detected"],
                "confidence": round(self._crash_state["confidence"], 2),
                "detection_algorithm": "mpu9250_threshold",
            },
            status_flags={
                "sos_active": self._sos_active,
                "emergency_brake": False,
                "airbag_deployed": self._crash_state["crash_flag"],
                "ignition_on": True,
                "vehicle_stopped": (
                    self._last_gps.speed_kmh < 1.0 if self._last_gps else True
                ),
            },
        )

    def get_stats(self) -> dict:
        return {
            "device_id": self.device_id,
            "running": self._running,
            "packets_sent": self.network.packets_sent,
            "packets_failed": self.network.packets_failed,
            "crash_detected": self._crash_state["crash_flag"],
            "sos_active": self._sos_active,
            "network_stats": self.network.get_stats(),
        }


# ── CLI Entry Point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import signal
    import argparse

    parser = argparse.ArgumentParser(description="RoadSoS Hardware Simulator")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/telemetry/hardware",
        help="Backend URL for telemetry",
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Telemetry send interval (seconds)",
    )
    parser.add_argument(
        "--crash-after", type=float, default=0,
        help="Auto-trigger crash after N seconds (0 = disabled)",
    )
    parser.add_argument(
        "--device-id", default="RPi-PICO2W-SIM-001",
        help="Simulated device ID",
    )
    args = parser.parse_args()

    sim = HardwareSimulator(
        device_id=args.device_id,
        backend_url=args.url,
        telemetry_interval_s=args.interval,
    )

    def signal_handler(sig, frame):
        print("\nStopping hardware simulator...")
        sim.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    sim.start()

    if args.crash_after > 0:
        sim.schedule_crash(delay_seconds=args.crash_after)

    print(f"Hardware simulator running. Press Ctrl+C to stop.")
    print(f"Device: {args.device_id}")
    print(f"Backend: {args.url}")
    print(f"Telemetry interval: {args.interval}s")

    try:
        while sim._running:
            time.sleep(5)
            stats = sim.get_stats()
            print(
                f"  Packets: {stats['packets_sent']} sent, "
                f"{stats['packets_failed']} failed | "
                f"Crash: {stats['crash_detected']} | "
                f"SOS: {stats['sos_active']}"
            )
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()