"""
MPU-9250 IMU Driver (Python Abstraction)
==========================================
For simulation and testing on laptop.
Reads from the MPU-9250 over I2C or generates simulated data.

Used in:
- hardware_module_code/simulation_mode/ (laptop demo)
- hardware_module_code/main.cpp (embedded C++ version)
"""

import struct
import time
import math
import random
from typing import Optional, Tuple


class MPU9250Reading:
    """Represents a single IMU sensor reading."""

    def __init__(
        self,
        accel_x: float, accel_y: float, accel_z: float,
        gyro_x: float, gyro_y: float, gyro_z: float,
        mag_x: float = 0.0, mag_y: float = 0.0, mag_z: float = 0.0,
        temperature_c: float = 25.0,
        timestamp: Optional[float] = None,
    ):
        self.accel_x = accel_x  # g
        self.accel_y = accel_y
        self.accel_z = accel_z
        self.gyro_x = gyro_x    # degrees per second
        self.gyro_y = gyro_y
        self.gyro_z = gyro_z
        self.mag_x = mag_x      # microTesla
        self.mag_y = mag_y
        self.mag_z = mag_z
        self.temperature_c = temperature_c
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "x": round(self.accel_x, 4),
            "y": round(self.accel_y, 4),
            "z": round(self.accel_z, 4),
            "gx": round(self.gyro_x, 4),
            "gy": round(self.gyro_y, 4),
            "gz": round(self.gyro_z, 4),
            "mx": round(self.mag_x, 2),
            "my": round(self.mag_y, 2),
            "mz": round(self.mag_z, 2),
            "temperature_c": round(self.temperature_c, 1),
            "timestamp": self.timestamp,
        }

    def total_acceleration_g(self) -> float:
        """Compute total acceleration magnitude (excluding gravity)."""
        ax = self.accel_x
        ay = self.accel_y
        az = self.accel_z - 1.0  # Subtract gravity (assume upright)
        return math.sqrt(ax * ax + ay * ay + az * az)

    def gravity_angle_degrees(self) -> float:
        """Compute angle from vertical in degrees."""
        norm = math.sqrt(
            self.accel_x ** 2 + self.accel_y ** 2 + self.accel_z ** 2
        )
        if norm < 0.001:
            return 0.0
        cos_angle = abs(self.accel_z) / norm
        return math.degrees(math.acos(min(1.0, cos_angle)))


