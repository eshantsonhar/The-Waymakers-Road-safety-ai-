"""
Road Routing Service — OSRM + straight-line fallback.

Uses the public OSRM demo server (router.project-osrm.org) which provides
real road-following routes for free with no API key.
Falls back to straight-line interpolation if OSRM is unavailable.

Route Progression Engine:
- Precomputes cumulative distances along route geometry.
- Advances ambulances by meters/second along the cumulative distance.
- Interpolates position continuously for smooth motion, correct heading, and stable ETA.
"""
from __future__ import annotations

import asyncio
import logging
import math
from typing import Optional, List, Tuple

import httpx

logger = logging.getLogger(__name__)

# Public OSRM demo server — no API key required
OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"

# Simple in-process route cache (key → route dict)
_route_cache: dict[str, dict] = {}
_MAX_CACHE = 500

# Default ambulance speeds (km/h) by phase
SPEED_TO_SCENE_KMH = 60.0
SPEED_TO_HOSPITAL_KMH = 50.0

# Simulation tick rate
SIMULATION_TICK_SECONDS = 1.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Geodesic distance in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _straight_line_route(
    origin_lat: float, origin_lon: float,
    dest_lat: float, dest_lon: float,
    num_points: int = 50,
) -> dict:
    """Fallback: interpolated straight-line route with dense points."""
    coords = [
        [
            origin_lat + (dest_lat - origin_lat) * i / (num_points - 1),
            origin_lon + (dest_lon - origin_lon) * i / (num_points - 1),
        ]
        for i in range(num_points)
    ]
    dist_km = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    duration_s = (dist_km / 40.0) * 3600
    return {
        "coordinates": coords,
        "distance_km": round(dist_km, 2),
        "duration_seconds": round(duration_s),
        "duration_minutes": round(duration_s / 60, 1),
        "source": "straight_line",
    }


async def get_route(
    origin_lat: float, origin_lon: float,
    dest_lat: float, dest_lon: float,
    timeout: float = 6.0,
) -> dict:
    """
    Get a road-following route between two coordinates.

    Returns:
        coordinates: list of [lat, lon] pairs following the road
        distance_km: total road distance
        duration_seconds: estimated travel time
        duration_minutes: estimated travel time in minutes
        source: 'osrm' or 'straight_line'
    """
    cache_key = f"{origin_lat:.4f},{origin_lon:.4f}->{dest_lat:.4f},{dest_lon:.4f}"
    if cache_key in _route_cache:
        return _route_cache[cache_key]

    url = f"{OSRM_BASE}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"OSRM returned: {data.get('code')}")

        route = data["routes"][0]
        geojson_coords = route["geometry"]["coordinates"]
        coords = [[c[1], c[0]] for c in geojson_coords]

        result = {
            "coordinates": coords,
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_seconds": round(route["duration"]),
            "duration_minutes": round(route["duration"] / 60, 1),
            "source": "osrm",
        }

        if len(_route_cache) >= _MAX_CACHE:
            oldest = next(iter(_route_cache))
            del _route_cache[oldest]
        _route_cache[cache_key] = result

        logger.debug(
            f"OSRM route: {result['distance_km']} km, "
            f"{result['duration_minutes']} min ({len(coords)} waypoints)"
        )
        return result

    except Exception as exc:
        logger.warning(f"OSRM routing failed ({exc}), using straight-line fallback")
        return _straight_line_route(origin_lat, origin_lon, dest_lat, dest_lon)


