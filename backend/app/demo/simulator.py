"""
Demo Scenario Simulator
Generates realistic simulated crashes, ambulance movements, and hospital load changes.
Focused on Bangalore geography and Indian road conditions.

Every crash event now includes:
- Full OSRM road-following route from ambulance → incident
- Full OSRM road-following route from incident → hospital
- Ambulance moves along the route waypoints (not teleporting)
- Hospital selection explanation
"""
import asyncio
import random
import math
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from app.config import settings
from app.websocket.manager import ws_manager, WSEventType
from app.services.routing import get_route

logger = logging.getLogger(__name__)

# ── Bangalore accident hotspots (real locations) ─────────────────────────────
BANGALORE_HOTSPOTS = [
    {"name": "Silk Board Junction",         "lat": 12.9177, "lon": 77.6228, "risk": 0.90},
    {"name": "Marathahalli Bridge",          "lat": 12.9591, "lon": 77.6974, "risk": 0.85},
    {"name": "KR Puram Bridge",              "lat": 13.0050, "lon": 77.6960, "risk": 0.80},
    {"name": "Hebbal Flyover",               "lat": 13.0358, "lon": 77.5970, "risk": 0.78},
    {"name": "Tin Factory Junction",         "lat": 12.9985, "lon": 77.6608, "risk": 0.75},
    {"name": "Bannerghatta Road",            "lat": 12.8900, "lon": 77.5970, "risk": 0.72},
    {"name": "Outer Ring Road Bellandur",    "lat": 12.9304, "lon": 77.6784, "risk": 0.70},
    {"name": "Hosur Road Electronic City",   "lat": 12.8399, "lon": 77.6770, "risk": 0.68},
    {"name": "Tumkur Road Yeshwanthpur",     "lat": 13.0280, "lon": 77.5540, "risk": 0.65},
    {"name": "Old Madras Road",              "lat": 12.9900, "lon": 77.6500, "risk": 0.63},
    {"name": "Mysore Road Kengeri",          "lat": 12.9100, "lon": 77.4900, "risk": 0.60},
    {"name": "Bellary Road Hebbal",          "lat": 13.0450, "lon": 77.5900, "risk": 0.58},
    {"name": "Sarjapur Road",                "lat": 12.9100, "lon": 77.6900, "risk": 0.55},
    {"name": "Whitefield Main Road",         "lat": 12.9698, "lon": 77.7499, "risk": 0.52},
    {"name": "Koramangala 80ft Road",        "lat": 12.9352, "lon": 77.6245, "risk": 0.50},
]

# ── Ambulance base stations ───────────────────────────────────────────────────
AMBULANCE_BASES = [
    {"name": "Silk Board Station",      "lat": 12.9177, "lon": 77.6228},
    {"name": "Marathahalli Station",    "lat": 12.9591, "lon": 77.6974},
    {"name": "Hebbal Station",          "lat": 13.0358, "lon": 77.5970},
    {"name": "Koramangala Station",     "lat": 12.9352, "lon": 77.6245},
    {"name": "Yeshwanthpur Station",    "lat": 13.0280, "lon": 77.5540},
    {"name": "Electronic City Station", "lat": 12.8399, "lon": 77.6770},
    {"name": "Whitefield Station",      "lat": 12.9698, "lon": 77.7499},
    {"name": "Kengeri Station",         "lat": 12.9100, "lon": 77.4900},
]

# ── Hospitals (real Bangalore hospitals) ─────────────────────────────────────
HOSPITALS = [
    {"id": "h1", "name": "Manipal Hospital Whitefield",        "short": "Manipal WF",   "lat": 12.9698, "lon": 77.7499, "trauma_level": 1, "icu": 40, "icu_avail": 18},
    {"id": "h2", "name": "Apollo Hospital Bannerghatta",        "short": "Apollo BG",    "lat": 12.8900, "lon": 77.5970, "trauma_level": 1, "icu": 50, "icu_avail": 22},
    {"id": "h3", "name": "Fortis Hospital Cunningham Road",     "short": "Fortis CR",    "lat": 12.9900, "lon": 77.5900, "trauma_level": 1, "icu": 35, "icu_avail": 15},
    {"id": "h4", "name": "Victoria Hospital",                   "short": "Victoria",     "lat": 12.9716, "lon": 77.5946, "trauma_level": 2, "icu": 60, "icu_avail": 25},
    {"id": "h5", "name": "St. John's Medical College Hospital", "short": "St. Johns",    "lat": 12.9352, "lon": 77.6245, "trauma_level": 1, "icu": 45, "icu_avail": 20},
    {"id": "h6", "name": "Narayana Health City",                "short": "Narayana HC",  "lat": 12.8399, "lon": 77.6770, "trauma_level": 1, "icu": 80, "icu_avail": 35},
    {"id": "h7", "name": "Sakra World Hospital",                "short": "Sakra",        "lat": 12.9591, "lon": 77.6974, "trauma_level": 2, "icu": 30, "icu_avail": 12},
    {"id": "h8", "name": "Aster CMI Hospital",                  "short": "Aster CMI",    "lat": 13.0358, "lon": 77.5970, "trauma_level": 2, "icu": 35, "icu_avail": 14},
]

