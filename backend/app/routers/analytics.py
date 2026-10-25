"""
Fixora Executive Analytics Router
Exposes GET /api/analytics/overview for scrutiny officers and administrators.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.models.entities import User
from app.models.enums import RoleEnum
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get(
    "/analytics/overview",
    summary="Executive statutory analytics and evaluation overview (Officers & Admins only)",
)
async def get_analytics_overview(
    current_user: User = Depends(require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns executive statutory overview:
    - Counts by application state
    - Deficiencies by type and severity
    - Queue ageing buckets (<24h, 24-48h, 48h-7d, >7d)
    - Average and median processing and verification times
    - Alert timeliness metrics
    - Estimated manual effort reduction with written methodology
    - Evaluation metrics block from data/eval/latest.json
    """
    overview = await AnalyticsService.get_overview(db)
    return overview
