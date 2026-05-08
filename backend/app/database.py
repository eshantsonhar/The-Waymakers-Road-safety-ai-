from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Sync engine for migrations/seeding
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    from sqlalchemy import text as sa_text
    # Import models to register them with Base.metadata
    from app.models import (  # noqa: F401
        Incident, Hospital, Ambulance, User, EmergencyContact,
        RoadSegment, RiskZone, AccidentEvent
    )
    async with async_engine.begin() as conn:
        # Enable PostGIS
        try:
            await conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS postgis_topology"))
        except Exception as e:
            logger.warning(f"PostGIS extension setup: {e}")
        await Base.metadata.create_all(conn)
    logger.info("Database initialized successfully")
