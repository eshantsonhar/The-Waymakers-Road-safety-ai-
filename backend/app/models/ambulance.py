from sqlalchemy import Column, String, Float, Boolean, DateTime, Enum, Integer, JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import enum
import uuid
from app.database import Base


class AmbulanceStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE_TO_SCENE = "EN_ROUTE_TO_SCENE"
    ON_SCENE = "ON_SCENE"
    TRANSPORTING = "TRANSPORTING"
    AT_HOSPITAL = "AT_HOSPITAL"
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


class AmbulanceType(str, enum.Enum):
    BLS = "BLS"       # Basic Life Support
    ALS = "ALS"       # Advanced Life Support
    MICU = "MICU"     # Mobile ICU
    NEONATAL = "NEONATAL"


class Ambulance(Base):
    __tablename__ = "ambulances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_number = Column(String(20), unique=True, nullable=False)
    call_sign = Column(String(20))
    ambulance_type = Column(Enum(AmbulanceType), default=AmbulanceType.BLS)

    # Location
    location = Column(Geometry("POINT", srid=4326))
    latitude = Column(Float)
    longitude = Column(Float)
    heading = Column(Float, default=0.0)  # degrees
    speed_kmh = Column(Float, default=0.0)

    # Status
    status = Column(Enum(AmbulanceStatus), default=AmbulanceStatus.AVAILABLE)
    is_active = Column(Boolean, default=True)

    # Assignment
    current_incident_id = Column(String(36), nullable=True)
    assigned_hospital_id = Column(String(36), nullable=True)

    # Crew
    crew_count = Column(Integer, default=2)
    has_paramedic = Column(Boolean, default=True)
    has_doctor = Column(Boolean, default=False)

    # Equipment
    equipment = Column(JSON, default=list)

    # Base station
    base_station_name = Column(String(100))
    base_latitude = Column(Float)
    base_longitude = Column(Float)

    # ETAs
    eta_to_scene_minutes = Column(Float)
    eta_to_hospital_minutes = Column(Float)

    # Route (list of [lat, lon] waypoints)
    current_route = Column(JSON, default=list)
    route_progress = Column(Float, default=0.0)  # 0.0 to 1.0

    # Timestamps
    last_location_update = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "vehicle_number": self.vehicle_number,
            "call_sign": self.call_sign,
            "ambulance_type": self.ambulance_type.value if self.ambulance_type else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "heading": self.heading,
            "speed_kmh": self.speed_kmh,
            "status": self.status.value if self.status else None,
            "is_active": self.is_active,
            "current_incident_id": self.current_incident_id,
            "assigned_hospital_id": self.assigned_hospital_id,
            "crew_count": self.crew_count,
            "has_paramedic": self.has_paramedic,
            "has_doctor": self.has_doctor,
            "base_station_name": self.base_station_name,
            "eta_to_scene_minutes": self.eta_to_scene_minutes,
            "eta_to_hospital_minutes": self.eta_to_hospital_minutes,
            "current_route": self.current_route or [],
            "route_progress": self.route_progress,
            "last_location_update": self.last_location_update.isoformat() if self.last_location_update else None,
        }
