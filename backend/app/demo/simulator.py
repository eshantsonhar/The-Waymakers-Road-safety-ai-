"""
Unified Emergency Simulation & Real-time State Synchronization
===============================================================

Synchronizes the in-memory backend stores (_hospitals_store, _ambulances_store, _incidents_store)
with the DemoSimulator loop. Implements intelligent hospital ranking for simulation dispatches,
realistic ambulance routing and movement without teleportation, and persistent active route
reconstructions on client reconnects or refreshes.

Key Design Decisions:
- SIMULATION_TICK = 1 second (deterministic)
- Route progression engine: precomputed cumulative distances, continuous interpolation
- Incident state machine: validated status transitions
- Nearest available ambulance from _ambulances_store (no random IDs)
- Hospital loads updated directly in _hospitals_store
- Incremental state snapshots with entity versioning
"""
import asyncio
import random
import math
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from app.config import settings
from app.websocket.manager import ws_manager, WSEventType
from app.services.routing import (
    get_route, precompute_route_progression, advance_along_route,
    SPEED_TO_SCENE_KMH, SPEED_TO_HOSPITAL_KMH, SIMULATION_TICK_SECONDS,
)
from app.incident_status import IncidentStatus
from app.api.hospitals import _hospitals_store
from app.api.ambulances import _ambulances_store
from app.api.incidents import _incidents_store
from app.api.routes import (
    create_route, update_route_progress, get_route_by_ambulance,
    deactivate_route_by_ambulance, get_all_active_routes,
)
from app.engines.hospital_intelligence import hospital_engine

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


def _find_nearest_available_ambulance(inc_lat: float, inc_lon: float) -> Optional[Tuple[str, dict]]:
    """Find the nearest available, active ambulance from _ambulances_store. Falls back to busy unit."""
    available = [
        (amb_id, amb) for amb_id, amb in _ambulances_store.items()
        if amb["status"] == "AVAILABLE" and amb["is_active"]
    ]
    if not available:
        logger.warning("No available ambulances — falling back to busy unit")
        busy = [(amb_id, amb) for amb_id, amb in _ambulances_store.items() if amb["is_active"]]
        if not busy:
            logger.error("No ambulances in store at all!")
            return None
        return min(busy, key=lambda x: _haversine_km(inc_lat, inc_lon, x[1]["latitude"], x[1]["longitude"]))
    return min(available, key=lambda x: _haversine_km(inc_lat, inc_lon, x[1]["latitude"], x[1]["longitude"]))


def _rank_hospitals_for_sim(inc_lat: float, inc_lon: float, severity: str):
    """Use hospital_engine to rank. Returns HospitalRanking dataclass ."""
    if not _hospitals_store:
        logger.error("No hospitals in store!")
        return None
    rankings = hospital_engine.rank_hospitals(
        hospitals=_hospitals_store, incident_lat=inc_lat, incident_lon=inc_lon,
        severity=severity, traffic_factor=1.0,
    )
    if not rankings:
        logger.warning("No hospital rankings returned — falling back to nearest")
        nearest = min(_hospitals_store, key=lambda h: _haversine_km(inc_lat, inc_lon, h.latitude, h.longitude))
        return nearest  # Returns MockHospital
    return rankings[0]  # Returns HospitalRanking dataclass


def _resolve_hospital(ranking):
    """If ranking is a HospitalRanking dataclass, look up MockHospital from store by hospital_id."""
    if hasattr(ranking, 'hospital_id'):
        for h in _hospitals_store:
            if h.id == ranking.hospital_id:
                return h
        return None
    # Already a MockHospital
    return ranking


