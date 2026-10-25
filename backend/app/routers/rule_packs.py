from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.entities import RulePack, RulePackVersion, User
from app.models.enums import RoleEnum
from app.services.rule_pack_service import RulePackService

router = APIRouter(prefix="/rule-packs", tags=["rule-packs"])


class CreateRulePackRequest(BaseModel):
    id: str = Field(..., description="Unique pack identifier e.g. EOA-CHECKLIST")
    name: str
    description: Optional[str] = None
    version: str = Field(..., description="Semantic version string e.g. v1.0")
    rules_yaml: str = Field(..., description="Full YAML rule definitions")


class VersionActionRequest(BaseModel):
    version: str = Field(..., description="Target version to submit or approve")


class TestRulePackRequest(BaseModel):
    rules_yaml: Optional[str] = None
    version: Optional[str] = None
    case_context: Dict[str, Any] = Field(..., description="Mock application context for evaluation")


@router.get("", summary="List all statutory rule packs")
async def list_rule_packs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RulePack).options(selectinload(RulePack.versions)).order_by(RulePack.id)
    res = await db.execute(stmt)
    packs = res.scalars().all()
    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "status": p.status.value,
                "versions": [
                    {
                        "version": v.version,
                        "status": v.status,
                        "is_active": v.is_active,
                        "created_by": v.created_by,
                        "approved_by": v.approved_by,
                        "created_at": v.created_at.isoformat(),
                    }
                    for v in p.versions
                ],
            }
            for p in packs
        ],
        "total": len(packs),
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a draft rule pack or new version")
async def create_rule_pack(
    body: CreateRulePackRequest,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SCRUTINY_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    try:
        version_entry = await RulePackService.create_draft(
            db=db,
            pack_id=body.id,
            name=body.name,
            description=body.description or "",
            version=body.version,
            yaml_content=body.rules_yaml,
            author_id=current_user.id,
        )
        return {
            "pack_id": body.id,
            "version": version_entry.version,
            "status": version_entry.status,
            "checksum": version_entry.checksum,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{id}", summary="Get rule pack details and active version")
async def get_rule_pack(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pack = await RulePackService.get_pack(db, id)
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule pack '{id}' not found.")

    return {
        "id": pack.id,
        "name": pack.name,
        "description": pack.description,
        "status": pack.status.value,
        "versions": [
            {
                "version": v.version,
                "status": v.status,
                "checksum": v.checksum,
                "is_active": v.is_active,
                "rules_yaml": v.rules_yaml,
                "created_by": v.created_by,
                "approved_by": v.approved_by,
                "created_at": v.created_at.isoformat(),
            }
            for v in pack.versions
        ],
    }


@router.post("/{id}/submit", summary="Submit a draft rule pack version for maker-checker review")
async def submit_rule_pack(
    id: str,
    body: VersionActionRequest,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SCRUTINY_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await RulePackService.submit_for_review(db, id, body.version, current_user.id)
        return {"pack_id": id, "version": res.version, "status": res.status}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{id}/approve", summary="Approve a rule pack version (enforces approver != author)")
async def approve_rule_pack(
    id: str,
    body: VersionActionRequest,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SCRUTINY_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await RulePackService.approve_pack(db, id, body.version, current_user.id)
        return {
            "pack_id": id,
            "version": res.version,
            "status": res.status,
            "approved_by": res.approved_by,
            "is_active": res.is_active,
        }
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{id}/test", summary="Test rule pack evaluation against a sample case context")
async def test_rule_pack(
    id: str,
    body: TestRulePackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    yaml_content = body.rules_yaml
    if not yaml_content:
        # Load from database by version or active
        if body.version:
            stmt = select(RulePackVersion).where(
                RulePackVersion.rule_pack_id == id, RulePackVersion.version == body.version
            )
            res = await db.execute(stmt)
            v = res.scalar_one_or_none()
            if not v:
                raise HTTPException(status_code=404, detail=f"Version '{body.version}' not found.")
            yaml_content = v.rules_yaml
        else:
            active_v = await RulePackService.get_active_version(db, id)
            if not active_v:
                raise HTTPException(status_code=404, detail=f"No active version found for rule pack '{id}'.")
            yaml_content = active_v.rules_yaml

    try:
        results = RulePackService.test_pack(yaml_content, body.case_context)
        return {
            "pack_id": id,
            "items_evaluated": len(results),
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rule evaluation error: {str(exc)}")
