from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.entities import AuditEntry, User
from app.models.enums import RoleEnum
from app.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    summary="List tamper-evident audit trail entries (Scrutiny Officers & Admins only)",
)
async def list_audit_entries(
    actor: Optional[str] = Query(None, description="Filter by user email or actor identifier"),
    role: Optional[str] = Query(None, description="Filter by actor role"),
    event: Optional[str] = Query(None, description="Filter by event action (e.g. LOGIN, READ_DOCUMENT)"),
    application: Optional[str] = Query(None, description="Filter by application target ID"),
    date_from: Optional[str] = Query(None, description="Filter events after ISO-8601 UTC date"),
    date_to: Optional[str] = Query(None, description="Filter events before ISO-8601 UTC date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves paginated audit log entries with statutory filtering.
    Restricted to scrutiny_officer and admin roles.
    """
    query = select(AuditEntry)

    if actor:
        query = query.where(AuditEntry.actor.ilike(f"%{actor}%"))
    if role:
        query = query.where(AuditEntry.role == role)
    if event:
        query = query.where(AuditEntry.action.ilike(f"%{event}%"))
    if application:
        query = query.where(
            (AuditEntry.target_id == application)
            | (AuditEntry.payload["application_id"].astext == application)
        )
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(AuditEntry.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(AuditEntry.created_at <= dt_to)
        except ValueError:
            pass

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    # Pagination ordered by sequence descending (most recent first)
    query = query.order_by(AuditEntry.seq.desc()).offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(query)
    entries = res.scalars().all()

    items = [
        {
            "seq": e.seq,
            "actor": e.actor,
            "role": e.role,
            "action": e.action,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "payload": e.payload,
            "payload_hash": e.payload_hash,
            "prev_hash": e.prev_hash,
            "current_hash": e.current_hash,
            "rule_versions": e.rule_versions,
            "model_versions": e.model_versions,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/verify-chain",
    summary="Cryptographically verify SHA-256 audit chain integrity",
)
async def verify_chain(
    current_user: User = Depends(require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Recomputes the entire cryptographic SHA-256 hash chain from genesis to latest sequence.
    Detects any payload tampering, sequence gaps, or hash alterations.
    Returns: { valid: bool, checked: int, first_broken_seq: Optional[int] }
    """
    verification_result = await AuditService.verify_chain(db)
    return verification_result
