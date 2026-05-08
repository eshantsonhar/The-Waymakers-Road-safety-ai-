from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, Enum
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import enum
import uuid
from app.database import Base


class TraumaLevel(int, enum.Enum):
    LEVEL_1 = 1  # Highest - comprehensive trauma center
    LEVEL_2 = 2  # Major trauma center
    LEVEL_3 = 3  # Trauma ready
    LEVEL_4 = 4  # Basic emergency


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    short_name = Column(String(50))

    # Location
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500))
    district = Column(String(100))
    phone = Column(String(20))

    # Capability
    trauma_level = Column(Integer, default=3)
    has_trauma_center = Column(Boolean, default=False)
    has_icu = Column(Boolean, default=True)
    has_cath_lab = Column(Boolean, default=False)
    has_neurosurgery = Column(Boolean, default=False)
    has_burn_unit = Column(Boolean, default=False)
    has_pediatric_emergency = Column(Boolean, default=False)

    # Capacity
    total_icu_beds = Column(Integer, default=20)
    available_icu_beds = Column(Integer, default=10)
    total_emergency_beds = Column(Integer, default=50)
    available_emergency_beds = Column(Integer, default=25)
    current_patient_load = Column(Integer, default=0)
    max_patient_load = Column(Integer, default=100)

    # Blood availability (JSON list of blood types)
    available_blood_types = Column(JSON, default=list)

    # Active specialists (JSON list)
    active_specialists = Column(JSON, default=list)

    # Computed scores
    suitability_score = Column(Float, default=50.0)
    load_percentage = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)
    is_on_alert = Column(Boolean, default=False)
    accepts_trauma = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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
            "available_blood_types": self.available_blood_types or [],
            "active_specialists": self.active_specialists or [],
            "suitability_score": self.suitability_score,
            "load_percentage": self.load_percentage,
            "is_active": self.is_active,
            "is_on_alert": self.is_on_alert,
            "accepts_trauma": self.accepts_trauma,
        }
