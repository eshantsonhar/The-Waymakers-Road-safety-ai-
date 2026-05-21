"""
Hospital Intelligence API endpoints.
Seeded with MockHospital items using IDs h1 through h10 (matching simulator).
"""
import math
import random
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List

from app.engines.hospital_intelligence import hospital_engine
from app.websocket.manager import ws_manager, WSEventType

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals"])

# In-memory hospital store (seeded on import)
_hospitals_store: list = []


def set_hospitals(hospitals: list):
    """Called by seed script to populate hospital data."""
    global _hospitals_store
    _hospitals_store = hospitals


# ── Hospital data (10 Bangalore hospitals, IDs h1–h10) ────────────────────────
_HOSPITAL_DATA = [
    {
        "id": "h1", "name": "Manipal Hospital Whitefield",
        "short_name": "Manipal WF", "latitude": 12.9698, "longitude": 77.7499,
        "address": "Whitefield Main Road, Bangalore", "district": "Mahadevapura",
        "trauma_level": 1, "has_trauma_center": True, "has_cath_lab": True,
        "has_neurosurgery": True, "total_icu_beds": 40, "available_icu_beds": 18,
        "current_patient_load": 55, "max_patient_load": 100,
        "total_emergency_beds": 50, "available_emergency_beds": 20,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+", "O-"],
        "active_specialists": ["Trauma Surgeon", "Orthopedic", "Neurosurgeon"],
    },
    {
        "id": "h2", "name": "Apollo Hospital Bannerghatta",
        "short_name": "Apollo BG", "latitude": 12.8900, "longitude": 77.5970,
        "address": "Bannerghatta Road, Bangalore", "district": "Bommanahalli",
        "trauma_level": 1, "has_trauma_center": True, "has_cath_lab": True,
        "has_neurosurgery": True, "total_icu_beds": 50, "available_icu_beds": 22,
        "current_patient_load": 45, "max_patient_load": 100,
        "total_emergency_beds": 60, "available_emergency_beds": 25,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+", "A-", "B-"],
        "active_specialists": ["Trauma Surgeon", "Cardiologist", "Neurosurgeon"],
    },
    {
        "id": "h3", "name": "Fortis Hospital Cunningham Road",
        "short_name": "Fortis CR", "latitude": 12.9900, "longitude": 77.5900,
        "address": "Cunningham Road, Bangalore", "district": "Shivajinagar",
        "trauma_level": 1, "has_trauma_center": True, "has_cath_lab": True,
        "has_neurosurgery": True, "total_icu_beds": 35, "available_icu_beds": 15,
        "current_patient_load": 60, "max_patient_load": 100,
        "total_emergency_beds": 40, "available_emergency_beds": 12,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+"],
        "active_specialists": ["Trauma Surgeon", "Orthopedic", "Neurosurgeon"],
    },
    {
        "id": "h4", "name": "Victoria Hospital",
        "short_name": "Victoria", "latitude": 12.9716, "longitude": 77.5946,
        "address": "Fort Road, Bangalore", "district": "Shivajinagar",
        "trauma_level": 2, "has_trauma_center": True, "has_cath_lab": False,
        "has_neurosurgery": False, "total_icu_beds": 60, "available_icu_beds": 25,
        "current_patient_load": 65, "max_patient_load": 100,
        "total_emergency_beds": 80, "available_emergency_beds": 30,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"],
        "active_specialists": ["Trauma Surgeon", "Orthopedic"],
    },
    {
        "id": "h5", "name": "St. John's Medical College Hospital",
        "short_name": "St. Johns", "latitude": 12.9352, "longitude": 77.6245,
        "address": "Sarjapur Road, Bangalore", "district": "Bommanahalli",
        "trauma_level": 1, "has_trauma_center": True, "has_cath_lab": True,
        "has_neurosurgery": True, "total_icu_beds": 45, "available_icu_beds": 20,
        "current_patient_load": 50, "max_patient_load": 100,
        "total_emergency_beds": 55, "available_emergency_beds": 22,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+"],
        "active_specialists": ["Trauma Surgeon", "Cardiologist", "Neurosurgeon", "Orthopedic"],
    },
    {
        "id": "h6", "name": "Narayana Health City",
        "short_name": "Narayana HC", "latitude": 12.8399, "longitude": 77.6770,
        "address": "Hosur Road, Bangalore", "district": "Bommanahalli",
        "trauma_level": 1, "has_trauma_center": True, "has_cath_lab": True,
        "has_neurosurgery": True, "total_icu_beds": 80, "available_icu_beds": 35,
        "current_patient_load": 40, "max_patient_load": 100,
        "total_emergency_beds": 100, "available_emergency_beds": 45,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+", "A-", "B-", "O-"],
        "active_specialists": ["Trauma Surgeon", "Cardiologist", "Neurosurgeon", "Orthopedic", "Pulmonologist"],
    },
    {
        "id": "h7", "name": "Sakra World Hospital",
        "short_name": "Sakra", "latitude": 12.9591, "longitude": 77.6974,
        "address": "Marathahalli, Bangalore", "district": "Mahadevapura",
        "trauma_level": 2, "has_trauma_center": True, "has_cath_lab": False,
        "has_neurosurgery": False, "total_icu_beds": 30, "available_icu_beds": 12,
        "current_patient_load": 70, "max_patient_load": 100,
        "total_emergency_beds": 35, "available_emergency_beds": 10,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+"],
        "active_specialists": ["Trauma Surgeon", "Orthopedic"],
    },
    {
        "id": "h8", "name": "BGS Gleneagles Global Hospital",
        "short_name": "BGS Global", "latitude": 12.9100, "longitude": 77.4900,
        "address": "Kengeri, Bangalore", "district": "Rajarajeshwari Nagar",
        "trauma_level": 2, "has_trauma_center": True, "has_cath_lab": True,
        "has_neurosurgery": False, "total_icu_beds": 25, "available_icu_beds": 10,
        "current_patient_load": 75, "max_patient_load": 100,
        "total_emergency_beds": 30, "available_emergency_beds": 8,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+"],
        "active_specialists": ["Trauma Surgeon", "Cardiologist"],
    },
    {
        "id": "h9", "name": "Aster CMI Hospital",
        "short_name": "Aster CMI", "latitude": 13.0358, "longitude": 77.5970,
        "address": "Hebbal, Bangalore", "district": "Yelahanka",
        "trauma_level": 2, "has_trauma_center": True, "has_cath_lab": True,
        "has_neurosurgery": False, "total_icu_beds": 35, "available_icu_beds": 14,
        "current_patient_load": 58, "max_patient_load": 100,
        "total_emergency_beds": 40, "available_emergency_beds": 15,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+", "AB+", "A-"],
        "active_specialists": ["Trauma Surgeon", "Cardiologist", "Orthopedic"],
    },
    {
        "id": "h10", "name": "Columbia Asia Hospital Whitefield",
        "short_name": "Columbia WF", "latitude": 12.9698, "longitude": 77.7499,
        "address": "Whitefield, Bangalore", "district": "Mahadevapura",
        "trauma_level": 3, "has_trauma_center": False, "has_cath_lab": False,
        "has_neurosurgery": False, "total_icu_beds": 20, "available_icu_beds": 8,
        "current_patient_load": 80, "max_patient_load": 100,
        "total_emergency_beds": 25, "available_emergency_beds": 5,
        "is_active": True, "is_on_alert": False,
        "available_blood_types": ["A+", "B+", "O+"],
        "active_specialists": ["Orthopedic"],
    },
]


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
    """Get aggregate hospital statistics computed from actual _hospitals_store state."""
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
        if hasattr(h, 'id') and h.id == hospital_id:
            return h.to_dict()
        if isinstance(h, dict) and h.get("id") == hospital_id:
            return h
    raise HTTPException(status_code=404, detail="Hospital not found")