class MPU9250Driver:
    """
    MPU-9250 driver with optional real hardware or simulation mode.
    """

    # MPU-9250 register addresses
    WHO_AM_I = 0x75
    ACCEL_XOUT_H = 0x3B
    GYRO_XOUT_H = 0x43
    PWR_MGMT_1 = 0x6B

    # Scale factors
    ACCEL_SCALE = 16384.0  # ±2g → LSB/g
    GYRO_SCALE = 131.0     # ±250dps → LSB/dps

    def __init__(self, simulation_mode: bool = True, i2c_bus: int = 1):
        self.simulation_mode = simulation_mode
        self.i2c_bus = i2c_bus
        self._i2c_device = None
        self._initialized = False
        self._noise_level = 0.02  # Gaussian noise std dev

        # Simulation state
        self._sim_time = 0.0
        self._sim_accel = [0.0, 0.0, 1.0]  # Base: gravity only
        self._sim_gyro = [0.0, 0.0, 0.0]
        self._sim_drift = [
            random.gauss(0, 0.005),
            random.gauss(0, 0.003),
            random.gauss(0, 0.004),
        ]

    def initialize(self) -> bool:
        """Initialize the MPU-9250 sensor."""
        if self.simulation_mode:
            self._initialized = True
            print("[MPU9250] Simulation mode initialized")
            return True

        try:
            import smbus
            self._i2c_device = smbus.SMBus(self.i2c_bus)

            # Check WHO_AM_I
            whoami = self._i2c_device.read_byte_data(
                self.MPU9250_ADDR, self.WHO_AM_I
            )
            if whoami not in (0x71, 0x73):
                print(f"[MPU9250] WHO_AM_I mismatch: 0x{whoami:02X}")
                return False

            # Wake up
            self._i2c_device.write_byte_data(
                self.MPU9250_ADDR, self.PWR_MGMT_1, 0x00
            )
            time.sleep(0.01)

            self._initialized = True
            print("[MPU9250] Hardware initialized successfully")
            return True

        except ImportError:
            print("[MPU9250] smbus not available, falling back to simulation")
            self.simulation_mode = True
            self._initialized = True
            return True
        except Exception as e:
            print(f"[MPU9250] Hardware init failed: {e}, using simulation")
            self.simulation_mode = True
            self._initialized = True
            return True

    def read(self) -> Optional[MPU9250Reading]:
        """Read one sample from the IMU."""
        if not self._initialized:
            return None

        if self.simulation_mode:
            return self._simulate_reading()
        return self._hardware_read()

    def read_multiple(self, count: int = 10) -> list:
        """Read multiple samples."""
        return [self.read() for _ in range(count) if self.read() is not None]

    def _simulate_reading(self) -> MPU9250Reading:
        """Generate realistic simulated IMU data."""
        self._sim_time += 0.02  # 50 Hz

        # Add drift
        for i in range(3):
            self._sim_drift[i] += random.gauss(0, 0.0001)
            self._sim_drift[i] = max(-0.05, min(0.05, self._sim_drift[i]))

        # Simulate vehicle motion
        speed_factor = math.sin(self._sim_time * 0.1) * 0.5 + 0.5

        # Accelerometer: gravity + motion
        accel = [
            math.sin(self._sim_time * 0.3) * 0.2 * speed_factor
            + random.gauss(0, self._noise_level),
            math.cos(self._sim_time * 0.2) * 0.15 * speed_factor
            + random.gauss(0, self._noise_level),
            1.0 + math.sin(self._sim_time * 0.5) * 0.1 * speed_factor
            + random.gauss(0, self._noise_level * 1.5),
        ]

        # Gyroscope: angular velocity with drift
        gyro = [
            math.sin(self._sim_time * 0.15) * 2.0 * speed_factor
            + self._sim_drift[0] + random.gauss(0, 0.01),
            math.cos(self._sim_time * 0.1) * 1.5 * speed_factor
            + self._sim_drift[1] + random.gauss(0, 0.008),
            math.sin(self._sim_time * 0.08) * 3.0 * speed_factor
            + self._sim_drift[2] + random.gauss(0, 0.012),
        ]

        return MPU9250Reading(
            accel_x=accel[0], accel_y=accel[1], accel_z=accel[2],
            gyro_x=gyro[0], gyro_y=gyro[1], gyro_z=gyro[2],
            temperature_c=32.0 + math.sin(self._sim_time * 0.01) * 0.5,
        )

    def _hardware_read(self) -> Optional[MPU9250Reading]:
        """Read from real MPU-9250 hardware via I2C."""
        if not self._i2c_device:
            return None

        try:
            # Read 14 bytes: accel (6) + temp (2) + gyro (6)
            data = self._i2c_device.read_i2c_block_data(
                self.MPU9250_ADDR, self.ACCEL_XOUT_H, 14
            )

            # Parse signed 16-bit values
            ax = struct.unpack_from('>h', data, 0)[0]
            ay = struct.unpack_from('>h', data, 2)[0]
            az = struct.unpack_from('>h', data, 4)[0]
            temp = struct.unpack_from('>h', data, 6)[0]
            gx = struct.unpack_from('>h', data, 8)[0]
            gy = struct.unpack_from('>h', data, 10)[0]
            gz = struct.unpack_from('>h', data, 12)[0]

            # Scale to physical units
            return MPU9250Reading(
                accel_x=ax / self.ACCEL_SCALE,
                accel_y=ay / self.ACCEL_SCALE,
                accel_z=az / self.ACCEL_SCALE,
                gyro_x=gx / self.GYRO_SCALE,
                gyro_y=gy / self.GYRO_SCALE,
                gyro_z=gz / self.GYRO_SCALE,
                temperature_c=temp / 333.87 + 21.0,
            )

        except Exception as e:
            print(f"[MPU9250] Read error: {e}")
            return None

    def close(self):
        """Clean up I2C resources."""
        if self._i2c_device:
            self._i2c_device.close()
        self._initialized = False


# Convenience
MPU9250_ADDR = 0x68