def get_route_sync(
    origin_lat: float, origin_lon: float,
    dest_lat: float, dest_lon: float,
) -> dict:
    """Synchronous wrapper — only use outside async context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return _straight_line_route(origin_lat, origin_lon, dest_lat, dest_lon)
        return loop.run_until_complete(
            get_route(origin_lat, origin_lon, dest_lat, dest_lon)
        )
    except Exception:
        return _straight_line_route(origin_lat, origin_lon, dest_lat, dest_lon)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE PROGRESSION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def precompute_route_progression(coordinates: List[Tuple[float, float]]) -> dict:
    """
    Precompute cumulative distances along a route geometry.

    Args:
        coordinates: List of [lat, lon] pairs.

    Returns:
        dict with:
            geometry: same coordinates
            cumulative_distances: list of cumulative distances in meters
            total_distance_m: total route distance in meters
    """
    if not coordinates:
        return {
            "geometry": [],
            "cumulative_distances": [],
            "total_distance_m": 0.0,
        }

    cumulative = [0.0]
    for i in range(1, len(coordinates)):
        seg_dist = _haversine_km(
            coordinates[i - 1][0], coordinates[i - 1][1],
            coordinates[i][0], coordinates[i][1],
        ) * 1000.0  # km → m
        cumulative.append(cumulative[-1] + seg_dist)

    total = cumulative[-1]
    return {
        "geometry": coordinates,
        "cumulative_distances": cumulative,
        "total_distance_m": total,
    }


def advance_along_route(
    route_progression: dict,
    speed_kmh: float,
    current_distance_m: float,
    tick_seconds: float = SIMULATION_TICK_SECONDS,
) -> dict:
    """
    Advance an ambulance along a precomputed route for one tick.

    Args:
        route_progression: Output from precompute_route_progression()
        speed_kmh: Current speed in km/h
        current_distance_m: Distance already traveled in meters
        tick_seconds: Duration of simulation tick in seconds

    Returns:
        dict with:
            position: [lat, lon] interpolated position
            heading: heading in degrees
            distance_traveled_m: total distance traveled in this tick
            new_distance_m: new cumulative distance traveled
            progress: 0.0–1.0 fraction of route completed
            eta_seconds: remaining time in seconds
            reached_end: bool
    """
    geometry = route_progression["geometry"]
    cumulative = route_progression["cumulative_distances"]
    total = route_progression["total_distance_m"]

    if not geometry or total <= 0:
        return {
            "position": geometry[0] if geometry else [0.0, 0.0],
            "heading": 0.0,
            "distance_traveled_m": 0.0,
            "new_distance_m": 0.0,
            "progress": 1.0,
            "eta_seconds": 0.0,
            "reached_end": True,
        }

    # Convert speed to meters per second
    speed_ms = speed_kmh * 1000.0 / 3600.0
    distance_per_tick = speed_ms * tick_seconds

    new_distance = min(current_distance_m + distance_per_tick, total)
    actual_traveled = new_distance - current_distance_m
    progress = new_distance / total if total > 0 else 1.0
    reached_end = new_distance >= total

    # Interpolate position along cumulative distance
    position, heading = _interpolate_position(geometry, cumulative, new_distance)

    # Compute ETA
    remaining_m = max(0.0, total - new_distance)
    eta_seconds = remaining_m / max(speed_ms, 0.1) if speed_ms > 0 else 0.0

    return {
        "position": position,
        "heading": heading,
        "distance_traveled_m": round(actual_traveled, 2),
        "new_distance_m": round(new_distance, 2),
        "progress": round(progress, 4),
        "eta_seconds": round(eta_seconds, 1),
        "reached_end": reached_end,
    }


def _interpolate_position(
    geometry: List[Tuple[float, float]],
    cumulative: List[float],
    distance_m: float,
) -> Tuple[Tuple[float, float], float]:
    """
    Interpolate position and heading along a route at a given cumulative distance.

    Returns:
        (lat, lon), heading_degrees
    """
    if distance_m <= 0:
        # Return first point
        prev_lat, prev_lon = geometry[0]
        next_lat, next_lon = geometry[1] if len(geometry) > 1 else (prev_lat, prev_lon)
        heading = _compute_heading(prev_lat, prev_lon, next_lat, next_lon)
        return (prev_lat, prev_lon), heading

    if distance_m >= cumulative[-1]:
        lat, lon = geometry[-1]
        prev_lat, prev_lon = geometry[-2] if len(geometry) > 1 else (lat, lon)
        heading = _compute_heading(prev_lat, prev_lon, lat, lon)
        return (lat, lon), heading

    # Find the segment containing this distance
    seg_idx = 0
    for i in range(1, len(cumulative)):
        if cumulative[i] >= distance_m:
            seg_idx = i - 1
            break

    seg_start = cumulative[seg_idx]
    seg_end = cumulative[seg_idx + 1]
    seg_length = seg_end - seg_start

    if seg_length <= 0:
        return geometry[seg_idx], 0.0

    # Fraction along this segment
    t = (distance_m - seg_start) / seg_length
    t = max(0.0, min(1.0, t))

    lat1, lon1 = geometry[seg_idx]
    lat2, lon2 = geometry[seg_idx + 1]

    # Linear interpolation
    lat = lat1 + (lat2 - lat1) * t
    lon = lon1 + (lon2 - lon1) * t

    heading = _compute_heading(lat1, lon1, lat2, lon2)

    return (lat, lon), heading


def _compute_heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute heading (degrees from north) between two coordinates."""
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    heading = (math.degrees(math.atan2(y, x)) + 360) % 360
    return round(heading, 1)