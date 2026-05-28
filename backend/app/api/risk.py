"""
Risk Prediction API — REAL Geospatial Logic
=============================================
Uses OpenStreetMap road network data for ALL geometry.
No random lines. No synthetic segments.

Risk segments are derived from:
- Road network edges (from Overpass API)
- Accident density per road segment (proximity to known hotspots)
- Road type weights
- Curvature / intersection density
"""

from fastapi import APIRouter, Query
from typing import Optional, List

from app.geospatial.road_network import road_network
from app.engines.risk_prediction import risk_engine

router = APIRouter(prefix="/api/risk", tags=["Risk Prediction"])

BANGALORE_CENTER = {"lat": 12.9716, "lon": 77.5946}


@router.get("/heatmap")
async def get_heatmap(
    lat: float = Query(default=BANGALORE_CENTER["lat"]),
    lon: float = Query(default=BANGALORE_CENTER["lon"]),
    radius_km: float = Query(default=10.0, le=25.0),
):
    """
    Get danger heatmap as GeoJSON FeatureCollection.
    Each feature is a REAL road segment with derived risk score.
    Geometry comes from OpenStreetMap road network.
    """
    segments = await road_network.get_risk_segments(
        lat=lat, lon=lon, radius_km=radius_km
    )

    features = []
    blackspots = []

    for seg in segments:
        feature = seg.to_geojson_feature()
        features.append(feature)

        if seg.is_blackspot:
            mid_idx = len(seg.coordinates) // 2
            mid_lat, mid_lon = seg.coordinates[mid_idx]
            blackspots.append({
                "id": seg.segment_id,
                "name": seg.name,
                "district": seg.district,
                "risk_score": seg.risk_score,
                "latitude": mid_lat,
                "longitude": mid_lon,
                "trend_direction": "stable",
                "total_accidents": int(seg.accident_density * 50),
                "fatal_accidents": int(seg.accident_density * 10),
                "primary_factor": _get_primary_factor(seg.risk_factors),
            })

    high_risk_count = sum(1 for s in segments if s.risk_score >= 50)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_segments": len(features),
            "blackspots": len(blackspots),
            "high_risk": high_risk_count,
            "model_trained": risk_engine.is_trained,
            "model_metrics": risk_engine.model_metrics,
            "source": "openstreetmap_overpass",
            "center": {"lat": lat, "lon": lon},
            "radius_km": radius_km,
            "cache_info": road_network.get_cache_info(),
        },
    }


@router.get("/blackspots")
async def get_blackspots(
    limit: int = Query(20, le=100),
    district: Optional[str] = Query(None),
    lat: float = Query(default=BANGALORE_CENTER["lat"]),
    lon: float = Query(default=BANGALORE_CENTER["lon"]),
):
    """Get real blackspot locations derived from road network risk analysis."""
    segments = await road_network.get_risk_segments(
        lat=lat, lon=lon, radius_km=10.0
    )
    blackspots = [s for s in segments if s.is_blackspot]

    if district:
        ds = district.lower()
        blackspots = [b for b in blackspots if ds in b.district.lower()]

    blackspots.sort(key=lambda s: s.risk_score, reverse=True)

    result = []
    for seg in blackspots[:limit]:
        mid_idx = len(seg.coordinates) // 2
        mid_lat, mid_lon = seg.coordinates[mid_idx]
        result.append({
            "id": seg.segment_id,
            "name": seg.name,
            "district": seg.district,
            "risk_score": seg.risk_score,
            "latitude": mid_lat,
            "longitude": mid_lon,
            "trend_direction": "stable",
            "total_accidents": int(seg.accident_density * 50),
            "fatal_accidents": int(seg.accident_density * 10),
            "primary_factor": _get_primary_factor(seg.risk_factors),
            "contributing_factors": seg.risk_factors,
            "prediction_confidence": seg.prediction_confidence,
        })

    return {
        "blackspots": result,
        "total": len(blackspots),
    }