def _get_mock_rankings(lat: float, lon: float, severity: str) -> dict:
    """Return mock hospital rankings when DB is not available."""
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
    """Return mock hospital data for demo. Uses same data as _HOSPITAL_DATA."""
    random.seed(42)
    hospitals = []
    for data in _HOSPITAL_DATA:
        h = dict(data)
        h["phone"] = f"080-{random.randint(10000000, 99999999)}"
        h["load_percentage"] = round(data["current_patient_load"] / data["max_patient_load"] * 100, 1)
        h["suitability_score"] = 0
        hospitals.append(h)
    return hospitals


def _get_mock_hospital_stats() -> dict:
    """Fallback hospital stats when store is empty."""
    total_icu = sum(h["total_icu_beds"] for h in _HOSPITAL_DATA)
    available_icu = sum(h["available_icu_beds"] for h in _HOSPITAL_DATA)
    trauma_centers = sum(1 for h in _HOSPITAL_DATA if h["has_trauma_center"])
    active = sum(1 for h in _HOSPITAL_DATA if h["is_active"])
    on_alert = sum(1 for h in _HOSPITAL_DATA if h.get("is_on_alert", False))
    return {
        "total_hospitals": len(_HOSPITAL_DATA),
        "active_hospitals": active,
        "on_alert": on_alert,
        "trauma_centers": trauma_centers,
        "total_icu_beds": total_icu,
        "available_icu_beds": available_icu,
        "icu_occupancy_percent": round((1 - available_icu / max(total_icu, 1)) * 100, 1),
    }


