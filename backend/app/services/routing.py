"""
Road Routing Service — OSRM + straight-line fallback.

Uses the public OSRM demo server (router.project-osrm.org) which provides
real road-following routes for free with no API key.
Falls back to straight-line interpolation if OSRM is unavailable.
"""
from __future__ import annotations

import asyncio
import logging
import math
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Public OSRM demo server — no API key required
OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"

# Simple in-process route cache (key → route dict)
_route_cache: dict[str, dict] = {}
_MAX_CACHE = 500


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
    num_points: int = 10,
) -> dict:
    """Fallback: interpolated straight-line route."""
    coords = [
        [
            origin_lat + (dest_lat - origin_lat) * i / (num_points - 1),
            origin_lon + (dest_lon - origin_lon) * i / (num_points - 1),
        ]
        for i in range(num_points)
    ]
    dist_km = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    # Assume 40 km/h average city speed for ambulance
    duration_s = (dist_km / 40.0) * 3600
    return {
        "coordinates": coords,          # list of [lat, lon]
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

    # OSRM expects lon,lat order
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
        # GeoJSON coordinates are [lon, lat] — flip to [lat, lon] for Leaflet
        geojson_coords = route["geometry"]["coordinates"]
        coords = [[c[1], c[0]] for c in geojson_coords]

        result = {
            "coordinates": coords,
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_seconds": round(route["duration"]),
            "duration_minutes": round(route["duration"] / 60, 1),
            "source": "osrm",
        }

        # Cache (evict oldest if full)
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