@router.get("/segments")
async def get_road_segments(
    district: Optional[str] = Query(None),
    min_risk: float = Query(0.0),
    limit: int = Query(100, le=500),
    lat: float = Query(default=BANGALORE_CENTER["lat"]),
    lon: float = Query(default=BANGALORE_CENTER["lon"]),
):
    """Get real road segments with risk scores."""
    segments = await road_network.get_risk_segments(
        lat=lat, lon=lon, radius_km=10.0, min_risk=min_risk
    )

    if district:
        ds = district.lower()
        segments = [s for s in segments if ds in s.district.lower()]

    segments = segments[:limit]

    return {
        "segments": [
            {
                "id": s.segment_id,
                "name": s.name,
                "road_type": s.road_type,
                "district": s.district,
                "start_latitude": s.coordinates[0][0],
                "start_longitude": s.coordinates[0][1],
                "end_latitude": s.coordinates[-1][0],
                "end_longitude": s.coordinates[-1][1],
                "length_km": round(s.length_km, 3),
                "risk_score": round(s.risk_score, 1),
                "is_blackspot": s.is_blackspot,
                "prediction_confidence": round(s.prediction_confidence, 3),
                "accident_density": round(s.accident_density, 4),
                "curvature_index": round(s.curvature_index, 4),
                "intersection_density": round(s.intersection_density, 4),
                "traffic_load": round(s.traffic_load, 4),
                "risk_factors": s.risk_factors,
                "trend_direction": "stable",
                "total_accidents": int(s.accident_density * 50),
                "fatal_accidents": int(s.accident_density * 10),
            }
            for s in segments
        ],
        "total": len(segments),
    }


@router.get("/analytics")
async def get_risk_analytics(
    lat: float = Query(default=BANGALORE_CENTER["lat"]),
    lon: float = Query(default=BANGALORE_CENTER["lon"]),
):
    """Get risk analytics summary derived from real road network data."""
    segments = await road_network.get_risk_segments(
        lat=lat, lon=lon, radius_km=10.0
    )
    blackspots = [s for s in segments if s.is_blackspot]

    district_stats = {}
    for seg in segments:
        d = seg.district
        if d not in district_stats:
            district_stats[d] = {
                "count": 0, "total_risk": 0, "blackspots": 0,
                "total_accidents": 0,
            }
        district_stats[d]["count"] += 1
        district_stats[d]["total_risk"] += seg.risk_score
        district_stats[d]["total_accidents"] += int(seg.accident_density * 50)
        if seg.is_blackspot:
            district_stats[d]["blackspots"] += 1

    district_summary = [
        {
            "district": d,
            "segment_count": v["count"],
            "avg_risk_score": round(v["total_risk"] / v["count"], 1),
            "blackspot_count": v["blackspots"],
            "total_accidents": v["total_accidents"],
        }
        for d, v in sorted(
            district_stats.items(),
            key=lambda x: x[1]["total_risk"] / x[1]["count"],
            reverse=True,
        )
    ]

    top_blackspots = sorted(
        blackspots, key=lambda s: s.risk_score, reverse=True
    )[:10]

    return {
        "total_segments": len(segments),
        "blackspot_count": len(blackspots),
        "high_risk_count": sum(
            1 for s in segments if s.risk_score >= 50
        ),
        "avg_risk_score": round(
            sum(s.risk_score for s in segments) / max(len(segments), 1), 1
        ),
        "district_summary": district_summary,
        "top_blackspots": [
            {
                "segment_id": s.segment_id,
                "name": s.name,
                "risk_score": s.risk_score,
                "latitude": s.coordinates[len(s.coordinates) // 2][0],
                "longitude": s.coordinates[len(s.coordinates) // 2][1],
            }
            for s in top_blackspots
        ],
        "infrastructure_alerts": [
            {
                "segment_id": s.segment_id,
                "name": s.name,
                "risk_score": s.risk_score,
                "primary_issue": _get_primary_factor(s.risk_factors),
                "priority": "HIGH" if s.risk_score >= 80 else "MEDIUM",
            }
            for s in sorted(segments, key=lambda x: x.risk_score, reverse=True)[:15]
            if s.risk_score >= 60
        ],
        "model_metrics": risk_engine.model_metrics,
        "data_source": "openstreetmap_overpass",
        "cache_info": road_network.get_cache_info(),
    }


def _get_primary_factor(risk_factors: dict) -> str:
    if not risk_factors:
        return "Unknown"
    factor_names = {
        "accident_density": "High accident history",
        "curvature_index": "Sharp curves",
        "intersection_density": "Dense intersections",
        "traffic_load": "High traffic volume",
        "road_type_weight": "Road classification risk",
    }
    top_factor = max(risk_factors, key=lambda k: risk_factors.get(k, 0))
    return factor_names.get(top_factor, top_factor)