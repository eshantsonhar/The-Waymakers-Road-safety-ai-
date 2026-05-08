"""
Ambulance tracking API endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import random
import math
from datetime import datetime

from app.websocket.manager import ws_manager, WSEventType

router = APIRouter(prefix="/api/ambulances", tags=["Ambulances"])

# In-memory ambulance store
_ambulances_store: dict = {}


def _init_demo_ambulances():
    """Initialize demo ambulances around Bangalore."""
    base_stations = [
        {"name": "Silk Board Station", "lat": 12.9177, "lon": 77.6228},
        {"name": "Marathahalli Station", "lat": 12.9591, "lon": 77.6974},
        {"name": "Hebbal Station", "lat": 13.0358, "lon": 77.5970},
        {"name": "Koramangala Station", "lat": 12.9352, "lon": 77.6245},
        {"name": "Yeshwanthpur Station", "lat": 13.0280, "lon": 77.5540},
        {"name": "Electronic City Station", "lat": 12.8399, "lon": 77.6770},
        {"name": "Whitefield Station", "lat": 12.9698, "lon": 77.7499},
        {"name": "Kengeri Station", "lat": 12.9100, "lon": 77.4900},
    ]

    ambulance_types = ["BLS", "ALS", "MICU", "BLS", "ALS", "BLS"]

    for i, station in enumerate(base_stations):
        for j in range(3):  # 3 ambulances per station
            amb_id = str(uuid.uuid4())
            amb_lat = station["lat"] + random.uniform(-0.01, 0.01)
            amb_lon = station["lon"] + random.uniform(-0.01, 0.01)

            _ambulances_store[amb_id] = {
                "id": amb_id,
                "vehicle_number": f"KA-01-{random.randint(1000, 9999)}",
                "call_sign": f"AMB-{i*3+j+1:03d}",
                "ambulance_type": random.choice(ambulance_types),
                "latitude": amb_lat,
                "longitude": amb_lon,
                "heading": random.uniform(0, 360),
                "speed_kmh": 0.0,
                "status": "AVAILABLE",
                "is_active": True,
                "current_incident_id": None,
                "assigned_hospital_id": None,
                "crew_count": 2,
                "has_paramedic": True,
                "has_doctor": random.random() < 0.3,
                "base_station_name": station["name"],
                "base_latitude": station["lat"],
                "base_longitude": station["lon"],
                "eta_to_scene_minutes": None,
                "eta_to_hospital_minutes": None,
                "current_route": [],
                "route_progress": 0.0,
                "equipment": ["Defibrillator", "Oxygen", "First Aid Kit", "Stretcher"],
                "last_location_update": datetime.utcnow().isoformat(),
            }


# Initialize on module load
_init_demo_ambulances()


@router.get("/")
async def list_ambulances(
    status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    limit: int = Query(100, le=500),
):
    """List all ambulances with optional filters."""
    ambulances = list(_ambulances_store.values())

    if status:
        ambulances = [a for a in ambulances if a["status"] == status.upper()]
    if is_active is not None:
        ambulances = [a for a in ambulances if a["is_active"] == is_active]

    return {
        "ambulances": ambulances[:limit],
        "total": len(ambulances),
        "available": sum(1 for a in ambulances if a["status"] == "AVAILABLE"),
        "deployed": sum(1 for a in ambulances if a["status"] not in ("AVAILABLE", "OFFLINE", "MAINTENANCE")),
    }


@router.get("/nearby")
async def get_nearby_ambulances(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = Query(20.0, le=50.0),
    limit: int = Query(5, le=20),
):
    """Find nearest available ambulances within radius."""
    available = [a for a in _ambulances_store.values() if a["status"] == "AVAILABLE" and a["is_active"]]

    # Compute distances
    with_distance = []
    for amb in available:
        dist = _haversine(latitude, longitude, amb["latitude"], amb["longitude"])
        if dist <= radius_km:
            amb_copy = dict(amb)
            amb_copy["distance_km"] = round(dist, 2)
            amb_copy["eta_minutes"] = round(dist / 60 * 60, 1)
            with_distance.append(amb_copy)

    with_distance.sort(key=lambda x: x["distance_km"])

    return {
        "nearby_ambulances": with_distance[:limit],
        "total_found": len(with_distance),
        "search_radius_km": radius_km,
    }


@router.get("/stats")
async def get_ambulance_stats():
    """Get aggregate ambulance statistics."""
    ambulances = list(_ambulances_store.values())
    status_counts = {}
    for a in ambulances:
        status_counts[a["status"]] = status_counts.get(a["status"], 0) + 1

    return {
        "total": len(ambulances),
        "available": status_counts.get("AVAILABLE", 0),
        "deployed": sum(v for k, v in status_counts.items() if k not in ("AVAILABLE", "OFFLINE", "MAINTENANCE")),
        "offline": status_counts.get("OFFLINE", 0),
        "status_breakdown": status_counts,
    }


@router.get("/{ambulance_id}")
async def get_ambulance(ambulance_id: str):
    """Get a specific ambulance by ID."""
    amb = _ambulances_store.get(ambulance_id)
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    return amb


@router.patch("/{ambulance_id}/position")
async def update_ambulance_position(
    ambulance_id: str,
    latitude: float,
    longitude: float,
    heading: float = 0.0,
    speed_kmh: float = 0.0,
):
    """Update ambulance GPS position."""
    amb = _ambulances_store.get(ambulance_id)
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")

    amb["latitude"] = latitude
    amb["longitude"] = longitude
    amb["heading"] = heading
    amb["speed_kmh"] = speed_kmh
    amb["last_location_update"] = datetime.utcnow().isoformat()

    await ws_manager.broadcast_event(
        WSEventType.AMBULANCE_POSITION_UPDATE,
        {
            "ambulances": [{
                "ambulance_id": ambulance_id,
                "latitude": latitude,
                "longitude": longitude,
                "heading": heading,
                "speed_kmh": speed_kmh,
            }]
        },
        channel="ambulances",
    )

    return {"message": "Position updated", "ambulance_id": ambulance_id}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
