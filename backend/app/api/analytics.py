"""
Admin Analytics API endpoints.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _generate_trend_data(days: int = 30) -> list:
    """Generate mock accident trend data."""
    data = []
    base_date = datetime.utcnow() - timedelta(days=days)
    base_count = 8

    for i in range(days):
        date = base_date + timedelta(days=i)
        # Simulate weekly patterns (more accidents on weekends)
        day_of_week = date.weekday()
        weekend_factor = 1.3 if day_of_week >= 5 else 1.0
        # Simulate rain effect
        rain_factor = 1.4 if random.random() < 0.2 else 1.0

        count = int(base_count * weekend_factor * rain_factor * random.uniform(0.7, 1.3))
        fatal = int(count * random.uniform(0.05, 0.15))
        severe = int(count * random.uniform(0.2, 0.35))

        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "total_incidents": count,
            "fatal": fatal,
            "severe": severe,
            "moderate": count - fatal - severe - max(0, count - fatal - severe - int(count * 0.4)),
            "minor": max(0, count - fatal - severe - int(count * 0.4)),
            "avg_response_time_minutes": round(random.uniform(6, 14), 1),
        })

    return data


def _generate_hourly_distribution() -> list:
    """Generate accident distribution by hour of day."""
    # Peak hours: 8-10am, 5-8pm; low: 2-5am
    hourly_weights = [
        0.3, 0.2, 0.15, 0.1, 0.1, 0.2,   # 0-5am
        0.5, 0.8, 1.2, 1.0, 0.8, 0.9,    # 6-11am
        1.0, 0.9, 0.8, 0.9, 1.1, 1.4,    # 12-5pm
        1.5, 1.3, 1.0, 0.8, 0.6, 0.4,    # 6-11pm
    ]
    return [
        {"hour": h, "count": int(w * random.uniform(8, 15)), "label": f"{h:02d}:00"}
        for h, w in enumerate(hourly_weights)
    ]


@router.get("/trends")
async def get_accident_trends(
    days: int = Query(30, ge=7, le=365),
    district: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
):
    """Get accident trend data for charts."""
    data = _generate_trend_data(days)

    total = sum(d["total_incidents"] for d in data)
    fatal = sum(d["fatal"] for d in data)
    avg_response = round(sum(d["avg_response_time_minutes"] for d in data) / len(data), 1)

    return {
        "period_days": days,
        "district_filter": district,
        "severity_filter": severity,
        "summary": {
            "total_incidents": total,
            "total_fatal": fatal,
            "fatality_rate_percent": round(fatal / max(total, 1) * 100, 1),
            "avg_response_time_minutes": avg_response,
            "incidents_under_10min_percent": round(random.uniform(65, 80), 1),
        },
        "daily_data": data,
        "hourly_distribution": _generate_hourly_distribution(),
    }


@router.get("/response-efficiency")
async def get_response_efficiency():
    """Get emergency response efficiency metrics."""
    return {
        "avg_detection_to_dispatch_seconds": round(random.uniform(8, 15), 1),
        "avg_dispatch_to_arrival_minutes": round(random.uniform(7, 12), 1),
        "avg_total_response_minutes": round(random.uniform(9, 16), 1),
        "incidents_under_10min_percent": round(random.uniform(62, 78), 1),
        "incidents_under_15min_percent": round(random.uniform(80, 92), 1),
        "false_positive_rate_percent": round(random.uniform(3, 8), 1),
        "ambulance_utilization_percent": round(random.uniform(45, 70), 1),
        "hospital_diversion_rate_percent": round(random.uniform(5, 15), 1),
        "monthly_trend": [
            {
                "month": (datetime.utcnow() - timedelta(days=30 * i)).strftime("%b %Y"),
                "avg_response_minutes": round(random.uniform(8, 14), 1),
                "incidents": random.randint(180, 280),
            }
            for i in range(6, 0, -1)
        ],
    }


@router.get("/district-stats")
async def get_district_stats():
    """Get district-wise accident statistics."""
    districts = [
        "Bommanahalli", "Mahadevapura", "Yelahanka", "Dasarahalli",
        "Shivajinagar", "Rajarajeshwari Nagar", "Bangalore East",
        "Bangalore North", "Bangalore South", "Bangalore West",
    ]

    stats = []
    for district in districts:
        total = random.randint(50, 200)
        fatal = random.randint(2, 20)
        stats.append({
            "district": district,
            "total_incidents": total,
            "fatal_incidents": fatal,
            "severe_incidents": random.randint(10, 50),
            "avg_severity_score": round(random.uniform(2.0, 3.5), 1),
            "top_blackspot": f"{district} Main Road",
            "avg_response_time_minutes": round(random.uniform(7, 14), 1),
            "blackspot_count": random.randint(2, 8),
            "trend": random.choice(["improving", "stable", "worsening"]),
            "fatality_rate_percent": round(fatal / total * 100, 1),
        })

    stats.sort(key=lambda x: x["total_incidents"], reverse=True)
    return {"districts": stats, "total_districts": len(stats)}


@router.get("/prediction-metrics")
async def get_prediction_metrics():
    """Get ML model performance metrics."""
    from app.engines.risk_prediction import risk_engine

    if risk_engine.model_metrics:
        metrics = risk_engine.model_metrics
    else:
        # Simulated metrics
        metrics = {
            "accuracy": 0.847,
            "precision": 0.812,
            "recall": 0.789,
            "f1_score": 0.800,
            "training_samples": 1200,
            "test_samples": 300,
        }

    return {
        "model_type": "Random Forest Classifier",
        "features": [
            "accident_frequency", "surface_condition", "rainfall_intensity",
            "lighting_level", "traffic_density", "curvature_index", "pothole_density"
        ],
        "metrics": metrics,
        "last_trained": datetime.utcnow().isoformat(),
        "prediction_horizon_hours": 24,
        "blackspot_threshold": 70.0,
        "confidence_distribution": {
            "high": round(random.uniform(0.4, 0.6), 2),
            "medium": round(random.uniform(0.25, 0.35), 2),
            "low": round(random.uniform(0.1, 0.2), 2),
        },
    }


@router.get("/infrastructure-insights")
async def get_infrastructure_insights():
    """Get road infrastructure insights and maintenance priorities."""
    from app.api.risk import _road_segments_cache

    high_risk = [s for s in _road_segments_cache if s["risk_score"] >= 70]
    high_risk.sort(key=lambda x: x["risk_score"], reverse=True)

    insights = []
    for seg in high_risk[:15]:
        insights.append({
            "segment_id": seg["id"],
            "name": seg["name"],
            "district": seg["district"],
            "risk_score": seg["risk_score"],
            "primary_issue": _get_primary_issue(seg["risk_factors"]),
            "recommended_action": _get_recommended_action(seg["risk_factors"]),
            "estimated_cost_lakhs": round(random.uniform(5, 50), 1),
            "priority": "CRITICAL" if seg["risk_score"] >= 85 else "HIGH",
            "trend": seg.get("trend_direction", "stable"),
        })

    return {
        "total_segments_requiring_attention": len(high_risk),
        "critical_priority": sum(1 for s in high_risk if s["risk_score"] >= 85),
        "high_priority": sum(1 for s in high_risk if 70 <= s["risk_score"] < 85),
        "estimated_total_cost_crores": round(sum(i["estimated_cost_lakhs"] for i in insights) / 100, 2),
        "insights": insights,
    }


def _get_primary_issue(risk_factors: dict) -> str:
    if not risk_factors:
        return "General road safety"
    top = max(risk_factors, key=lambda k: risk_factors.get(k, 0))
    issues = {
        "accident_frequency": "High historical accident rate",
        "surface_condition": "Deteriorated road surface",
        "curvature": "Dangerous road geometry",
        "pothole_density": "Severe pothole damage",
        "rainfall": "Flood/drainage issues",
        "lighting": "Inadequate street lighting",
        "traffic_density": "Traffic management needed",
    }
    return issues.get(top, "Road safety improvement needed")


def _get_recommended_action(risk_factors: dict) -> str:
    if not risk_factors:
        return "Conduct road safety audit"
    top = max(risk_factors, key=lambda k: risk_factors.get(k, 0))
    actions = {
        "accident_frequency": "Install speed cameras and warning signs",
        "surface_condition": "Road resurfacing and repair",
        "curvature": "Install guardrails and chevron signs",
        "pothole_density": "Emergency pothole patching",
        "rainfall": "Improve drainage infrastructure",
        "lighting": "Install LED street lights",
        "traffic_density": "Signal optimization and lane marking",
    }
    return actions.get(top, "Comprehensive road safety intervention")