CRASH_SCENARIOS = [
    {"type": "MINOR_COLLISION",  "severity": "LOW",      "probability": 0.78, "impact_g": 2.5, "speed_delta": 20, "sound_db": 72, "description": "Minor rear-end collision at traffic signal"},
    {"type": "MODERATE_CRASH",   "severity": "MEDIUM",   "probability": 0.85, "impact_g": 4.2, "speed_delta": 35, "sound_db": 82, "description": "Side-impact collision at intersection"},
    {"type": "SEVERE_CRASH",     "severity": "HIGH",     "probability": 0.93, "impact_g": 6.8, "speed_delta": 55, "sound_db": 91, "description": "High-speed frontal collision on highway"},
    {"type": "ROLLOVER",         "severity": "CRITICAL", "probability": 0.97, "impact_g": 9.2, "speed_delta": 70, "sound_db": 95, "description": "Vehicle rollover on elevated road"},
]

VEHICLE_TYPES = ["Two-Wheeler", "Auto-Rickshaw", "Car", "SUV", "Bus", "Truck", "Mini-Van"]
WEATHER_CONDITIONS = ["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Fog", "Drizzle"]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_hospital(inc_lat: float, inc_lon: float, severity: str) -> dict:
    """Select best hospital: nearest trauma center for HIGH/CRITICAL, nearest otherwise."""
    candidates = HOSPITALS
    if severity in ("HIGH", "CRITICAL"):
        trauma = [h for h in HOSPITALS if h["trauma_level"] <= 1]
        if trauma:
            candidates = trauma

    def score(h: dict) -> float:
        dist = _haversine_km(inc_lat, inc_lon, h["lat"], h["lon"])
        # Prefer closer + more ICU available
        return dist - (h["icu_avail"] / 10.0)

    return min(candidates, key=score)


def _hospital_selection_reason(hospital: dict, dist_km: float, eta_min: float, severity: str) -> str:
    """Generate human-readable hospital selection explanation."""
    reasons = []
    if hospital["trauma_level"] == 1:
        reasons.append("Level 1 Trauma Centre")
    if hospital["icu_avail"] >= 15:
        reasons.append(f"{hospital['icu_avail']} ICU beds available")
    elif hospital["icu_avail"] >= 8:
        reasons.append(f"{hospital['icu_avail']} ICU beds available")
    reasons.append(f"{dist_km:.1f} km away")
    reasons.append(f"ETA {eta_min:.0f} min")
    if severity == "CRITICAL":
        reasons.append("Neurosurgery on standby")
    return " · ".join(reasons)


def _get_district(hotspot_name: str) -> str:
    district_map = {
        "Silk Board": "Bommanahalli", "Marathahalli": "Mahadevapura",
        "KR Puram": "Mahadevapura", "Hebbal": "Yelahanka",
        "Tin Factory": "Mahadevapura", "Bannerghatta": "Bommanahalli",
        "Bellandur": "Mahadevapura", "Electronic City": "Bommanahalli",
        "Yeshwanthpur": "Dasarahalli", "Old Madras": "Mahadevapura",
        "Kengeri": "Rajarajeshwari Nagar", "Whitefield": "Mahadevapura",
        "Koramangala": "Bommanahalli", "Sarjapur": "Mahadevapura",
    }
    for key, district in district_map.items():
        if key.lower() in hotspot_name.lower():
            return district
    return "Bangalore Urban"