class MockHospital:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.name = data["name"]
        self.short_name = data.get("short_name", "")
        self.latitude = data["latitude"]
        self.longitude = data["longitude"]
        self.address = data.get("address", "")
        self.district = data.get("district", "")
        self.phone = data.get("phone", "")
        self.trauma_level = data.get("trauma_level", 4)
        self.has_trauma_center = data.get("has_trauma_center", False)
        self.has_icu = data.get("has_icu", True)
        self.has_cath_lab = data.get("has_cath_lab", False)
        self.has_neurosurgery = data.get("has_neurosurgery", False)
        self.total_icu_beds = data.get("total_icu_beds", 10)
        self.available_icu_beds = data.get("available_icu_beds", 5)
        self.total_emergency_beds = data.get("total_emergency_beds", 20)
        self.available_emergency_beds = data.get("available_emergency_beds", 10)
        self.current_patient_load = data.get("current_patient_load", 50)
        self.max_patient_load = data.get("max_patient_load", 100)
        self.available_blood_types = data.get("available_blood_types", [])
        self.active_specialists = data.get("active_specialists", [])
        self.suitability_score = data.get("suitability_score", 0.0)
        self.load_percentage = data.get("load_percentage", 50.0)
        self.is_active = data.get("is_active", True)
        self.is_on_alert = data.get("is_on_alert", False)
        self.accepts_trauma = data.get("accepts_trauma", True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "district": self.district,
            "phone": self.phone,
            "trauma_level": self.trauma_level,
            "has_trauma_center": self.has_trauma_center,
            "has_icu": self.has_icu,
            "has_cath_lab": self.has_cath_lab,
            "has_neurosurgery": self.has_neurosurgery,
            "total_icu_beds": self.total_icu_beds,
            "available_icu_beds": self.available_icu_beds,
            "total_emergency_beds": self.total_emergency_beds,
            "available_emergency_beds": self.available_emergency_beds,
            "current_patient_load": self.current_patient_load,
            "max_patient_load": self.max_patient_load,
            "available_blood_types": self.available_blood_types,
            "active_specialists": self.active_specialists,
            "suitability_score": self.suitability_score,
            "load_percentage": self.load_percentage,
            "is_active": self.is_active,
            "is_on_alert": self.is_on_alert,
            "accepts_trauma": self.accepts_trauma,
        }


# Seed _hospitals_store on module import
_hospitals_store.extend([MockHospital(h) for h in _HOSPITAL_DATA])