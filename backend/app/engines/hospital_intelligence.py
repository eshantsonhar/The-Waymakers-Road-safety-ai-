"""
Hospital Intelligence Engine
Ranks hospitals based on multiple weighted factors for optimal patient routing.
"""
import math
from typing import List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HospitalRanking:
    hospital_id: str
    hospital_name: str
    latitude: float
    longitude: float
    suitability_score: float
    distance_km: float
    estimated_travel_minutes: float
    recommendation_explanation: str
    score_breakdown: dict
    rank: int


class HospitalIntelligenceEngine:
    """
    Ranks hospitals using a weighted multi-factor scoring algorithm.
    
    Weight distribution:
    - Trauma capability: 25%
    - ICU availability: 20%
    - Travel time (with traffic): 20%
    - Distance: 15%
    - Hospital load: 10%
    - Blood availability: 5%
    - Specialist availability: 5%
    """

    WEIGHTS = {
        "trauma_capability": 0.25,
        "icu_availability": 0.20,
        "travel_time": 0.20,
        "distance": 0.15,
        "hospital_load": 0.10,
        "blood_availability": 0.05,
        "specialist_availability": 0.05,
    }

    # ICU penalty threshold
    ICU_PENALTY_THRESHOLD = 0.90  # 90% occupancy
    ICU_PENALTY_POINTS = 20.0

    # Max distance for scoring (beyond this = 0 score)
    MAX_DISTANCE_KM = 30.0
    MAX_TRAVEL_MINUTES = 60.0

    def rank_hospitals(
        self,
        hospitals: list,
        incident_lat: float,
        incident_lon: float,
        severity: str,
        required_blood_type: Optional[str] = None,
        traffic_factor: float = 1.0,
    ) -> List[HospitalRanking]:
        """
        Rank hospitals for a given incident.
        Returns sorted list with highest suitability first.
        """
        rankings = []

        for hospital in hospitals:
            # Skip hospitals without trauma capability for CRITICAL incidents
            if severity == "CRITICAL" and not hospital.has_trauma_center:
                continue

            # Skip inactive hospitals
            if not hospital.is_active:
                continue

            distance_km = self._haversine_distance(
                incident_lat, incident_lon,
                hospital.latitude, hospital.longitude
            )

            # Skip hospitals beyond max distance
            if distance_km > self.MAX_DISTANCE_KM:
                continue

            # Compute travel time (accounting for traffic)
            travel_minutes = self._estimate_travel_time(distance_km, traffic_factor)

            # Compute individual scores
            scores = self._compute_scores(
                hospital, distance_km, travel_minutes, required_blood_type
            )

            # Compute weighted total
            raw_score = sum(
                scores[factor] * weight
                for factor, weight in self.WEIGHTS.items()
            )

            # Convert to 0-100 scale
            suitability_score = raw_score * 100.0

            # Apply ICU penalty
            icu_occupancy = 1.0 - (hospital.available_icu_beds / max(hospital.total_icu_beds, 1))
            if icu_occupancy >= self.ICU_PENALTY_THRESHOLD:
                suitability_score = max(0.0, suitability_score - self.ICU_PENALTY_POINTS)

            # Generate explanation
            explanation = self._generate_explanation(
                hospital, distance_km, travel_minutes, scores, suitability_score
            )

            rankings.append(HospitalRanking(
                hospital_id=hospital.id,
                hospital_name=hospital.name,
                latitude=hospital.latitude,
                longitude=hospital.longitude,
                suitability_score=round(suitability_score, 1),
                distance_km=round(distance_km, 2),
                estimated_travel_minutes=round(travel_minutes, 1),
                recommendation_explanation=explanation,
                score_breakdown={k: round(v * 100, 1) for k, v in scores.items()},
                rank=0,  # set after sorting
            ))

        # Sort by suitability score descending
        rankings.sort(key=lambda x: x.suitability_score, reverse=True)

        # Assign ranks
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1

        return rankings

    def _compute_scores(
        self,
        hospital,
        distance_km: float,
        travel_minutes: float,
        required_blood_type: Optional[str],
    ) -> dict:
        """Compute normalized scores (0.0-1.0) for each factor."""
        scores = {}

        # Trauma capability (0-1 based on trauma level)
        trauma_level = getattr(hospital, 'trauma_level', 4)
        scores["trauma_capability"] = max(0.0, (5 - trauma_level) / 4.0)
        if hospital.has_trauma_center:
            scores["trauma_capability"] = min(1.0, scores["trauma_capability"] + 0.2)

        # ICU availability
        total_icu = max(hospital.total_icu_beds, 1)
        available_icu = max(hospital.available_icu_beds, 0)
        scores["icu_availability"] = available_icu / total_icu

        # Travel time (inverse - closer is better)
        scores["travel_time"] = max(0.0, 1.0 - (travel_minutes / self.MAX_TRAVEL_MINUTES))

        # Distance (inverse)
        scores["distance"] = max(0.0, 1.0 - (distance_km / self.MAX_DISTANCE_KM))

        # Hospital load (inverse)
        max_load = max(hospital.max_patient_load, 1)
        current_load = min(hospital.current_patient_load, max_load)
        scores["hospital_load"] = 1.0 - (current_load / max_load)

        # Blood availability
        if required_blood_type:
            available_types = hospital.available_blood_types or []
            scores["blood_availability"] = 1.0 if required_blood_type in available_types else 0.0
        else:
            # Score based on variety of blood types available
            available_types = hospital.available_blood_types or []
            scores["blood_availability"] = min(1.0, len(available_types) / 8.0)

        # Specialist availability
        specialists = hospital.active_specialists or []
        scores["specialist_availability"] = min(1.0, len(specialists) / 5.0)

        return scores

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in km."""
        R = 6371.0  # Earth radius in km
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _estimate_travel_time(self, distance_km: float, traffic_factor: float = 1.0) -> float:
        """
        Estimate travel time in minutes.
        Assumes average ambulance speed of 60 km/h in city, adjusted for traffic.
        """
        base_speed_kmh = 60.0
        effective_speed = base_speed_kmh / max(traffic_factor, 0.1)
        return (distance_km / effective_speed) * 60.0

    def _generate_explanation(
        self,
        hospital,
        distance_km: float,
        travel_minutes: float,
        scores: dict,
        final_score: float,
    ) -> str:
        """Generate human-readable recommendation explanation."""
        reasons = []

        if scores["trauma_capability"] > 0.7:
            reasons.append(f"Level {hospital.trauma_level} trauma center with full emergency capability")
        if scores["icu_availability"] > 0.6:
            reasons.append(f"{hospital.available_icu_beds} ICU beds available")
        if distance_km < 5.0:
            reasons.append(f"Closest facility at {distance_km:.1f} km")
        elif travel_minutes < 10:
            reasons.append(f"Fast access — estimated {travel_minutes:.0f} min travel time")
        if hospital.has_neurosurgery:
            reasons.append("Neurosurgery unit available")
        if hospital.has_cath_lab:
            reasons.append("Cardiac catheterization lab on standby")
        if scores["hospital_load"] > 0.7:
            reasons.append("Low current patient load")

        if not reasons:
            reasons.append(f"Nearest available facility at {distance_km:.1f} km")

        return f"Recommended: {hospital.name} — " + "; ".join(reasons[:3]) + f" (Score: {final_score:.0f}/100)"


# Singleton instance
hospital_engine = HospitalIntelligenceEngine()
