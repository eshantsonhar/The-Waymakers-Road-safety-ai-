"""
Hospital Intelligence API endpoints.
"""
import math
import random
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List

from app.engines.hospital_intelligence import hospital_engine
from app.websocket.manager import ws_manager, WSEventType

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals"])

# In-memory hospital store (seeded from seed script)
_hospitals_store: list = []


def set_hospitals(hospitals: list):
    """Called by seed script to populate hospital data."""
    global _hospitals_store
    _hospitals_store = hospitals


class HospitalRankRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    severity: str = Field(default="HIGH", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    required_blood_type: Optional[str] = None
    traffic_factor: float = Field(default=1.0, ge=0.1, le=5.0)
    max_results: int = Field(default=5, ge=1, le=20)


@router.post("/rank")
async def rank_hospitals(request: HospitalRankRequest):
    """
    Rank hospitals for a given incident location and severity.
    Returns sorted list with suitability scores and recommendation explanations.
    """
    if not _hospitals_store:
        # Return mock data if not seeded
        return _get_mock_rankings(request.latitude, request.longitude, request.severity)

    rankings = hospital_engine.rank_hospitals(
        hospitals=_hospitals_store,
        incident_lat=request.latitude,
        incident_lon=request.longitude,
        severity=request.severity,
        required_blood_type=request.required_blood_type,
        traffic_factor=request.traffic_factor,
    )

    result = [
        {
            "rank": r.rank,
            "hospital_id": r.hospital_id,
            "hospital_name": r.hospital_name,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "suitability_score": r.suitability_score,
            "distance_km": r.distance_km,
            "estimated_travel_minutes": r.estimated_travel_minutes,
            "recommendation_explanation": r.recommendation_explanation,
            "score_breakdown": r.score_breakdown,
        }
        for r in rankings[:request.max_results]
    ]

    return {
        "incident_location": {"latitude": request.latitude, "longitude": request.longitude},
        "severity": request.severity,
        "total_evaluated": len(rankings),
        "rankings": result,
        "top_recommendation": result[0] if result else None,
    }


@router.get("/")
async def list_hospitals(
    district: Optional[str] = Query(None),
    has_trauma: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(True),
    limit: int = Query(50, le=200),
):
    """List all hospitals with optional filters."""
    if not _hospitals_store:
        return {"hospitals": _get_mock_hospitals(), "total": 10}

    hospitals = _hospitals_store

    if district:
        hospitals = [h for h in hospitals if h.district and district.lower() in h.district.lower()]
    if has_trauma is not None:
        hospitals = [h for h in hospitals if h.has_trauma_center == has_trauma]
    if is_active is not None:
        hospitals = [h for h in hospitals if h.is_active == is_active]

    return {
        "hospitals": [h.to_dict() for h in hospitals[:limit]],
        "total": len(hospitals),
    }


@router.get("/stats")
async def get_hospital_stats():
    """Get aggregate hospital statistics."""
    if not _hospitals_store:
        return _get_mock_hospital_stats()

    total = len(_hospitals_store)
    active = sum(1 for h in _hospitals_store if h.is_active)
    on_alert = sum(1 for h in _hospitals_store if h.is_on_alert)
    trauma_centers = sum(1 for h in _hospitals_store if h.has_trauma_center)
    total_icu = sum(h.total_icu_beds for h in _hospitals_store)
    available_icu = sum(h.available_icu_beds for h in _hospitals_store)

    return {
        "total_hospitals": total,
        "active_hospitals": active,
        "on_alert": on_alert,
        "trauma_centers": trauma_centers,
        "total_icu_beds": total_icu,
        "available_icu_beds": available_icu,
        "icu_occupancy_percent": round((1 - available_icu / max(total_icu, 1)) * 100, 1),
    }


@router.get("/{hospital_id}")
async def get_hospital(hospital_id: str):
    """Get a specific hospital by ID."""
    for h in _hospitals_store:
        if h.id == hospital_id:
            return h.to_dict()
    raise HTTPException(status_code=404, detail="Hospital not found")


def _get_mock_rankings(lat: float, lon: float, severity: str) -> dict:
    """Return mock hospital rankings when DB is not available."""
    import random
    hospitals = _get_mock_hospitals()
    for i, h in enumerate(hospitals):
        dist = math.sqrt((h["latitude"] - lat) ** 2 + (h["longitude"] - lon) ** 2) * 111
        h["rank"] = i + 1
        h["distance_km"] = round(dist, 2)
        h["estimated_travel_minutes"] = round(dist / 60 * 60, 1)
        h["suitability_score"] = round(90 - i * 8 + random.uniform(-3, 3), 1)
        h["recommendation_explanation"] = f"Recommended: {h['name']} — Level {h['trauma_level']} trauma center; {h['available_icu_beds']} ICU beds available (Score: {h['suitability_score']:.0f}/100)"
        h["score_breakdown"] = {
            "trauma_capability": round(random.uniform(60, 95), 1),
            "icu_availability": round(random.uniform(50, 90), 1),
            "travel_time": round(random.uniform(40, 85), 1),
            "distance": round(random.uniform(50, 90), 1),
            "hospital_load": round(random.uniform(40, 80), 1),
        }

    return {
        "incident_location": {"latitude": lat, "longitude": lon},
        "severity": severity,
        "total_evaluated": len(hospitals),
        "rankings": hospitals[:5],
        "top_recommendation": hospitals[0] if hospitals else None,
    }


def _get_mock_hospitals() -> list:
    """Return mock hospital data for demo."""
    return [
        {
            "id": f"hosp-{i:03d}",
            "name": name,
            "short_name": short,
            "latitude": lat,
            "longitude": lon,
            "address": addr,
            "district": dist,
            "phone": f"080-{random.randint(10000000, 99999999)}",
            "trauma_level": tl,
            "has_trauma_center": tl <= 2,
            "has_icu": True,
            "has_cath_lab": tl == 1,
            "has_neurosurgery": tl <= 2,
            "total_icu_beds": icu_total,
            "available_icu_beds": icu_avail,
            "total_emergency_beds": 50,
            "available_emergency_beds": 20,
            "current_patient_load": random.randint(20, 70),
            "max_patient_load": 100,
            "available_blood_types": ["A+", "B+", "O+", "AB+", "O-"],
            "active_specialists": ["Trauma Surgeon", "Orthopedic", "Neurosurgeon"],
            "suitability_score": 0,
            "load_percentage": random.uniform(30, 80),
            "is_active": True,
            "is_on_alert": random.random() < 0.3,
            "accepts_trauma": True,
        }
        for i, (name, short, lat, lon, addr, dist, tl, icu_total, icu_avail) in enumerate([
            ("Manipal Hospital Whitefield", "Manipal WF", 12.9698, 77.7499, "Whitefield Main Road, Bangalore", "Mahadevapura", 1, 40, 18),
            ("Apollo Hospital Bannerghatta", "Apollo BG", 12.8900, 77.5970, "Bannerghatta Road, Bangalore", "Bommanahalli", 1, 50, 22),
            ("Fortis Hospital Cunningham Road", "Fortis CR", 12.9900, 77.5900, "Cunningham Road, Bangalore", "Shivajinagar", 1, 35, 15),
            ("Victoria Hospital", "Victoria", 12.9716, 77.5946, "Fort Road, Bangalore", "Shivajinagar", 2, 60, 25),
            ("St. John's Medical College Hospital", "St. Johns", 12.9352, 77.6245, "Sarjapur Road, Bangalore", "Bommanahalli", 1, 45, 20),
            ("Narayana Health City", "Narayana HC", 12.8399, 77.6770, "Hosur Road, Bangalore", "Bommanahalli", 1, 80, 35),
            ("Sakra World Hospital", "Sakra", 12.9591, 77.6974, "Marathahalli, Bangalore", "Mahadevapura", 2, 30, 12),
            ("BGS Gleneagles Global Hospital", "BGS Global", 12.9100, 77.4900, "Kengeri, Bangalore", "Rajarajeshwari Nagar", 2, 25, 10),
            ("Aster CMI Hospital", "Aster CMI", 13.0358, 77.5970, "Hebbal, Bangalore", "Yelahanka", 2, 35, 14),
            ("Columbia Asia Hospital Whitefield", "Columbia WF", 12.9698, 77.7499, "Whitefield, Bangalore", "Mahadevapura", 3, 20, 8),
        ])
    ]


def _get_mock_hospital_stats() -> dict:
    return {
        "total_hospitals": 50,
        "active_hospitals": 48,
        "on_alert": random.randint(3, 8),
        "trauma_centers": 12,
        "total_icu_beds": 850,
        "available_icu_beds": random.randint(200, 400),
        "icu_occupancy_percent": round(random.uniform(45, 75), 1),
    }
