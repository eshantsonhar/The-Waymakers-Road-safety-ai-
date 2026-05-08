"""
Risk Prediction API endpoints.
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import random
import math

from app.engines.risk_prediction import risk_engine
from app.config import settings

router = APIRouter(prefix="/api/risk", tags=["Risk Prediction"])

# Mock road segments for demo
_road_segments_cache: list = []


def _generate_mock_segments():
    """Generate mock Bangalore road segments with risk data."""
    segments = []
    hotspots = [
        ("Silk Board Junction", 12.9177, 77.6228, "Bommanahalli", "arterial"),
        ("Marathahalli Bridge", 12.9591, 77.6974, "Mahadevapura", "arterial"),
        ("KR Puram Bridge", 13.0050, 77.6960, "Mahadevapura", "highway"),
        ("Hebbal Flyover", 13.0358, 77.5970, "Yelahanka", "highway"),
        ("Tin Factory Junction", 12.9985, 77.6608, "Mahadevapura", "arterial"),
        ("Bannerghatta Road", 12.8900, 77.5970, "Bommanahalli", "arterial"),
        ("Outer Ring Road Bellandur", 12.9304, 77.6784, "Mahadevapura", "highway"),
        ("Hosur Road Electronic City", 12.8399, 77.6770, "Bommanahalli", "highway"),
        ("Tumkur Road Yeshwanthpur", 13.0280, 77.5540, "Dasarahalli", "highway"),
        ("Old Madras Road", 12.9900, 77.6500, "Mahadevapura", "arterial"),
        ("Mysore Road Kengeri", 12.9100, 77.4900, "Rajarajeshwari Nagar", "highway"),
        ("Bellary Road Hebbal", 13.0450, 77.5900, "Yelahanka", "highway"),
        ("Sarjapur Road", 12.9100, 77.6900, "Mahadevapura", "arterial"),
        ("Whitefield Main Road", 12.9698, 77.7499, "Mahadevapura", "arterial"),
        ("Koramangala 80ft Road", 12.9352, 77.6245, "Bommanahalli", "collector"),
        ("MG Road", 12.9757, 77.6011, "Shivajinagar", "arterial"),
        ("Brigade Road", 12.9719, 77.6069, "Shivajinagar", "collector"),
        ("Residency Road", 12.9700, 77.6100, "Shivajinagar", "collector"),
        ("Airport Road", 13.0100, 77.6200, "Yelahanka", "highway"),
        ("Hennur Road", 13.0200, 77.6400, "Yelahanka", "arterial"),
    ]

    for i, (name, lat, lon, district, road_type) in enumerate(hotspots):
        # Generate realistic risk factors
        accident_freq = random.uniform(2, 18)
        surface = random.uniform(0.3, 0.9)
        curvature = random.uniform(0.05, 0.6)
        pothole_density = random.uniform(0.5, 8.0)

        risk_score, confidence, factors = risk_engine.compute_risk_score(
            accident_frequency_per_year=accident_freq,
            surface_condition=surface,
            rainfall_intensity=random.uniform(0.0, 0.4),
            lighting_level=random.uniform(0.4, 0.9),
            traffic_density=random.uniform(0.3, 0.9),
            curvature_index=curvature,
            pothole_density=pothole_density,
        )

        # Add more segments around each hotspot
        for j in range(5):
            seg_lat = lat + random.uniform(-0.01, 0.01)
            seg_lon = lon + random.uniform(-0.01, 0.01)
            seg_risk = max(0, min(100, risk_score + random.uniform(-15, 15)))

            segments.append({
                "id": f"seg-{i:03d}-{j:02d}",
                "name": f"{name} - Segment {j+1}",
                "road_type": road_type,
                "district": district,
                "start_latitude": seg_lat,
                "start_longitude": seg_lon,
                "end_latitude": seg_lat + random.uniform(0.002, 0.008),
                "end_longitude": seg_lon + random.uniform(0.002, 0.008),
                "length_km": random.uniform(0.3, 1.5),
                "speed_limit_kmh": 60 if road_type == "arterial" else 80,
                "surface_condition": surface + random.uniform(-0.1, 0.1),
                "curvature_index": curvature,
                "pothole_density": pothole_density,
                "risk_score": round(seg_risk, 1),
                "accident_frequency_per_year": round(accident_freq + random.uniform(-2, 2), 1),
                "is_blackspot": seg_risk >= settings.BLACKSPOT_RISK_THRESHOLD,
                "prediction_confidence": round(confidence + random.uniform(-0.1, 0.1), 3),
                "total_accidents": random.randint(5, 50),
                "fatal_accidents": random.randint(0, 5),
                "risk_factors": {
                    "accident_frequency": round(factors.get("accident_frequency", 0), 3),
                    "surface_condition": round(factors.get("surface_condition", 0), 3),
                    "curvature": round(factors.get("curvature", 0), 3),
                    "pothole_density": round(factors.get("pothole_density", 0), 3),
                },
                "trend_direction": random.choice(["improving", "stable", "worsening"]),
            })

    return segments


# Initialize on module load
_road_segments_cache = _generate_mock_segments()


@router.get("/heatmap")
async def get_heatmap():
    """
    Get danger heatmap as GeoJSON FeatureCollection.
    Each feature represents a road segment with risk score.
    """

    class MockSegment:
        pass

    features = []
    blackspots = []

    for seg in _road_segments_cache:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [seg["start_longitude"], seg["start_latitude"]],
                    [seg["end_longitude"], seg["end_latitude"]],
                ],
            },
            "properties": {
                "id": seg["id"],
                "name": seg["name"],
                "district": seg["district"],
                "risk_score": seg["risk_score"],
                "is_blackspot": seg["is_blackspot"],
                "prediction_confidence": seg["prediction_confidence"],
                "accident_frequency": seg["accident_frequency_per_year"],
                "road_type": seg["road_type"],
                "risk_color": _risk_to_color(seg["risk_score"]),
                "risk_level": _risk_to_level(seg["risk_score"]),
                "contributing_factors": seg["risk_factors"],
            },
        }
        features.append(feature)

        if seg["is_blackspot"]:
            blackspots.append({
                "id": seg["id"],
                "name": seg["name"],
                "district": seg["district"],
                "risk_score": seg["risk_score"],
                "latitude": seg["start_latitude"],
                "longitude": seg["start_longitude"],
                "trend_direction": seg["trend_direction"],
                "total_accidents": seg["total_accidents"],
                "fatal_accidents": seg["fatal_accidents"],
                "primary_factor": _get_primary_factor(seg["risk_factors"]),
            })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_segments": len(features),
            "blackspots": len(blackspots),
            "high_risk": sum(1 for s in _road_segments_cache if s["risk_score"] >= 50),
            "model_trained": risk_engine.is_trained,
            "model_metrics": risk_engine.model_metrics,
        },
    }


@router.get("/blackspots")
async def get_blackspots(
    limit: int = Query(20, le=100),
    district: Optional[str] = Query(None),
):
    """Get list of active blackspot locations."""
    blackspots = [s for s in _road_segments_cache if s["is_blackspot"]]

    if district:
        blackspots = [b for b in blackspots if district.lower() in b.get("district", "").lower()]

    blackspots.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "blackspots": [
            {
                "id": b["id"],
                "name": b["name"],
                "district": b["district"],
                "risk_score": b["risk_score"],
                "latitude": b["start_latitude"],
                "longitude": b["start_longitude"],
                "trend_direction": b["trend_direction"],
                "total_accidents": b["total_accidents"],
                "fatal_accidents": b["fatal_accidents"],
                "primary_factor": _get_primary_factor(b["risk_factors"]),
                "contributing_factors": b["risk_factors"],
                "prediction_confidence": b["prediction_confidence"],
            }
            for b in blackspots[:limit]
        ],
        "total": len(blackspots),
    }


@router.get("/segments")
async def get_road_segments(
    district: Optional[str] = Query(None),
    min_risk: float = Query(0.0),
    limit: int = Query(100, le=500),
):
    """Get road segments with risk scores."""
    segments = _road_segments_cache

    if district:
        segments = [s for s in segments if district.lower() in s.get("district", "").lower()]
    if min_risk > 0:
        segments = [s for s in segments if s["risk_score"] >= min_risk]

    segments = sorted(segments, key=lambda x: x["risk_score"], reverse=True)

    return {
        "segments": segments[:limit],
        "total": len(segments),
    }


@router.get("/analytics")
async def get_risk_analytics():
    """Get risk analytics summary for admin dashboard."""
    segments = _road_segments_cache
    blackspots = [s for s in segments if s["is_blackspot"]]

    district_stats = {}
    for seg in segments:
        d = seg.get("district", "Unknown")
        if d not in district_stats:
            district_stats[d] = {"count": 0, "total_risk": 0, "blackspots": 0, "accidents": 0}
        district_stats[d]["count"] += 1
        district_stats[d]["total_risk"] += seg["risk_score"]
        district_stats[d]["accidents"] += seg["total_accidents"]
        if seg["is_blackspot"]:
            district_stats[d]["blackspots"] += 1

    district_summary = [
        {
            "district": d,
            "segment_count": v["count"],
            "avg_risk_score": round(v["total_risk"] / v["count"], 1),
            "blackspot_count": v["blackspots"],
            "total_accidents": v["accidents"],
        }
        for d, v in district_stats.items()
    ]
    district_summary.sort(key=lambda x: x["avg_risk_score"], reverse=True)

    return {
        "total_segments": len(segments),
        "blackspot_count": len(blackspots),
        "high_risk_count": sum(1 for s in segments if s["risk_score"] >= 50),
        "avg_risk_score": round(sum(s["risk_score"] for s in segments) / max(len(segments), 1), 1),
        "district_summary": district_summary,
        "top_blackspots": sorted(blackspots, key=lambda x: x["risk_score"], reverse=True)[:10],
        "model_metrics": risk_engine.model_metrics,
        "infrastructure_alerts": [
            {
                "segment_id": s["id"],
                "name": s["name"],
                "risk_score": s["risk_score"],
                "primary_issue": _get_primary_factor(s["risk_factors"]),
                "priority": "HIGH" if s["risk_score"] >= 80 else "MEDIUM",
            }
            for s in sorted(segments, key=lambda x: x["risk_score"], reverse=True)[:15]
            if s["risk_score"] >= 60
        ],
    }


def _risk_to_color(risk_score: float) -> str:
    if risk_score >= 80:
        return "#FF0000"
    elif risk_score >= 60:
        return "#FF6600"
    elif risk_score >= 40:
        return "#FFAA00"
    elif risk_score >= 20:
        return "#FFFF00"
    else:
        return "#00FF00"


def _risk_to_level(risk_score: float) -> str:
    if risk_score >= 80:
        return "CRITICAL"
    elif risk_score >= 60:
        return "HIGH"
    elif risk_score >= 40:
        return "MODERATE"
    elif risk_score >= 20:
        return "LOW"
    else:
        return "MINIMAL"


def _get_primary_factor(risk_factors: dict) -> str:
    if not risk_factors:
        return "Unknown"
    factor_names = {
        "accident_frequency": "High accident history",
        "surface_condition": "Poor road surface",
        "curvature": "Sharp curves",
        "pothole_density": "High pothole density",
        "rainfall": "Rain-prone area",
        "lighting": "Poor lighting",
        "traffic_density": "High traffic density",
    }
    top_factor = max(risk_factors, key=lambda k: risk_factors.get(k, 0))
    return factor_names.get(top_factor, top_factor)
