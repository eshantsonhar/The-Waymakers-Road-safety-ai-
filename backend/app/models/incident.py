from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey, Text, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import enum
import uuid
from app.database import Base


class SeverityLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    CONFIRMED = "CONFIRMED"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    TRANSPORTING = "TRANSPORTING"
    RESOLVED = "RESOLVED"
    FALSE_ALARM = "FALSE_ALARM"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_number = Column(String(20), unique=True, nullable=False)

    # Location
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    address = Column(String(500))
    district = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Classification
    severity = Column(Enum(SeverityLevel), nullable=False, default=SeverityLevel.MEDIUM)
    status = Column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.DETECTED)

    # Detection data
    crash_probability_score = Column(Float, default=0.0)
    confidence_level = Column(String(10), default="LOW")
    event_classification = Column(String(50))
    detection_source = Column(String(50), default="SENSOR")

    # Sensor data snapshot
    sensor_data = Column(JSON)

    # Assignments
    assigned_ambulance_id = Column(String(36), ForeignKey("ambulances.id"), nullable=True)
    assigned_hospital_id = Column(String(36), ForeignKey("hospitals.id"), nullable=True)

    # User/device
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    device_id = Column(String(100))

    # Timeline (JSON object with timestamps)
    timeline = Column(JSON, default=dict)

    # ETAs
    ambulance_eta_minutes = Column(Float)
    hospital_eta_minutes = Column(Float)

    # Flags
    is_demo = Column(Boolean, default=False)
    offline_mode = Column(Boolean, default=False)
    notifications_sent = Column(Boolean, default=False)

    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    assigned_ambulance = relationship("Ambulance", foreign_keys=[assigned_ambulance_id])
    assigned_hospital = relationship("Hospital", foreign_keys=[assigned_hospital_id])
    user = relationship("User", foreign_keys=[user_id])
    accident_events = relationship("AccidentEvent", back_populates="incident")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_number": self.incident_number,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "district": self.district,
            "severity": self.severity.value if self.severity else None,
            "status": self.status.value if self.status else None,
            "crash_probability_score": self.crash_probability_score,
            "confidence_level": self.confidence_level,
            "event_classification": self.event_classification,
            "assigned_ambulance_id": self.assigned_ambulance_id,
            "assigned_hospital_id": self.assigned_hospital_id,
            "ambulance_eta_minutes": self.ambulance_eta_minutes,
            "hospital_eta_minutes": self.hospital_eta_minutes,
            "timeline": self.timeline or {},
            "is_demo": self.is_demo,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
