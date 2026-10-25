from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import check_mongo, check_postgres
from app.schemas.health import HealthResponse, ServiceConnectivity

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Checks PostgreSQL and MongoDB connectivity and returns system health status."""
    pg_res = await check_postgres()
    mongo_res = await check_mongo()

    is_healthy = pg_res["status"] == "connected" and mongo_res["status"] == "connected"
    overall_status = "ok" if is_healthy else "degraded"

    payload = HealthResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        postgres=ServiceConnectivity(**pg_res),
        mongodb=ServiceConnectivity(**mongo_res),
    )

    http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content=payload.model_dump(),
    )
