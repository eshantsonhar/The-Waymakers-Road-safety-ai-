"""
Active routes API and in-memory store.
Each route is an explicit entity linking ambulance, incident, and hospital.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Optional, List
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/routes", tags=["Routes"])

# In-memory store for active route entities
# Key: route_id (unique), Value: route dict
_active_routes_store: Dict[str, dict] = {}


def create_route(
    ambulance_id: str,
    incident_id: str,
    incident_number: str,
    hospital_id: str,
    hospital_name: str,
    route_type: str,  # "to_scene" | "to_hospital"
    geometry: list,
    distance_meters: float,
    duration_seconds: float,
    traffic_delay: float = 0.0,
) -> dict:
    """Create a new active route entity and store it."""
    route_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    route = {
        "id": route_id,
        "ambulance_id": ambulance_id,
        "incident_id": incident_id,
        "incident_number": incident_number,
        "hospital_id": hospital_id,
        "hospital_name": hospital_name,
        "route_type": route_type,
        "geometry": geometry,
        "distance_meters": distance_meters,
        "duration_seconds": duration_seconds,
        "traffic_delay": traffic_delay,
        "progress": 0.0,
        "distance_traveled_m": 0.0,
        "created_at": now,
        "updated_at": now,
        "is_active": True,
    }

    # Also index by ambulance_id for quick lookups
    route["_ambulance_key"] = ambulance_id
    _active_routes_store[route_id] = route
    return route


def update_route_progress(route_id: str, progress: float, distance_traveled_m: float) -> Optional[dict]:
    """Update route progress in the store."""
    route = _active_routes_store.get(route_id)
    if route:
        route["progress"] = progress
        route["distance_traveled_m"] = distance_traveled_m
        route["updated_at"] = datetime.utcnow().isoformat()
        if progress >= 1.0:
            route["is_active"] = False
        return route
    return None


def get_route_by_ambulance(ambulance_id: str) -> Optional[dict]:
    """Find active route for a given ambulance."""
    for route in _active_routes_store.values():
        if route.get("_ambulance_key") == ambulance_id and route.get("is_active", False):
            return route
    return None


def get_all_active_routes() -> List[dict]:
    """Get all currently active routes."""
    return [r for r in _active_routes_store.values() if r.get("is_active", False)]


def deactivate_route(route_id: str):
    """Mark a route as inactive."""
    route = _active_routes_store.get(route_id)
    if route:
        route["is_active"] = False
        route["updated_at"] = datetime.utcnow().isoformat()


def deactivate_route_by_ambulance(ambulance_id: str):
    """Deactivate all routes for a given ambulance."""
    for route in _active_routes_store.values():
        if route.get("_ambulance_key") == ambulance_id:
            route["is_active"] = False
            route["updated_at"] = datetime.utcnow().isoformat()


@router.get("/")
async def list_active_routes():
    """List all currently active routes."""
    return {
        "routes": get_all_active_routes(),
        "total": len(_active_routes_store),
    }


@router.get("/{ambulance_id}")
async def get_ambulance_route(ambulance_id: str):
    """Get the active route for a specific ambulance."""
    route = get_route_by_ambulance(ambulance_id)
    if not route:
        raise HTTPException(status_code=404, detail="No active route found for this ambulance")
    return route