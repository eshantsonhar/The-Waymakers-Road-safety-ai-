"""
Demo Scenario Simulator
Generates realistic simulated crashes, ambulance movements, and hospital load changes.
Focused on Bangalore geography and Indian road conditions.
"""
import asyncio
import random
import math
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.websocket.manager import ws_manager, WSEventType

logger = logging.getLogger(__name__)

# Bangalore accident hotspots (real locations)
BANGALORE_HOTSPOTS = [
    {"name": "Silk Board Junction", "lat": 12.9177, "lon": 77.6228, "risk": 0.9},
    {"name": "Marathahalli Bridge", "lat": 12.9591, "lon": 77.6974, "risk": 0.85},
    {"name": "KR Puram Bridge", "lat": 13.0050, "lon": 77.6960, "risk": 0.80},
    {"name": "Hebbal Flyover", "lat": 13.0358, "lon": 77.5970, "risk": 0.78},
    {"name": "Tin Factory Junction", "lat": 12.9985, "lon": 77.6608, "risk": 0.75},
    {"name": "Bannerghatta Road", "lat": 12.8900, "lon": 77.5970, "risk": 0.72},
    {"name": "Outer Ring Road Bellandur", "lat": 12.9304, "lon": 77.6784, "risk": 0.70},
    {"name": "Hosur Road Electronic City", "lat": 12.8399, "lon": 77.6770, "risk": 0.68},
    {"name": "Tumkur Road Yeshwanthpur", "lat": 13.0280, "lon": 77.5540, "risk": 0.65},
    {"name": "Old Madras Road", "lat": 12.9900, "lon": 77.6500, "risk": 0.63},
    {"name": "Mysore Road Kengeri", "lat": 12.9100, "lon": 77.4900, "risk": 0.60},
    {"name": "Bellary Road Hebbal", "lat": 13.0450, "lon": 77.5900, "risk": 0.58},
    {"name": "Sarjapur Road", "lat": 12.9100, "lon": 77.6900, "risk": 0.55},
    {"name": "Whitefield Main Road", "lat": 12.9698, "lon": 77.7499, "risk": 0.52},
    {"name": "Koramangala 80ft Road", "lat": 12.9352, "lon": 77.6245, "risk": 0.50},
]

CRASH_SCENARIOS = [
    {
        "type": "MINOR_COLLISION",
        "severity": "LOW",
        "probability": 0.78,
        "impact_g": 2.5,
        "speed_delta": 20,
        "sound_db": 72,
        "description": "Minor rear-end collision at traffic signal",
    },
    {
        "type": "MODERATE_CRASH",
        "severity": "MEDIUM",
        "probability": 0.85,
        "impact_g": 4.2,
        "speed_delta": 35,
        "sound_db": 82,
        "description": "Side-impact collision at intersection",
    },
    {
        "type": "SEVERE_CRASH",
        "severity": "HIGH",
        "probability": 0.93,
        "impact_g": 6.8,
        "speed_delta": 55,
        "sound_db": 91,
        "description": "High-speed frontal collision on highway",
    },
    {
        "type": "ROLLOVER",
        "severity": "CRITICAL",
        "probability": 0.97,
        "impact_g": 9.2,
        "speed_delta": 70,
        "sound_db": 95,
        "description": "Vehicle rollover on elevated road",
    },
]

VEHICLE_TYPES = [
    "Two-Wheeler", "Auto-Rickshaw", "Car", "SUV", "Bus", "Truck", "Mini-Van"
]

WEATHER_CONDITIONS = ["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Fog", "Drizzle"]


