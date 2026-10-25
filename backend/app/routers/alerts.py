"""
Fixora Alerts Router
Endpoints:
- GET /api/alerts: Role-scoped alerts list
- POST /api/alerts/{id}/ack: Acknowledge an alert
- GET /api/alerts/stream: Real-time Server-Sent Events (SSE) stream
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.entities import User
from app.models.enums import RoleEnum
from app.services.alert_service import AlertService

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
async def list_alerts(
    application_id: Optional[str] = Query(None),
    unacknowledged_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List alerts with strict role scoping:
    Institution users only see institution-safe alerts for their own application.
    Officer-only alerts (anomalies, source outages) are hidden from institutions.
    """
    return await AlertService.get_alerts_for_user(
        db=db,
        user=current_user,
        application_id=application_id,
        unacknowledged_only=unacknowledged_only,
        page=page,
        page_size=page_size,
    )


@router.post("/alerts/{id}/ack")
async def acknowledge_alert(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Acknowledge an alert, recording the user and timestamp.
    """
    try:
        res = await AlertService.acknowledge_alert(
            db=db,
            alert_id=id,
            user_id=current_user.id,
        )
        return {"data": res}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/alerts/stream")
async def stream_alerts(
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time statutory alert notifications.
    """
    return StreamingResponse(
        AlertService.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
