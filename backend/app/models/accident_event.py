from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid
from app.database import Base


class AccidentEvent(Base):
    __tablename__ = "accident_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=True)

    # Location
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    road_segment_id = Column(String(36), ForeignKey("road_segments.id"), nullable=True)
    district = Column(String(100))

    # Event details
    event_type = Column(String(50))  # crash, near_miss, pothole_hit, etc.
    severity = Column(String(20))
    vehicle_type = Column(String(50))
    vehicles_involved = Column(Integer, default=1)
    casualties = Column(Integer, default=0)
    fatalities = Column(Integer, default=0)

    # Sensor data at time of event
    sensor_snapshot = Column(JSON)
    crash_probability_score = Column(Float)
    impact_force_g = Column(Float)
    speed_at_impact_kmh = Column(Float)

    # Environmental conditions at time of event
    weather_condition = Column(String(50))
    visibility_meters = Column(Float)
    road_condition = Column(String(50))
    time_of_day = Column(String(20))  # morning, afternoon, evening, night

    # Flags
    is_historical = Column(Boolean, default=False)
    is_demo = Column(Boolean, default=False)

    # Timestamps
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    incident = relationship("Incident", back_populates="accident_events")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district": self.district,
            "event_type": self.event_type,
            "severity": self.severity,
            "vehicle_type": self.vehicle_type,
            "vehicles_involved": self.vehicles_involved,
            "casualties": self.casualties,
            "fatalities": self.fatalities,
            "crash_probability_score": self.crash_probability_score,
            "impact_force_g": self.impact_force_g,
            "speed_at_impact_kmh": self.speed_at_impact_kmh,
            "weather_condition": self.weather_condition,
            "road_condition": self.road_condition,
            "time_of_day": self.time_of_day,
            "is_historical": self.is_historical,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
