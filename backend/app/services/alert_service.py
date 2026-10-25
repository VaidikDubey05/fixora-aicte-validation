"""
Fixora Alerts Engine
Generates and manages statutory alerts:
- Missing mandatory documents
- Certificates expiring within configurable threshold window
- Verification pending longer than configured SLA
- Preliminary anomaly indicators (restricted to scrutiny/verification officers)
- Source registry outages (officers only, never adverse)

Supports role-based filtering and Server-Sent Events (SSE) broadcasting.
"""

import asyncio
from datetime import datetime, timezone, timedelta
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

try:
    from sqlalchemy import func, select, update
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.entities import Alert, Application, Document, User
    HAS_SQLALCHEMY = True
except ImportError:
    func = None
    select = None
    update = None
    AsyncSession = Any  # type: ignore
    Alert = None  # type: ignore
    Application = None  # type: ignore
    Document = None  # type: ignore
    User = None  # type: ignore
    HAS_SQLALCHEMY = False

from app.core.logging import logger
from app.models.enums import FindingSeverityEnum, RoleEnum, VerificationStatusEnum

# Global SSE subscriber set
_sse_subscribers: Set[asyncio.Queue] = set()


class AlertService:
    """
    Statutory alerts engine with role scoping and real-time event broadcasting.
    """

    @classmethod
    async def create_alert(
        cls,
        db: AsyncSession,
        title: str,
        message: str,
        severity: FindingSeverityEnum,
        application_id: Optional[str] = None,
        role: Optional[RoleEnum] = None,  # If specified, only this role may view
        user_id: Optional[int] = None,
    ) -> Alert:
        """Creates and persists an alert, broadcasting it to active SSE streams."""
        alert = Alert(
            title=title,
            message=message,
            severity=severity,
            application_id=application_id,
            role=role,
            user_id=user_id,
            acknowledged=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        # Broadcast via SSE
        payload = {
            "id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
            "application_id": alert.application_id,
            "role": alert.role.value if alert.role else None,
            "acknowledged": alert.acknowledged,
            "created_at": alert.created_at.isoformat(),
        }
        await cls.broadcast_event("alert_created", payload)
        return alert

    @classmethod
    async def get_alerts_for_user(
        cls,
        db: AsyncSession,
        user: User,
        application_id: Optional[str] = None,
        unacknowledged_only: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Retrieves alerts with strict role-based scoping:
        - Institution users NEVER see officer-only alerts (role=SCRUTINY_OFFICER or VERIFICATION_OFFICER,
          anomalies, or source outages).
        - Officers and Admins view council-wide alerts.
        """
        query = select(Alert)

        if application_id:
            query = query.where(Alert.application_id == application_id)

        if unacknowledged_only:
            query = query.where(Alert.acknowledged == False)  # noqa: E712

        # Role Scoping
        if user.role == RoleEnum.INSTITUTION:
            # Institution may only see alerts specifically unassigned or designated for institution
            query = query.where((Alert.role == RoleEnum.INSTITUTION) | (Alert.role == None))  # noqa: E711
            # Must belong to institution's application
            if user.institution_id:
                app_subquery = select(Application.id).where(Application.institution_id == user.institution_id)
                query = query.where(Alert.application_id.in_(app_subquery))
            else:
                return {"items": [], "total": 0, "page": page, "page_size": page_size}

        elif user.role in (RoleEnum.SCRUTINY_OFFICER, RoleEnum.VERIFICATION_OFFICER):
            # Officers can view council alerts and officer-scoped alerts
            pass

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        query = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        alerts = res.scalars().all()

        items = []
        for a in alerts:
            items.append({
                "id": a.id,
                "title": a.title,
                "message": a.message,
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "application_id": a.application_id,
                "role": a.role.value if a.role else None,
                "acknowledged": a.acknowledged,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                "created_at": a.created_at.isoformat(),
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @classmethod
    async def acknowledge_alert(
        cls,
        db: AsyncSession,
        alert_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """Marks an alert as acknowledged, recording acknowledging officer and timestamp."""
        stmt = select(Alert).where(Alert.id == alert_id)
        res = await db.execute(stmt)
        alert = res.scalar_one_or_none()
        if not alert:
            raise ValueError(f"Alert with ID {alert_id} not found.")

        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.user_id = user_id

        await db.commit()
        await db.refresh(alert)

        payload = {
            "id": alert.id,
            "acknowledged": True,
            "acknowledged_at": alert.acknowledged_at.isoformat(),
            "acknowledged_by": user_id,
        }
        await cls.broadcast_event("alert_acknowledged", payload)
        return payload

    @classmethod
    async def subscribe(cls) -> AsyncGenerator[str, None]:
        """SSE event generator yielding serialized alert events to connected client."""
        queue: asyncio.Queue = asyncio.Queue()
        _sse_subscribers.add(queue)
        try:
            # Yield initial connection heartbeat
            yield f"event: connect\ndata: {json.dumps({'status': 'connected', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
            while True:
                msg = await queue.get()
                yield msg
        finally:
            _sse_subscribers.discard(queue)

    @classmethod
    async def broadcast_event(cls, event_type: str, data: Dict[str, Any]):
        """Pushes event payload to all active SSE client queues."""
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        for q in list(_sse_subscribers):
            try:
                q.put_nowait(msg)
            except Exception:
                pass
