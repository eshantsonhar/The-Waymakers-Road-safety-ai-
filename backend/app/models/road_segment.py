from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid
from app.database import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200))
    road_type = Column(String(50))  # highway, arterial, collector, local
    district = Column(String(100))

    # Geometry
    geometry = Column(Geometry("LINESTRING", srid=4326))
    start_latitude = Column(Float)
    start_longitude = Column(Float)
    end_latitude = Column(Float)
    end_longitude = Column(Float)
    length_km = Column(Float)

    # Road characteristics
    speed_limit_kmh = Column(Integer, default=60)
    lanes = Column(Integer, default=2)
    has_median = Column(Boolean, default=False)
    has_footpath = Column(Boolean, default=False)
    has_streetlight = Column(Boolean, default=True)
    surface_condition = Column(Float, default=0.7)  # 0.0 (terrible) to 1.0 (perfect)
    curvature_index = Column(Float, default=0.1)    # 0.0 (straight) to 1.0 (very curved)
    pothole_density = Column(Float, default=0.1)    # potholes per km

    # Environmental factors
    flood_prone = Column(Boolean, default=False)
    fog_prone = Column(Boolean, default=False)

    # Risk data
    risk_score = Column(Float, default=0.0)
    accident_frequency_per_year = Column(Float, default=0.0)
    is_blackspot = Column(Boolean, default=False)
    prediction_confidence = Column(Float, default=0.5)

    # Historical stats
    total_accidents = Column(Integer, default=0)
    fatal_accidents = Column(Integer, default=0)
    last_accident_date = Column(DateTime(timezone=True), nullable=True)

    # Contributing factors (JSON)
    risk_factors = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "road_type": self.road_type,
            "district": self.district,
            "start_latitude": self.start_latitude,
            "start_longitude": self.start_longitude,
            "end_latitude": self.end_latitude,
            "end_longitude": self.end_longitude,
            "length_km": self.length_km,
            "speed_limit_kmh": self.speed_limit_kmh,
            "surface_condition": self.surface_condition,
            "curvature_index": self.curvature_index,
            "pothole_density": self.pothole_density,
            "risk_score": self.risk_score,
            "accident_frequency_per_year": self.accident_frequency_per_year,
            "is_blackspot": self.is_blackspot,
            "prediction_confidence": self.prediction_confidence,
            "total_accidents": self.total_accidents,
            "fatal_accidents": self.fatal_accidents,
            "risk_factors": self.risk_factors or {},
        }