class DemoSimulator:
    """Generates realistic demo scenarios for RoadSoS."""

    def __init__(self):
        self._running = False
        self._incident_counter = 0
        # ambulance_id → movement state
        self._active_ambulances: dict[str, dict] = {}

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info("Demo simulator started")
        asyncio.create_task(self._crash_generation_loop())
        asyncio.create_task(self._ambulance_movement_loop())
        asyncio.create_task(self._hospital_load_loop())
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        self._running = False
        logger.info("Demo simulator stopped")

    # ── Loops ─────────────────────────────────────────────────────────────────

    async def _crash_generation_loop(self):
        await asyncio.sleep(8)
        while self._running:
            try:
                await self._generate_crash_event()
            except Exception as e:
                logger.error(f"Crash generation error: {e}", exc_info=True)
            await asyncio.sleep(settings.DEMO_CRASH_INTERVAL_SECONDS)

    async def _ambulance_movement_loop(self):
        while self._running:
            try:
                await self._tick_ambulance_movement()
            except Exception as e:
                logger.error(f"Ambulance movement error: {e}")
            await asyncio.sleep(settings.DEMO_AMBULANCE_UPDATE_INTERVAL_SECONDS)

    async def _hospital_load_loop(self):
        await asyncio.sleep(5)
        while self._running:
            try:
                await self._update_hospital_loads()
            except Exception as e:
                logger.error(f"Hospital load update error: {e}")
            await asyncio.sleep(settings.DEMO_HOSPITAL_UPDATE_INTERVAL_SECONDS)

    async def _heartbeat_loop(self):
        while self._running:
            await ws_manager.broadcast_event(
                WSEventType.HEARTBEAT,
                {"server_time": datetime.utcnow().isoformat(), "connections": ws_manager.connection_count, "demo_mode": True},
            )
            await asyncio.sleep(30)

    # ── Crash generation ──────────────────────────────────────────────────────

    async def _generate_crash_event(self):
        hotspot = random.choice(BANGALORE_HOTSPOTS)
        scenario = random.choice(CRASH_SCENARIOS)

        # Jitter location slightly
        inc_lat = hotspot["lat"] + random.uniform(-0.004, 0.004)
        inc_lon = hotspot["lon"] + random.uniform(-0.004, 0.004)

        self._incident_counter += 1
        incident_id = str(uuid.uuid4())
        incident_number = f"INC-BLR-{datetime.now().strftime('%Y%m%d')}-{self._incident_counter:04d}"

        # Pick nearest ambulance base
        base = min(AMBULANCE_BASES, key=lambda b: _haversine_km(inc_lat, inc_lon, b["lat"], b["lon"]))
        amb_lat = base["lat"] + random.uniform(-0.008, 0.008)
        amb_lon = base["lon"] + random.uniform(-0.008, 0.008)
        ambulance_id = str(uuid.uuid4())
        vehicle_number = f"KA-01-{random.randint(1000, 9999)}"
        ambulance_type = random.choice(["ALS", "BLS", "MICU"])

        # Pick best hospital
        hospital = _nearest_hospital(inc_lat, inc_lon, scenario["severity"])

        # Fetch routes concurrently
        route_to_scene, route_to_hospital = await asyncio.gather(
            get_route(amb_lat, amb_lon, inc_lat, inc_lon),
            get_route(inc_lat, inc_lon, hospital["lat"], hospital["lon"]),
        )

        amb_eta = route_to_scene["duration_minutes"]
        hosp_eta = route_to_hospital["duration_minutes"]
        amb_dist = route_to_scene["distance_km"]
        hosp_dist = route_to_hospital["distance_km"]

        hospital_reason = _hospital_selection_reason(hospital, hosp_dist, hosp_eta, scenario["severity"])

        now = datetime.utcnow().isoformat()

        incident_payload = {
            "id": incident_id,
            "incident_number": incident_number,
            "latitude": inc_lat,
            "longitude": inc_lon,
            "address": f"Near {hotspot['name']}, Bangalore",
            "district": _get_district(hotspot["name"]),
            "severity": scenario["severity"],
            "status": "DETECTED",
            "crash_probability_score": scenario["probability"],
            "confidence_level": "HIGH" if scenario["probability"] > 0.85 else "MEDIUM",
            "event_classification": scenario["type"],
            "vehicle_type": random.choice(VEHICLE_TYPES),
            "weather_condition": random.choice(WEATHER_CONDITIONS),
            "is_demo": True,
            "detected_at": now,
            "created_at": now,
            "description": scenario["description"],
            "timeline": {"detected": now},
            # Ambulance assignment
            "assigned_ambulance_id": ambulance_id,
            "ambulance_eta_minutes": round(amb_eta, 1),
            "ambulance_distance_km": round(amb_dist, 2),
            # Hospital assignment
            "assigned_hospital_id": hospital["id"],
            "assigned_hospital_name": hospital["name"],
            "assigned_hospital_short": hospital["short"],
            "hospital_eta_minutes": round(hosp_eta, 1),
            "hospital_distance_km": round(hosp_dist, 2),
            "hospital_selection_reason": hospital_reason,
            "hospital_trauma_level": hospital["trauma_level"],
            "hospital_icu_available": hospital["icu_avail"],
            # Route geometry (for map rendering)
            "route_to_scene": route_to_scene["coordinates"],
            "route_to_hospital": route_to_hospital["coordinates"],
            "route_source": route_to_scene["source"],
        }

        # Store ambulance movement state
        self._active_ambulances[ambulance_id] = {
            "ambulance_id": ambulance_id,
            "vehicle_number": vehicle_number,
            "ambulance_type": ambulance_type,
            "incident_id": incident_id,
            "incident_number": incident_number,
            # Phase 1: ambulance → scene
            "phase": "to_scene",
            "route_coords": route_to_scene["coordinates"],
            "route_to_hospital": route_to_hospital["coordinates"],
            "waypoint_index": 0,
            "lat": amb_lat,
            "lon": amb_lon,
            "target_lat": inc_lat,
            "target_lon": inc_lon,
            "hospital_lat": hospital["lat"],
            "hospital_lon": hospital["lon"],
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "eta_minutes": round(amb_eta, 1),
            "status": "EN_ROUTE_TO_SCENE",
            "base_station": base["name"],
        }

        # Broadcast incident with full context
        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_CREATED,
            incident_payload,
            channel="incidents",
        )

        # Broadcast ambulance assignment
        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_ASSIGNED,
            {
                "incident_id": incident_id,
                "incident_number": incident_number,
                "ambulance_id": ambulance_id,
                "vehicle_number": vehicle_number,
                "ambulance_type": ambulance_type,
                "latitude": amb_lat,
                "longitude": amb_lon,
                "status": "EN_ROUTE_TO_SCENE",
                "eta_to_scene_minutes": round(amb_eta, 1),
                "distance_to_scene_km": round(amb_dist, 2),
                "base_station": base["name"],
                "route_to_scene": route_to_scene["coordinates"],
                "route_to_hospital": route_to_hospital["coordinates"],
                "hospital_id": hospital["id"],
                "hospital_name": hospital["name"],
                "hospital_selection_reason": hospital_reason,
            },
            channel="ambulances",
        )

        logger.info(
            f"Demo crash: {incident_number} at {hotspot['name']} ({scenario['severity']}) | "
            f"Amb: {vehicle_number} ETA {amb_eta:.0f}min | "
            f"Hospital: {hospital['short']} ETA {hosp_eta:.0f}min | "
            f"Route source: {route_to_scene['source']}"
        )

    # ── Ambulance movement ────────────────────────────────────────────────────

    async def _tick_ambulance_movement(self):
        """Move each active ambulance one step along its route."""
        updates = []
        to_remove = []

        for amb_id, state in list(self._active_ambulances.items()):
            coords = state["route_coords"]
            idx = state["waypoint_index"]

            if not coords or idx >= len(coords) - 1:
                # Arrived at current destination
                if state["phase"] == "to_scene":
                    await self._ambulance_arrived_at_scene(amb_id, state)
                elif state["phase"] == "to_hospital":
                    await self._ambulance_arrived_at_hospital(amb_id, state)
                    to_remove.append(amb_id)
                continue

            # Advance 1-3 waypoints per tick for realistic speed
            step = random.randint(1, 3)
            new_idx = min(idx + step, len(coords) - 1)
            state["waypoint_index"] = new_idx

            new_lat = coords[new_idx][0]
            new_lon = coords[new_idx][1]
            state["lat"] = new_lat
            state["lon"] = new_lon

            # Compute heading
            if new_idx > 0:
                prev = coords[new_idx - 1]
                dlat = new_lat - prev[0]
                dlon = new_lon - prev[1]
                heading = (math.degrees(math.atan2(dlon, dlat)) + 360) % 360
            else:
                heading = 0.0

            # Estimate remaining ETA
            remaining_waypoints = len(coords) - new_idx - 1
            total_waypoints = max(len(coords) - 1, 1)
            progress = new_idx / total_waypoints
            original_eta = state.get("eta_minutes", 10.0)
            remaining_eta = max(0.0, original_eta * (1.0 - progress))

            speed_kmh = random.uniform(45, 75) if state["phase"] == "to_scene" else random.uniform(35, 55)

            updates.append({
                "ambulance_id": amb_id,
                "vehicle_number": state["vehicle_number"],
                "ambulance_type": state["ambulance_type"],
                "latitude": round(new_lat, 6),
                "longitude": round(new_lon, 6),
                "heading": round(heading, 1),
                "speed_kmh": round(speed_kmh, 1),
                "status": state["status"],
                "incident_id": state["incident_id"],
                "route_progress": round(progress, 3),
                "eta_minutes": round(remaining_eta, 1),
                "phase": state["phase"],
            })

        for amb_id in to_remove:
            del self._active_ambulances[amb_id]

        if updates:
            await ws_manager.broadcast_event(
                WSEventType.AMBULANCE_POSITION_UPDATE,
                {"ambulances": updates},
                channel="ambulances",
            )

    async def _ambulance_arrived_at_scene(self, amb_id: str, state: dict):
        """Ambulance reached the incident scene — switch to hospital route."""
        now = datetime.utcnow().isoformat()
        state["phase"] = "to_hospital"
        state["route_coords"] = state["route_to_hospital"]
        state["waypoint_index"] = 0
        state["lat"] = state["target_lat"]
        state["lon"] = state["target_lon"]
        state["status"] = "TRANSPORTING"

        # Compute hospital ETA from route
        hosp_route = state["route_to_hospital"]
        if hosp_route:
            dist_km = _haversine_km(
                state["target_lat"], state["target_lon"],
                state["hospital_lat"], state["hospital_lon"]
            )
            state["eta_minutes"] = round((dist_km / 40.0) * 60, 1)

        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_STATUS_CHANGE,
            {
                "ambulance_id": amb_id,
                "vehicle_number": state["vehicle_number"],
                "status": "ON_SCENE",
                "latitude": state["target_lat"],
                "longitude": state["target_lon"],
                "incident_id": state["incident_id"],
                "timestamp": now,
            },
            channel="ambulances",
        )

        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_UPDATED,
            {
                "id": state["incident_id"],
                "incident_number": state["incident_number"],
                "status": "ON_SCENE",
                "timeline": {"ambulance_arrived": now},
            },
            channel="incidents",
        )

        # Brief pause at scene
        await asyncio.sleep(random.uniform(3, 8))

        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_STATUS_CHANGE,
            {
                "ambulance_id": amb_id,
                "vehicle_number": state["vehicle_number"],
                "status": "TRANSPORTING",
                "latitude": state["target_lat"],
                "longitude": state["target_lon"],
                "incident_id": state["incident_id"],
                "hospital_id": state["hospital_id"],
                "hospital_name": state["hospital_name"],
                "eta_to_hospital_minutes": state["eta_minutes"],
                "timestamp": now,
            },
            channel="ambulances",
        )

        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_UPDATED,
            {
                "id": state["incident_id"],
                "incident_number": state["incident_number"],
                "status": "TRANSPORTING",
                "timeline": {"patient_picked_up": now},
            },
            channel="incidents",
        )

    async def _ambulance_arrived_at_hospital(self, amb_id: str, state: dict):
        """Ambulance reached the hospital — incident resolved."""
        now = datetime.utcnow().isoformat()

        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_STATUS_CHANGE,
            {
                "ambulance_id": amb_id,
                "vehicle_number": state["vehicle_number"],
                "status": "AT_HOSPITAL",
                "latitude": state["hospital_lat"],
                "longitude": state["hospital_lon"],
                "incident_id": state["incident_id"],
                "hospital_id": state["hospital_id"],
                "hospital_name": state["hospital_name"],
                "timestamp": now,
            },
            channel="ambulances",
        )

        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_UPDATED,
            {
                "id": state["incident_id"],
                "incident_number": state["incident_number"],
                "status": "RESOLVED",
                "resolved_at": now,
                "timeline": {"hospital_reached": now},
            },
            channel="incidents",
        )

        logger.info(
            f"Incident {state['incident_number']} resolved — "
            f"ambulance {state['vehicle_number']} delivered to {state['hospital_name']}"
        )

    async def _update_hospital_loads(self):
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

    # ── Sensor stream generator (for detection API) ───────────────────────────

    def generate_sensor_stream(self, scenario_type: str = "CRASH") -> list:
        scenarios = {s["type"]: s for s in CRASH_SCENARIOS}
        scenario = scenarios.get(scenario_type, CRASH_SCENARIOS[0])
        readings = []

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
