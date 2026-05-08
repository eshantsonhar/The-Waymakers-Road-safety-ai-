from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import uuid
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    phone = Column(String(20), unique=True)
    email = Column(String(200), unique=True)
    device_id = Column(String(100), unique=True)

    # Location
    last_known_latitude = Column(Float)
    last_known_longitude = Column(Float)
    last_location = Column(Geometry("POINT", srid=4326))

    # Medical info
    blood_type = Column(String(5))
    medical_conditions = Column(String(500))
    allergies = Column(String(500))

    # Status
    is_active = Column(Boolean, default=True)
    is_demo = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    emergency_contacts = relationship("EmergencyContact", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "device_id": self.device_id,
            "last_known_latitude": self.last_known_latitude,
            "last_known_longitude": self.last_known_longitude,
            "blood_type": self.blood_type,
            "medical_conditions": self.medical_conditions,
            "is_active": self.is_active,
        }


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    relationship = Column(String(50))
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="emergency_contacts")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "phone": self.phone,
            "relationship": self.relationship,
            "priority": self.priority,
        }
