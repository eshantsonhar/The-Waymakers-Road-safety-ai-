from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "RoadSoS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DEMO_MODE: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://roadsos:roadsos_secret@localhost:5432/roadsos_db"
    DATABASE_URL_SYNC: str = "postgresql://roadsos:roadsos_secret@localhost:5432/roadsos_db"

    # Security
    SECRET_KEY: str = "roadsos-dev-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:80",
        "http://127.0.0.1:80",
    ]

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    # Demo Mode Settings
    DEMO_CRASH_INTERVAL_SECONDS: int = 45
    DEMO_AMBULANCE_UPDATE_INTERVAL_SECONDS: int = 5
    DEMO_HOSPITAL_UPDATE_INTERVAL_SECONDS: int = 30

    # Bangalore center coordinates
    BANGALORE_LAT: float = 12.9716
    BANGALORE_LON: float = 77.5946
    BANGALORE_RADIUS_KM: float = 25.0

    # Detection thresholds
    CRASH_CONFIRM_THRESHOLD: float = 0.75
    CRASH_SUSPECT_THRESHOLD: float = 0.40
    SOUND_INTENSITY_THRESHOLD_DB: float = 85.0
    SOUND_SCORE_BOOST: float = 0.15

    # Emergency coordination
    MAX_AMBULANCE_SEARCH_RADIUS_KM: float = 20.0
    MAX_HOSPITALS_TO_RANK: int = 5
    NOTIFICATION_TIMEOUT_SECONDS: int = 5

    # Risk prediction
    BLACKSPOT_RISK_THRESHOLD: float = 70.0

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