class DemoSimulator:
    """Generates realistic demo scenarios for RoadSoS."""

    def __init__(self):
        self._running = False
        self._ambulance_positions: dict = {}
        self._incident_counter = 0

    async def start(self):
        """Start all demo simulation loops."""
        if self._running:
            return
        self._running = True
        logger.info("Demo simulator started")

        # Start concurrent simulation tasks
        asyncio.create_task(self._crash_generation_loop())
        asyncio.create_task(self._ambulance_movement_loop())
        asyncio.create_task(self._hospital_load_loop())
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        """Stop the simulator."""
        self._running = False
        logger.info("Demo simulator stopped")

    async def _crash_generation_loop(self):
        """Periodically generate simulated crash events."""
        await asyncio.sleep(10)  # Initial delay
        while self._running:
            try:
                await self._generate_crash_event()
            except Exception as e:
                logger.error(f"Crash generation error: {e}")
            await asyncio.sleep(settings.DEMO_CRASH_INTERVAL_SECONDS)

    async def _ambulance_movement_loop(self):
        """Continuously update ambulance positions."""
        while self._running:
            try:
                await self._update_ambulance_positions()
            except Exception as e:
                logger.error(f"Ambulance movement error: {e}")
            await asyncio.sleep(settings.DEMO_AMBULANCE_UPDATE_INTERVAL_SECONDS)

    async def _hospital_load_loop(self):
        """Periodically update hospital load data."""
        await asyncio.sleep(5)
        while self._running:
            try:
                await self._update_hospital_loads()
            except Exception as e:
                logger.error(f"Hospital load update error: {e}")
            await asyncio.sleep(settings.DEMO_HOSPITAL_UPDATE_INTERVAL_SECONDS)

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to keep connections alive."""
        while self._running:
            await ws_manager.broadcast_event(
                WSEventType.HEARTBEAT,
                {
                    "server_time": datetime.utcnow().isoformat(),
                    "connections": ws_manager.connection_count,
                    "demo_mode": True,
                },
            )
            await asyncio.sleep(30)

    async def _generate_crash_event(self):
        """Generate a simulated crash at a random hotspot."""
        hotspot = random.choice(BANGALORE_HOTSPOTS)
        scenario = random.choice(CRASH_SCENARIOS)

        # Add some jitter to the location
        lat = hotspot["lat"] + random.uniform(-0.005, 0.005)
        lon = hotspot["lon"] + random.uniform(-0.005, 0.005)

        self._incident_counter += 1
        incident_id = str(uuid.uuid4())
        incident_number = f"INC-BLR-{datetime.now().strftime('%Y%m%d')}-{self._incident_counter:04d}"

        # Build sensor data
        sensor_data = {
            "accel_x": random.uniform(-scenario["impact_g"] * 9.81, scenario["impact_g"] * 9.81),
            "accel_y": random.uniform(-2.0, 2.0),
            "accel_z": 9.81 + random.uniform(-1.0, 1.0),
            "gyro_x": random.uniform(-50, 50) if scenario["type"] != "ROLLOVER" else random.uniform(180, 360),
            "gyro_y": random.uniform(-50, 50) if scenario["type"] != "ROLLOVER" else random.uniform(180, 360),
            "gyro_z": random.uniform(-30, 30),
            "speed_kmh": random.uniform(20, 80),
            "sound_db": scenario["sound_db"] + random.uniform(-5, 5),
            "latitude": lat,
            "longitude": lon,
        }

        incident_payload = {
            "id": incident_id,
            "incident_number": incident_number,
            "latitude": lat,
            "longitude": lon,
            "address": f"Near {hotspot['name']}, Bangalore",
            "district": self._get_district(hotspot["name"]),
            "severity": scenario["severity"],
            "status": "DETECTED",
            "crash_probability_score": scenario["probability"],
            "confidence_level": "HIGH" if scenario["probability"] > 0.85 else "MEDIUM",
            "event_classification": scenario["type"],
            "sensor_data": sensor_data,
            "vehicle_type": random.choice(VEHICLE_TYPES),
            "weather_condition": random.choice(WEATHER_CONDITIONS),
            "is_demo": True,
            "detected_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "timeline": {
                "detected": datetime.utcnow().isoformat(),
            },
            "description": scenario["description"],
        }

        # Broadcast incident creation
        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_CREATED,
            incident_payload,
            channel="incidents",
        )

        logger.info(f"Demo crash generated: {incident_number} at {hotspot['name']} ({scenario['severity']})")

        # Simulate ambulance assignment after 3 seconds
        await asyncio.sleep(3)
        await self._simulate_ambulance_assignment(incident_id, incident_number, lat, lon, scenario["severity"])

    async def _simulate_ambulance_assignment(
        self,
        incident_id: str,
        incident_number: str,
        lat: float,
        lon: float,
        severity: str,
    ):
        """Simulate ambulance being assigned to incident."""
        ambulance_id = str(uuid.uuid4())
        eta = random.uniform(4, 15)

        # Generate ambulance starting position (nearby)
        amb_lat = lat + random.uniform(-0.02, 0.02)
        amb_lon = lon + random.uniform(-0.02, 0.02)

        # Store for movement simulation
        self._ambulance_positions[ambulance_id] = {
            "lat": amb_lat,
            "lon": amb_lon,
            "target_lat": lat,
            "target_lon": lon,
            "incident_id": incident_id,
            "status": "EN_ROUTE_TO_SCENE",
            "progress": 0.0,
        }

        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_ASSIGNED,
            {
                "incident_id": incident_id,
                "incident_number": incident_number,
                "ambulance_id": ambulance_id,
                "vehicle_number": f"KA-01-{random.randint(1000, 9999)}",
                "ambulance_type": random.choice(["ALS", "BLS", "MICU"]),
                "latitude": amb_lat,
                "longitude": amb_lon,
                "eta_to_scene_minutes": round(eta, 1),
                "status": "EN_ROUTE_TO_SCENE",
            },
            channel="ambulances",
        )

        # Simulate hospital assignment
        await asyncio.sleep(1)
        hospital_name = random.choice([
            "Manipal Hospital Whitefield",
            "Apollo Hospital Bannerghatta",
            "Fortis Hospital Cunningham Road",
            "Victoria Hospital",
            "St. John's Medical College Hospital",
        ])

        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_UPDATED,
            {
                "id": incident_id,
                "incident_number": incident_number,
                "status": "DISPATCHED",
                "assigned_ambulance_id": ambulance_id,
                "assigned_hospital_name": hospital_name,
                "hospital_eta_minutes": round(eta + random.uniform(5, 15), 1),
                "timeline": {
                    "ambulance_assigned": datetime.utcnow().isoformat(),
                    "hospital_assigned": datetime.utcnow().isoformat(),
                },
            },
            channel="incidents",
        )

    async def _update_ambulance_positions(self):
        """Move ambulances toward their targets."""
        updates = []

        for amb_id, amb_data in list(self._ambulance_positions.items()):
            # Move toward target
            progress = amb_data["progress"] + random.uniform(0.05, 0.15)

            if progress >= 1.0:
                # Arrived at scene
                del self._ambulance_positions[amb_id]
                await ws_manager.broadcast_event(
                    WSEventType.AMBULANCE_STATUS_CHANGE,
                    {
                        "ambulance_id": amb_id,
                        "status": "ON_SCENE",
                        "latitude": amb_data["target_lat"],
                        "longitude": amb_data["target_lon"],
                        "incident_id": amb_data["incident_id"],
                    },
                    channel="ambulances",
                )
                continue

            # Interpolate position
            new_lat = amb_data["lat"] + (amb_data["target_lat"] - amb_data["lat"]) * progress
            new_lon = amb_data["lon"] + (amb_data["target_lon"] - amb_data["lon"]) * progress

            # Add slight jitter for realism
            new_lat += random.uniform(-0.0001, 0.0001)
            new_lon += random.uniform(-0.0001, 0.0001)

            amb_data["progress"] = progress
            amb_data["lat"] = new_lat
            amb_data["lon"] = new_lon

            updates.append({
                "ambulance_id": amb_id,
                "latitude": round(new_lat, 6),
                "longitude": round(new_lon, 6),
                "heading": self._compute_heading(
                    new_lat, new_lon, amb_data["target_lat"], amb_data["target_lon"]
                ),
                "speed_kmh": random.uniform(40, 80),
                "status": amb_data["status"],
                "route_progress": round(progress, 3),
                "incident_id": amb_data["incident_id"],
            })

        if updates:
            await ws_manager.broadcast_event(
                WSEventType.AMBULANCE_POSITION_UPDATE,
                {"ambulances": updates},
                channel="ambulances",
            )

    async def _update_hospital_loads(self):
        """Simulate hospital load fluctuations."""
        # Generate random hospital load updates
        hospitals_update = []
        for i in range(random.randint(2, 5)):
            hospitals_update.append({
                "hospital_index": i,
                "available_icu_beds": random.randint(2, 15),
                "current_patient_load": random.randint(20, 80),
                "is_on_alert": random.random() < 0.2,
            })

        await ws_manager.broadcast_event(
            WSEventType.HOSPITAL_STATUS_UPDATE,
            {"updates": hospitals_update},
            channel="hospitals",
        )

    def _compute_heading(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Compute compass heading from point 1 to point 2."""
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        angle = math.degrees(math.atan2(dlon, dlat))
        return (angle + 360) % 360

    def _get_district(self, hotspot_name: str) -> str:
        """Map hotspot to Bangalore district."""
        district_map = {
            "Silk Board": "Bommanahalli",
            "Marathahalli": "Mahadevapura",
            "KR Puram": "Mahadevapura",
            "Hebbal": "Yelahanka",
            "Tin Factory": "Mahadevapura",
            "Bannerghatta": "Bommanahalli",
            "Bellandur": "Mahadevapura",
            "Electronic City": "Bommanahalli",
            "Yeshwanthpur": "Dasarahalli",
            "Old Madras": "Mahadevapura",
            "Kengeri": "Rajarajeshwari Nagar",
            "Whitefield": "Mahadevapura",
            "Koramangala": "Bommanahalli",
            "Sarjapur": "Mahadevapura",
        }
        for key, district in district_map.items():
            if key.lower() in hotspot_name.lower():
                return district
        return "Bangalore Urban"

    def generate_sensor_stream(self, scenario_type: str = "CRASH") -> list:
        """Generate a sequence of sensor readings for a given scenario."""
        readings = []
        scenarios = {s["type"]: s for s in CRASH_SCENARIOS}
        scenario = scenarios.get(scenario_type, CRASH_SCENARIOS[0])

        # Pre-crash normal readings
        for i in range(5):
            readings.append({
                "timestamp": i * 0.1,
                "accel_x": random.uniform(-0.5, 0.5),
                "accel_y": random.uniform(-0.3, 0.3),
                "accel_z": 9.81 + random.uniform(-0.2, 0.2),
                "gyro_x": random.uniform(-5, 5),
                "gyro_y": random.uniform(-5, 5),
                "gyro_z": random.uniform(-3, 3),
                "speed_kmh": random.uniform(40, 60),
                "sound_db": random.uniform(35, 55),
                "event": "NORMAL",
            })

        # Impact readings
        for i in range(3):
            readings.append({
                "timestamp": (5 + i) * 0.1,
                "accel_x": scenario["impact_g"] * 9.81 * random.uniform(0.8, 1.2),
                "accel_y": random.uniform(-3.0, 3.0),
                "accel_z": 9.81 + random.uniform(-5.0, 5.0),
                "gyro_x": random.uniform(-200, 200) if scenario_type == "ROLLOVER" else random.uniform(-50, 50),
                "gyro_y": random.uniform(-200, 200) if scenario_type == "ROLLOVER" else random.uniform(-50, 50),
                "gyro_z": random.uniform(-100, 100),
                "speed_kmh": max(0, 60 - scenario["speed_delta"] * random.uniform(0.5, 1.0)),
                "sound_db": scenario["sound_db"] + random.uniform(-3, 3),
                "event": "IMPACT",
            })

        return readings


# Singleton instance
demo_simulator = DemoSimulator()
