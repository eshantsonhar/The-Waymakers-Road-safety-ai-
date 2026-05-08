from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Integer
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid
from app.database import Base


class RiskZone(Base):
    __tablename__ = "risk_zones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200))
    zone_type = Column(String(50))  # blackspot, high_risk, moderate_risk
    district = Column(String(100))

    # Geometry (polygon or point)
    geometry = Column(Geometry("POLYGON", srid=4326))
    center_latitude = Column(Float)
    center_longitude = Column(Float)
    radius_meters = Column(Float, default=500.0)

    # Risk data
    risk_score = Column(Float, default=0.0)
    prediction_confidence = Column(Float, default=0.5)
    accident_count_last_year = Column(Integer, default=0)
    fatal_count_last_year = Column(Integer, default=0)

    # Contributing factors
    primary_factor = Column(String(100))
    contributing_factors = Column(JSON, default=list)

    # Trend
    trend_direction = Column(String(20), default="stable")  # improving, stable, worsening

    # Status
    is_active = Column(Boolean, default=True)
    requires_intervention = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "zone_type": self.zone_type,
            "district": self.district,
            "center_latitude": self.center_latitude,
            "center_longitude": self.center_longitude,
            "radius_meters": self.radius_meters,
            "risk_score": self.risk_score,
            "prediction_confidence": self.prediction_confidence,
            "accident_count_last_year": self.accident_count_last_year,
            "fatal_count_last_year": self.fatal_count_last_year,
            "primary_factor": self.primary_factor,
            "contributing_factors": self.contributing_factors or [],
            "trend_direction": self.trend_direction,
            "is_active": self.is_active,
            "requires_intervention": self.requires_intervention,
        }
