"""
SIM7600E-H Network Handler (Python Abstraction)
=================================================
Handles 4G LTE connectivity, HTTP POST telemetry, and SMS alerts.

For the laptop simulation mode, this uses requests/httpx instead
of AT commands over serial.
"""

import json
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TelemetryPacket:
    """Standard telemetry packet matching the protocol schema."""
    device_id: str
    timestamp: str
    telemetry_version: str = "1.0"
    gps: Optional[dict] = None
    accelerometer: Optional[dict] = None
    gyroscope: Optional[dict] = None
    magnetometer: Optional[dict] = None
    imu_temperature_c: Optional[float] = None
    system: Optional[dict] = None
    crash_detection: Optional[dict] = None
    status_flags: Optional[dict] = None


class SIM7600Handler:
    """
    SIM7600E-H network handler.
    In simulation mode, sends HTTP requests via httpx/requests.
    In hardware mode, uses AT commands over serial.
    """

    def __init__(
        self,
        simulation_mode: bool = True,
        backend_url: str = "http://localhost:8000/api/telemetry/hardware",
        serial_port: str = "/dev/ttyS0",
        baud_rate: int = 115200,
        on_telemetry_sent: Optional[Callable[[bool, str], None]] = None,
    ):
        self.simulation_mode = simulation_mode
        self.backend_url = backend_url
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.on_telemetry_sent = on_telemetry_sent
        self._serial = None
        self._initialized = False
        self._pending_sms: list = []

        # Statistics
        self.packets_sent = 0
        self.packets_failed = 0
        self.last_signal_strength = -75  # dBm

    def initialize(self) -> bool:
        """Initialize the modem."""
        if self.simulation_mode:
            self._initialized = True
            logger.info("[SIM7600] Simulation mode initialized")
            logger.info(f"[SIM7600] Backend URL: {self.backend_url}")
            return True

        try:
            import serial
            self._serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=2.0,
            )
            # Send AT to check modem
            self._at_command("AT")
            resp = self._at_command("AT+CREG?")
            self._initialized = True
            logger.info("[SIM7600] Hardware modem initialized")
            return True
        except ImportError:
            logger.warning("[SIM7600] pyserial not available, using simulation")
            self.simulation_mode = True
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"[SIM7600] Hardware init failed: {e}, using simulation")
            self.simulation_mode = True
            self._initialized = True
            return True

    def send_telemetry(self, packet: TelemetryPacket) -> bool:
        """Send a telemetry packet to the backend."""
        if not self._initialized:
            return False

        json_data = json.dumps(asdict(packet), default=str)

        if self.simulation_mode:
            return self._http_send(json_data)

        return self._at_http_post(json_data)

    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send an SMS alert."""
        if self.simulation_mode:
            logger.info(f"[SIM7600] SMS to {phone_number}: {message}")
            return True

        cmd = f'AT+CMGS="{phone_number}"'
        self._at_command(cmd)
        time.sleep(0.2)
        self._at_command(message)
        time.sleep(0.1)
        self._serial.write(bytes([0x1A]))  # Ctrl+Z
        time.sleep(1.0)
        return True

    def check_signal(self) -> int:
        """Check signal strength in dBm."""
        if self.simulation_mode:
            return self.last_signal_strength

        resp = self._at_command("AT+CSQ")
        # Parse response: +CSQ: <rssi>,<ber>
        try:
            parts = resp.split(":")[1].strip().split(",")
            rssi = int(parts[0])
            if rssi == 99:
                return -120  # Not detectable
            dBm = -113 + (rssi * 2)  # Convert to dBm
            self.last_signal_strength = dBm
            return dBm
        except (IndexError, ValueError):
            return -120

    def get_network_type(self) -> str:
        """Get current network type."""
        if self.simulation_mode:
            return "LTE"

        resp = self._at_command("AT+COPS?")
        if "CHT" in resp or "AIRTEL" in resp or "JIO" in resp:
            return "4G/LTE"
        return "Unknown"

    def _http_send(self, json_data: str) -> bool:
        """Send HTTP POST in simulation mode."""
        try:
            import httpx
            resp = httpx.post(
                self.backend_url,
                content=json_data,
                headers={"Content-Type": "application/json"},
                timeout=5.0,
            )
            success = resp.status_code == 200
            if success:
                self.packets_sent += 1
                logger.debug(f"[SIM7600] Telemetry sent (packet #{self.packets_sent})")
            else:
                self.packets_failed += 1
                logger.warning(f"[SIM7600] HTTP {resp.status_code}: {resp.text[:200]}")
            if self.on_telemetry_sent:
                self.on_telemetry_sent(success, resp.text[:200])
            return success
        except httpx.TimeoutException:
            self.packets_failed += 1
            logger.warning("[SIM7600] HTTP timeout")
            return False
        except Exception as e:
            self.packets_failed += 1
            logger.warning(f"[SIM7600] HTTP error: {e}")
            return False

    def _at_command(self, command: str) -> str:
        """Send an AT command and read response."""
        if not self._serial or not self._serial.is_open:
            return ""

        self._serial.write((command + "\r\n").encode())
        time.sleep(0.3)

        response = ""
        timeout = time.time() + 1.0
        while time.time() < timeout:
            if self._serial.in_waiting:
                response += self._serial.read(self._serial.in_waiting).decode(errors='ignore')
            else:
                break

        return response.strip()

    def _at_http_post(self, json_data: str) -> bool:
        """Send HTTP POST via SIM7600 AT commands."""
        if not self._serial:
            return False

        try:
            # Set URL
            self._at_command(f'AT+HTTPPARA="URL","{self.backend_url}"')
            # Set content type
            self._at_command('AT+HTTPPARA="CONTENT","application/json"')
            # Set data length
            self._at_command(f"AT+HTTPDATA={len(json_data)},5000")
            time.sleep(0.3)
            # Send data
            self._serial.write(json_data.encode())
            time.sleep(1.0)
            # Execute POST
            resp = self._at_command("AT+HTTPACTION=1")
            time.sleep(2.0)

            if "+HTTPACTION: 0,200" in resp:
                self.packets_sent += 1
                return True

            self.packets_failed += 1
            return False

        except Exception as e:
            logger.error(f"[SIM7600] AT HTTP POST error: {e}")
            self.packets_failed += 1
            return False

    def close(self):
        """Clean up resources."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._initialized = False

    def get_stats(self) -> dict:
        return {
            "simulation_mode": self.simulation_mode,
            "packets_sent": self.packets_sent,
            "packets_failed": self.packets_failed,
            "signal_strength_dbm": self.last_signal_strength,
            "network_type": self.get_network_type(),
        }