import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.entities import RulePack, RulePackVersion
from app.models.enums import RulePackStatusEnum
from app.rules.evaluator import evaluate

# Safe YAML loading with JSON fallback
try:
    import yaml
    def parse_yaml(content: str) -> Dict[str, Any]:
        return yaml.safe_load(content)
except ImportError:
    def parse_yaml(content: str) -> Dict[str, Any]:
        return json.loads(content)


class RulePackService:
    """
    Manages statutory YAML rule packs with maker-checker lifecycle governance.
    Statuses: Draft -> In review -> Approved -> Retired
    Constraint: The approver must differ from the author.
    Version Pinning: New versions apply only to new applications.
    """

    @staticmethod
    def calculate_checksum(yaml_content: str) -> str:
        return hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()

    @staticmethod
    async def get_pack(db: AsyncSession, pack_id: str) -> Optional[RulePack]:
        stmt = (
            select(RulePack)
            .where(RulePack.id == pack_id)
            .options(selectinload(RulePack.versions))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_active_version(db: AsyncSession, pack_id: str) -> Optional[RulePackVersion]:
        stmt = (
            select(RulePackVersion)
            .where(RulePackVersion.rule_pack_id == pack_id, RulePackVersion.is_active == True)
            .order_by(RulePackVersion.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_draft(
        db: AsyncSession,
        pack_id: str,
        name: str,
        description: str,
        version: str,
        yaml_content: str,
        author_id: int,
    ) -> RulePackVersion:
        """Creates or registers a new rule pack draft version by an author."""
        pack = await RulePackService.get_pack(db, pack_id)
        if not pack:
            pack = RulePack(
                id=pack_id,
                name=name,
                description=description,
                status=RulePackStatusEnum.DRAFT,
            )
            db.add(pack)
            await db.flush()

        checksum = RulePackService.calculate_checksum(yaml_content)

        # Check if version already exists
        stmt = select(RulePackVersion).where(
            RulePackVersion.rule_pack_id == pack_id,
            RulePackVersion.version == version,
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            if existing.status in ("Approved", "Retired"):
                raise ValueError(f"Version '{version}' is already {existing.status} and immutable.")
            existing.rules_yaml = yaml_content
            existing.checksum = checksum
            existing.created_by = author_id
            existing.status = "Draft"
            version_entry = existing
        else:
            version_entry = RulePackVersion(
                rule_pack_id=pack_id,
                version=version,
                rules_yaml=yaml_content,
                checksum=checksum,
                created_by=author_id,
                status="Draft",
                is_active=False,
            )
            db.add(version_entry)

        await db.commit()
        return version_entry

    @staticmethod
    async def submit_for_review(
        db: AsyncSession,
        pack_id: str,
        version: str,
        user_id: int,
    ) -> RulePackVersion:
        """Transitions a draft pack version to 'In review'."""
        stmt = select(RulePackVersion).where(
            RulePackVersion.rule_pack_id == pack_id,
            RulePackVersion.version == version,
        )
        res = await db.execute(stmt)
        version_entry = res.scalar_one_or_none()

        if not version_entry:
            raise ValueError(f"Rule pack version '{pack_id}:{version}' not found.")
        if version_entry.status != "Draft":
            raise ValueError(f"Only 'Draft' versions can be submitted for review (current: {version_entry.status}).")

        version_entry.status = "In review"
        await db.commit()
        return version_entry

    @staticmethod
    async def approve_pack(
        db: AsyncSession,
        pack_id: str,
        version: str,
        approver_id: int,
    ) -> RulePackVersion:
        """
        Maker-Checker approval.
        Enforces: Approver must differ from the author.
        Retires previous active versions; newly created applications will use this new version.
        """
        stmt = select(RulePackVersion).where(
            RulePackVersion.rule_pack_id == pack_id,
            RulePackVersion.version == version,
        )
        res = await db.execute(stmt)
        version_entry = res.scalar_one_or_none()

        if not version_entry:
            raise ValueError(f"Rule pack version '{pack_id}:{version}' not found.")
        if version_entry.status not in ("In review", "Draft"):
            raise ValueError(f"Cannot approve version in '{version_entry.status}' state.")

        # Maker-checker validation constraint
        if version_entry.created_by is not None and version_entry.created_by == approver_id:
            raise PermissionError("Maker-checker violation: the approver must differ from the author.")

        # Retire older active versions
        await db.execute(
            update(RulePackVersion)
            .where(RulePackVersion.rule_pack_id == pack_id, RulePackVersion.is_active == True)
            .values(is_active=False, status="Retired")
        )

        version_entry.approved_by = approver_id
        version_entry.approved_at = datetime.now(timezone.utc)
        version_entry.status = "Approved"
        version_entry.is_active = True

        # Update parent pack status
        stmt_pack = select(RulePack).where(RulePack.id == pack_id)
        res_pack = await db.execute(stmt_pack)
        pack = res_pack.scalar_one_or_none()
        if pack:
            pack.status = RulePackStatusEnum.APPROVED

        await db.commit()
        return version_entry

    @staticmethod
    def test_pack(yaml_content: str, case_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parses and executes pure evaluation against supplied test context."""
        pack_data = parse_yaml(yaml_content)
        return evaluate(pack_data, case_context)

    @staticmethod
    async def seed_eoa_checklist_pack(db: AsyncSession, admin_id: int, approver_id: int) -> RulePackVersion:
        """Seeds the standard APH EOA-CHECKLIST v1 pack from data/rulepacks."""
        yaml_path = os.path.join("data", "rulepacks", "eoa_checklist_v1.yaml")
        if not os.path.exists(yaml_path):
            yaml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "rulepacks", "eoa_checklist_v1.yaml")

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_content = f.read()

        pack_data = parse_yaml(yaml_content)
        pack_id = pack_data["id"]
        version = pack_data["version"]

        version_entry = await RulePackService.create_draft(
            db=db,
            pack_id=pack_id,
            name=pack_data["name"],
            description=pack_data.get("description", ""),
            version=version,
            yaml_content=yaml_content,
            author_id=admin_id,
        )
        await RulePackService.submit_for_review(db, pack_id, version, admin_id)
        approved = await RulePackService.approve_pack(db, pack_id, version, approver_id)
        return approved