class DemoSimulator:
    """
    Unified emergency simulation system with deterministic 1-second ticks,
    continuous route interpolation, incident state machine, and shared backend stores.
    """

    def __init__(self):
        self._running = False
        self._incident_counter = 0
        self._sim_tick = 0
        self._movement_state: Dict[str, dict] = {}
        self._incident_versions: Dict[str, int] = {}
        self._sent_geometry: Dict[str, bool] = {}

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info("Demo simulator started — deterministic 1s tick")
        asyncio.create_task(self._main_simulation_loop())

    async def stop(self):
        self._running = False
        logger.info("Demo simulator stopped")

    async def _main_simulation_loop(self):
        await asyncio.sleep(3)
        crash_tick = 0
        crash_interval_ticks = max(1, int(settings.DEMO_CRASH_INTERVAL_SECONDS / SIMULATION_TICK_SECONDS))
        while self._running:
            self._sim_tick += 1
            crash_tick += 1
            try:
                if crash_tick >= crash_interval_ticks:
                    crash_tick = 0
                    await self._generate_crash_event()
                await self._tick_all_ambulances()
                if self._sim_tick % max(1, int(settings.DEMO_HOSPITAL_UPDATE_INTERVAL_SECONDS / SIMULATION_TICK_SECONDS)) == 0:
                    await self._update_hospital_loads()
                if self._sim_tick % 30 == 0:
                    await ws_manager.broadcast_event(
                        WSEventType.HEARTBEAT, {
                            "server_time": datetime.utcnow().isoformat(),
                            "connections": ws_manager.connection_count,
                            "demo_mode": True, "sim_tick": self._sim_tick,
                        },
                    )
            except Exception as e:
                logger.error(f"Simulation tick error: {e}", exc_info=True)
            await asyncio.sleep(SIMULATION_TICK_SECONDS)

    async def _generate_crash_event(self):
        hotspot = random.choice(BANGALORE_HOTSPOTS)
        scenario = random.choice(CRASH_SCENARIOS)

        inc_lat = hotspot["lat"] + random.uniform(-0.004, 0.004)
        inc_lon = hotspot["lon"] + random.uniform(-0.004, 0.004)

        self._incident_counter += 1
        incident_id = str(uuid.uuid4())
        incident_number = f"INC-BLR-{datetime.now().strftime('%Y%m%d')}-{self._incident_counter:04d}"

        amb_result = _find_nearest_available_ambulance(inc_lat, inc_lon)
        if amb_result is None:
            logger.warning("Cannot dispatch — no ambulances available")
            return
        amb_id, amb_data = amb_result
        vehicle_number = amb_data["vehicle_number"]
        ambulance_type = amb_data["ambulance_type"]

        best_ranking = _rank_hospitals_for_sim(inc_lat, inc_lon, scenario["severity"])
        if best_ranking is None:
            logger.warning("Cannot dispatch — no hospitals available")
            return

        # Resolve the MockHospital from the ranking or use directly
        hospital = _resolve_hospital(best_ranking)
        if hospital is None:
            logger.warning("Cannot find hospital in store!")
            return

        hospital_id = hospital.id
        hospital_name = hospital.name
        hospital_lat = hospital.latitude
        hospital_lon = hospital.longitude

        amb_lat = amb_data["latitude"]
        amb_lon = amb_data["longitude"]

        route_to_scene, route_to_hospital = await asyncio.gather(
            get_route(amb_lat, amb_lon, inc_lat, inc_lon),
            get_route(inc_lat, inc_lon, hospital_lat, hospital_lon),
        )

        amb_eta = route_to_scene["duration_minutes"]
        amb_dist = route_to_scene["distance_km"]
        hosp_eta = route_to_hospital["duration_minutes"]
        hosp_dist = route_to_hospital["distance_km"]
        now = datetime.utcnow().isoformat()

        timeline = {"detected": now, "ambulance_dispatched": now}
        incident = {
            "id": incident_id, "incident_number": incident_number,
            "latitude": inc_lat, "longitude": inc_lon,
            "address": f"Near {hotspot['name']}, Bangalore",
            "district": _get_district(hotspot["name"]),
            "severity": scenario["severity"],
            "status": IncidentStatus.DISPATCHING.value,
            "crash_probability_score": scenario["probability"],
            "confidence_level": "HIGH" if scenario["probability"] > 0.85 else "MEDIUM",
            "event_classification": scenario["type"],
            "vehicle_type": random.choice(VEHICLE_TYPES),
            "weather_condition": random.choice(WEATHER_CONDITIONS),
            "is_demo": True, "detected_at": now, "created_at": now,
            "description": scenario["description"], "timeline": timeline,
            "assigned_ambulance_id": amb_id,
            "ambulance_eta_minutes": round(amb_eta, 1),
            "ambulance_distance_km": round(amb_dist, 2),
            "assigned_hospital_id": hospital_id,
            "assigned_hospital_name": hospital_name,
            "assigned_hospital_short": hospital.short_name,
            "hospital_eta_minutes": round(hosp_eta, 1),
            "hospital_distance_km": round(hosp_dist, 2),
            "hospital_selection_reason": hospital_engine._generate_explanation(
                hospital, hosp_dist, hosp_eta,
                {"trauma_capability": 0.8, "icu_availability": 0.7,
                 "hospital_load": 0.6, "blood_availability": 0.5,
                 "specialist_availability": 0.6}, 85.0,
            ),
            "hospital_trauma_level": hospital.trauma_level,
            "hospital_icu_available": hospital.available_icu_beds,
            "route_to_scene": route_to_scene["coordinates"],
            "route_to_hospital": route_to_hospital["coordinates"],
            "route_source": route_to_scene["source"],
            "version": 1,
        }
        _incidents_store[incident_id] = incident
        self._incident_versions[incident_id] = 1

        amb_data["status"] = "EN_ROUTE_TO_SCENE"
        amb_data["current_incident_id"] = incident_id
        amb_data["assigned_hospital_id"] = hospital_id
        amb_data["eta_to_scene_minutes"] = round(amb_eta, 1)
        amb_data["heading"] = 0.0
        amb_data["speed_kmh"] = 0.0
        amb_data["last_location_update"] = now
        _ambulances_store[amb_id] = amb_data

        scene_progression = precompute_route_progression(route_to_scene["coordinates"])
        hospital_progression = precompute_route_progression(route_to_hospital["coordinates"])

        self._movement_state[amb_id] = {
            "ambulance_id": amb_id, "vehicle_number": vehicle_number,
            "ambulance_type": ambulance_type, "incident_id": incident_id,
            "incident_number": incident_number, "phase": "to_scene",
            "scene_progression": scene_progression,
            "hospital_progression": hospital_progression,
            "current_distance_m": 0.0, "speed_kmh": SPEED_TO_SCENE_KMH,
            "origin_lat": amb_lat, "origin_lon": amb_lon,
            "target_lat": inc_lat, "target_lon": inc_lon,
            "hospital_id": hospital_id, "hospital_name": hospital_name,
            "hospital_lat": hospital_lat, "hospital_lon": hospital_lon,
            "scene_eta_minutes": round(amb_eta, 1),
            "hospital_eta_minutes": round(hosp_eta, 1),
            "base_station_name": amb_data.get("base_station_name", "Unknown"),
            "scene_route_source": route_to_scene["source"],
            "hospital_route_source": route_to_hospital["source"],
            "status": "EN_ROUTE_TO_SCENE",
            "scene_duration_seconds": route_to_scene["duration_seconds"],
            "hospital_duration_seconds": route_to_hospital["duration_seconds"],
        }

        create_route(
            ambulance_id=amb_id, incident_id=incident_id,
            incident_number=incident_number, hospital_id=hospital_id,
            hospital_name=hospital_name, route_type="to_scene",
            geometry=route_to_scene["coordinates"],
            distance_meters=route_to_scene["distance_km"] * 1000,
            duration_seconds=route_to_scene["duration_seconds"],
        )

        await ws_manager.broadcast_event(WSEventType.INCIDENT_CREATED, incident, channel="incidents")
        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_ASSIGNED, {
                "incident_id": incident_id, "incident_number": incident_number,
                "ambulance_id": amb_id, "vehicle_number": vehicle_number,
                "ambulance_type": ambulance_type, "latitude": amb_lat,
                "longitude": amb_lon, "status": "EN_ROUTE_TO_SCENE",
                "eta_to_scene_minutes": round(amb_eta, 1),
                "distance_to_scene_km": round(amb_dist, 2),
                "base_station": amb_data.get("base_station_name", "Unknown"),
                "route_to_scene": route_to_scene["coordinates"],
                "route_to_hospital": route_to_hospital["coordinates"],
                "hospital_id": hospital_id, "hospital_name": hospital_name,
                "hospital_selection_reason": incident["hospital_selection_reason"],
                "long_routes": True,
            }, channel="ambulances",
        )

        logger.info(
            f"Demo crash: {incident_number} at {hotspot['name']} ({scenario['severity']}) | "
            f"Amb: {vehicle_number} ETA {amb_eta:.0f}min | "
            f"Hospital: {hospital.short_name} ETA {hosp_eta:.0f}min | "
            f"Route source: {route_to_scene['source']}"
        )

    async def _tick_all_ambulances(self):
        updates = []
        to_remove = []
        for amb_id, state in list(self._movement_state.items()):
            try:
                result = self._tick_single_ambulance(amb_id, state)
                if result is None:
                    to_remove.append(amb_id)
                    continue
                updates.append(result)
            except Exception as e:
                logger.error(f"Error moving ambulance {amb_id}: {e}")
                to_remove.append(amb_id)
        for amb_id in to_remove:
            self._movement_state.pop(amb_id, None)
        if updates:
            await ws_manager.broadcast_event(
                WSEventType.AMBULANCE_POSITION_UPDATE, {"ambulances": updates}, channel="ambulances",
            )

    def _tick_single_ambulance(self, amb_id: str, state: dict) -> Optional[dict]:
        progression_key = "scene_progression" if state["phase"] == "to_scene" else "hospital_progression"
        progression = state[progression_key]
        current_dist = state["current_distance_m"]
        speed = state["speed_kmh"]
        result = advance_along_route(progression, speed, current_dist)
        new_dist = result["new_distance_m"]
        pos = result["position"]
        heading = result["heading"]
        progress = result["progress"]
        eta_seconds = result["eta_seconds"]
        state["current_distance_m"] = new_dist
        eta_minutes = eta_seconds / 60.0

        amb = _ambulances_store.get(amb_id)
        if amb:
            amb.update({
                "latitude": round(pos[0], 6), "longitude": round(pos[1], 6),
                "heading": heading, "speed_kmh": round(speed, 1),
                "route_progress": progress,
                "last_location_update": datetime.utcnow().isoformat(),
            })
            if state["phase"] == "to_scene":
                amb["eta_to_scene_minutes"] = round(eta_minutes, 1)
            else:
                amb["eta_to_hospital_minutes"] = round(eta_minutes, 1)

        route_entity = get_route_by_ambulance(amb_id)
        if route_entity:
            update_route_progress(route_entity["id"], progress, new_dist)

        if result["reached_end"]:
            if state["phase"] == "to_scene":
                asyncio.ensure_future(self._ambulance_arrived_at_scene(amb_id, state))
                return {
                    "ambulance_id": amb_id, "vehicle_number": state["vehicle_number"],
                    "ambulance_type": state["ambulance_type"],
                    "latitude": round(pos[0], 6), "longitude": round(pos[1], 6),
                    "heading": heading, "speed_kmh": round(speed, 1),
                    "status": "ON_SCENE", "incident_id": state["incident_id"],
                    "route_progress": 1.0, "eta_minutes": 0.0, "phase": "to_scene",
                }
            else:
                asyncio.ensure_future(self._ambulance_arrived_at_hospital(amb_id, state))
                return None

        return {
            "ambulance_id": amb_id, "vehicle_number": state["vehicle_number"],
            "ambulance_type": state["ambulance_type"],
            "latitude": round(pos[0], 6), "longitude": round(pos[1], 6),
            "heading": heading, "speed_kmh": round(speed, 1),
            "status": state["status"], "incident_id": state["incident_id"],
            "route_progress": round(progress, 4), "eta_minutes": round(eta_minutes, 1),
            "phase": state["phase"],
        }

    async def _ambulance_arrived_at_scene(self, amb_id: str, state: dict):
        now = datetime.utcnow().isoformat()
        state["phase"] = "to_hospital"
        state["current_distance_m"] = 0.0
        state["speed_kmh"] = SPEED_TO_HOSPITAL_KMH
        state["status"] = "TRANSPORTING"
        state["target_lat"] = state["hospital_lat"]
        state["target_lon"] = state["hospital_lon"]

        amb = _ambulances_store.get(amb_id)
        if amb:
            amb.update({
                "latitude": state["target_lat"], "longitude": state["target_lon"],
                "status": "ON_SCENE", "heading": 0.0, "speed_kmh": 0.0,
                "last_location_update": now,
            })

        incident = _incidents_store.get(state["incident_id"])
        if incident:
            incident["status"] = IncidentStatus.ON_SCENE.value
            incident["timeline"]["ambulance_arrived"] = now
            incident["version"] = incident.get("version", 0) + 1

        create_route(
            ambulance_id=amb_id, incident_id=state["incident_id"],
            incident_number=state["incident_number"],
            hospital_id=state["hospital_id"], hospital_name=state["hospital_name"],
            route_type="to_hospital",
            geometry=state["hospital_progression"]["geometry"],
            distance_meters=state["hospital_progression"]["total_distance_m"],
            duration_seconds=state["hospital_duration_seconds"],
        )

        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_STATUS_CHANGE, {
                "ambulance_id": amb_id, "vehicle_number": state["vehicle_number"],
                "status": "ON_SCENE", "latitude": state["target_lat"],
                "longitude": state["target_lon"], "incident_id": state["incident_id"],
                "timestamp": now,
            }, channel="ambulances",
        )
        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_UPDATED, {
                "id": state["incident_id"], "incident_number": state["incident_number"],
                "status": IncidentStatus.ON_SCENE.value,
                "timeline": {"ambulance_arrived": now},
                "version": incident["version"] if incident else 2,
            }, channel="incidents",
        )

        await asyncio.sleep(random.uniform(3, 6))

        if amb:
            amb.update({"status": "TRANSPORTING", "speed_kmh": SPEED_TO_HOSPITAL_KMH, "last_location_update": now})
        if incident:
            incident["status"] = IncidentStatus.TRANSPORTING.value
            incident["timeline"]["patient_picked_up"] = now
            incident["version"] = incident.get("version", 0) + 1

        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_STATUS_CHANGE, {
                "ambulance_id": amb_id, "vehicle_number": state["vehicle_number"],
                "status": "TRANSPORTING", "latitude": state["target_lat"],
                "longitude": state["target_lon"], "incident_id": state["incident_id"],
                "hospital_id": state["hospital_id"], "hospital_name": state["hospital_name"],
                "eta_to_hospital_minutes": state["hospital_eta_minutes"], "timestamp": now,
            }, channel="ambulances",
        )
        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_UPDATED, {
                "id": state["incident_id"], "incident_number": state["incident_number"],
                "status": IncidentStatus.TRANSPORTING.value,
                "timeline": {"patient_picked_up": now},
                "version": incident["version"] if incident else 3,
            }, channel="incidents",
        )

    async def _ambulance_arrived_at_hospital(self, amb_id: str, state: dict):
        now = datetime.utcnow().isoformat()
        incident = _incidents_store.get(state["incident_id"])
        if incident:
            incident["status"] = IncidentStatus.RESOLVED.value
            incident["resolved_at"] = now
            incident["timeline"]["hospital_reached"] = now
            incident["version"] = incident.get("version", 0) + 1

        amb = _ambulances_store.get(amb_id)
        if amb:
            amb.update({
                "latitude": state["hospital_lat"], "longitude": state["hospital_lon"],
                "status": "AVAILABLE", "heading": 0.0, "speed_kmh": 0.0,
                "current_incident_id": None, "assigned_hospital_id": None,
                "eta_to_scene_minutes": None, "eta_to_hospital_minutes": None,
                "route_progress": 0.0, "last_location_update": now,
            })

        hospital = next((h for h in _hospitals_store if h.id == state["hospital_id"]), None)
        if hospital and hospital.available_icu_beds > 0:
            hospital.available_icu_beds -= 1
            hospital.current_patient_load = min(hospital.max_patient_load, hospital.current_patient_load + 5)

        deactivate_route_by_ambulance(amb_id)

        await ws_manager.broadcast_event(
            WSEventType.AMBULANCE_STATUS_CHANGE, {
                "ambulance_id": amb_id, "vehicle_number": state["vehicle_number"],
                "status": "AT_HOSPITAL", "latitude": state["hospital_lat"],
                "longitude": state["hospital_lon"], "incident_id": state["incident_id"],
                "hospital_id": state["hospital_id"], "hospital_name": state["hospital_name"],
                "timestamp": now,
            }, channel="ambulances",
        )
        await ws_manager.broadcast_event(
            WSEventType.INCIDENT_UPDATED, {
                "id": state["incident_id"], "incident_number": state["incident_number"],
                "status": IncidentStatus.RESOLVED.value, "resolved_at": now,
                "timeline": {"hospital_reached": now},
                "version": incident["version"] if incident else 4,
            }, channel="incidents",
        )

        await asyncio.sleep(2)
        if amb:
            await ws_manager.broadcast_event(
                WSEventType.AMBULANCE_STATUS_CHANGE, {
                    "ambulance_id": amb_id, "vehicle_number": state["vehicle_number"],
                    "status": "AVAILABLE", "latitude": state["hospital_lat"],
                    "longitude": state["hospital_lon"], "incident_id": None, "timestamp": now,
                }, channel="ambulances",
            )
        logger.info(f"Incident {state['incident_number']} resolved — ambulance {state['vehicle_number']} delivered to {state['hospital_name']}")

    async def _update_hospital_loads(self):
        if not _hospitals_store:
            return
        updates = []
        for hospital in _hospitals_store:
            delta = random.uniform(-3, 3)
            current_load = max(10, min(hospital.max_patient_load, hospital.current_patient_load + delta))
            icu_change = 1 if random.random() < 0.1 else 0
            avail_icu = max(0, min(hospital.total_icu_beds, hospital.available_icu_beds + icu_change - (1 if random.random() < 0.05 else 0)))
            hospital.current_patient_load = int(current_load)
            hospital.available_icu_beds = avail_icu
            hospital.is_on_alert = avail_icu <= 2
            updates.append({
                "hospital_id": hospital.id, "hospital_name": hospital.name,
                "available_icu_beds": hospital.available_icu_beds,
                "current_patient_load": hospital.current_patient_load,
                "is_on_alert": hospital.is_on_alert,
                "icu_occupancy_percent": round((1 - hospital.available_icu_beds / max(hospital.total_icu_beds, 1)) * 100, 1),
            })
        await ws_manager.broadcast_event(WSEventType.HOSPITAL_STATUS_UPDATE, {"updates": updates}, channel="hospitals")

    async def build_state_snapshot(self) -> dict:
        active_incidents = [inc for inc in _incidents_store.values() if inc.get("status") not in ("RESOLVED", "FALSE_ALARM")]
        ambulances = list(_ambulances_store.values())
        active_routes = get_all_active_routes()
        hospitals = [h.to_dict() for h in _hospitals_store] if _hospitals_store else []

        route_reconstruction = []
        for route in active_routes:
            amb_id = route.get("_ambulance_key") or route["ambulance_id"]
            movement = self._movement_state.get(amb_id)
            if movement:
                current_dist = movement.get("current_distance_m", 0.0)
                phase = movement.get("phase", "to_scene")
                progression = movement.get("scene_progression" if phase == "to_scene" else "hospital_progression", {})
                total_m = progression.get("total_distance_m", 0.0)
                progress = current_dist / max(total_m, 1)
                speed = movement.get("speed_kmh", 0)
                pos_result = advance_along_route(progression, speed, current_dist, tick_seconds=0)
                pos = pos_result["position"]
                heading = pos_result["heading"]
            else:
                amb = _ambulances_store.get(amb_id)
                pos = (amb["latitude"], amb["longitude"]) if amb else (12.97, 77.59)
                heading = amb.get("heading", 0.0) if amb else 0.0
                progress = route.get("progress", 0.0)

            route_reconstruction.append({
                "ambulance_id": amb_id, "incident_id": route["incident_id"],
                "incident_number": route["incident_number"],
                "route_type": route["route_type"], "geometry": route["geometry"],
                "current_lat": round(pos[0], 6), "current_lon": round(pos[1], 6),
                "heading": heading, "progress": progress,
                "hospital_name": route["hospital_name"], "hospital_id": route["hospital_id"],
            })

        return {
            "active_incidents": active_incidents, "ambulances": ambulances,
            "active_routes": route_reconstruction, "hospitals": hospitals,
            "sim_tick": self._sim_tick, "demo_mode": True,
        }


# Singleton instance
demo_simulator = DemoSimulator()