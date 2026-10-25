import time
from typing import Any, Dict, Optional
import asyncio

try:
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy import text
    HAS_SQLALCHEMY = True
except ImportError:
    AsyncEngine = Any
    AsyncSession = Any
    async_sessionmaker = Any
    create_async_engine = None
    text = None
    HAS_SQLALCHEMY = False

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    HAS_MOTOR = True
except ImportError:
    AsyncIOMotorClient = Any
    HAS_MOTOR = False

from app.core.config import settings
from app.core.logging import logger

# Async PostgreSQL Engine & Session Maker
async_engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[Any] = None

# MongoDB Client
mongo_client: Optional[AsyncIOMotorClient] = None


def get_async_engine() -> AsyncEngine:
    global async_engine, AsyncSessionLocal
    if async_engine is None:
        async_engine = create_async_engine(
            settings.async_postgres_uri,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_engine


async def get_db():
    """FastAPI dependency that yields an asynchronous database session."""
    engine = get_async_engine()
    async_session = AsyncSessionLocal
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def get_mongo_client() -> AsyncIOMotorClient:
    global mongo_client
    if mongo_client is None:
        mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
    return mongo_client


def get_mongo_db():
    client = get_mongo_client()
    return client[settings.MONGODB_DB_NAME]


async def check_postgres() -> Dict[str, Any]:
    """Checks PostgreSQL connectivity and measures latency."""
    start_time = time.perf_counter()
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=3.0)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "connected",
            "latency_ms": latency,
            "details": "PostgreSQL 16 connection operational",
        }
    except Exception as exc:
        logger.warning("PostgreSQL health check failed", extra={"error": str(exc)})
        return {
            "status": "unavailable",
            "details": str(exc),
            "latency_ms": None,
        }


async def check_mongo() -> Dict[str, Any]:
    """Checks MongoDB connectivity and measures latency."""
    start_time = time.perf_counter()
    try:
        client = get_mongo_client()
        await asyncio.wait_for(client.admin.command("ping"), timeout=3.0)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "connected",
            "latency_ms": latency,
            "details": "MongoDB 7 connection operational",
        }
    except Exception as exc:
        logger.warning("MongoDB health check failed", extra={"error": str(exc)})
        return {
            "status": "unavailable",
            "details": str(exc),
            "latency_ms": None,
        }


async def close_connections() -> None:
    """Closes all database connections cleanly."""
    global async_engine, mongo_client
    if async_engine is not None:
        await async_engine.dispose()
        async_engine = None
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
