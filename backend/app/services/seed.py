import asyncio
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_async_engine
from app.core.logging import logger
from app.core.security import hash_password
from app.models.entities import (
    Alert,
    Application,
    AuditEntry,
    ChecklistResult,
    Document,
    Evidence,
    ExtractedField,
    Finding,
    Institution,
    OfficerAction,
    PipelineJob,
    RefRecord,
    RulePack,
    RulePackVersion,
    User,
    VerificationRecord,
)
from app.models.enums import (
    ApplicationStateEnum,
    RoleEnum,
    RulePackStatusEnum,
    ScanStatusEnum,
)
from app.services.storage import encrypt_file_bytes
from data.synthetic.generate import INSTITUTIONS as SYNTHETIC_INSTITUTIONS, generate_synthetic_dataset

DEMO_USERS = [
    {
        "email": "admin@aicte.gov.in",
        "password": "Admin@Fixora2026!",
        "role": RoleEnum.ADMIN,
        "full_name": "AICTE System Administrator",
        "institution_id": None,
    },
    {
        "email": "scrutiny@aicte.gov.in",
        "password": "Scrutiny@Fixora2026!",
        "role": RoleEnum.SCRUTINY_OFFICER,
        "full_name": "Dr. Ramesh Chandra (Scrutiny Bureau)",
        "institution_id": None,
    },
    {
        "email": "verification@aicte.gov.in",
        "password": "Verification@Fixora2026!",
        "role": RoleEnum.VERIFICATION_OFFICER,
        "full_name": "Smt. Sunita Rao (Verification Bureau)",
        "institution_id": None,
    },
    {
        "email": "principal@gecpune.edu.in",
        "password": "Inst1@Fixora2026!",
        "role": RoleEnum.INSTITUTION,
        "full_name": "Prof. D. K. Deshmukh (Principal, GEC Pune)",
        "institution_id": "1-33276541",
    },
    {
        "email": "director@mitmumbai.edu.in",
        "password": "Inst2@Fixora2026!",
        "role": RoleEnum.INSTITUTION,
        "full_name": "Dr. V. N. Patil (Director, MIT Mumbai)",
        "institution_id": "1-44589210",
    },
    {
        "email": "principal@kitmblr.edu.in",
        "password": "Inst3@Fixora2026!",
        "role": RoleEnum.INSTITUTION,
        "full_name": "Dr. A. K. Narayan (Principal, KITM Bengaluru)",
        "institution_id": "1-55691023",
    },
    {
        "email": "director@ncphyderabad.edu.in",
        "password": "Inst4@Fixora2026!",
        "role": RoleEnum.INSTITUTION,
        "full_name": "Dr. Priya Reddy (Director, NCP Hyderabad)",
        "institution_id": "1-66782345",
    },
    {
        "email": "dean@daapdelhi.edu.in",
        "password": "Inst5@Fixora2026!",
        "role": RoleEnum.INSTITUTION,
        "full_name": "Prof. Sanjay Malhotra (Dean, DAAP New Delhi)",
        "institution_id": "1-77893456",
    },
    {
        "email": "principal@tnihmchennai.edu.in",
        "password": "Inst6@Fixora2026!",
        "role": RoleEnum.INSTITUTION,
        "full_name": "Dr. K. Swaminathan (Principal, TNIHM Chennai)",
        "institution_id": "1-88904567",
    },
]


async def seed_rule_packs(db: AsyncSession) -> int:
    """Seeds the EOA-CHECKLIST v1 statutory rule pack if not present."""
    seeded = 0
    res = await db.execute(select(RulePack).where(RulePack.id == "EOA-CHECKLIST-v1"))
    pack = res.scalar_one_or_none()
    if not pack:
        pack = RulePack(
            id="EOA-CHECKLIST-v1",
            name="AICTE Approval Process Handbook (EoA) Checklist",
            description="Statutory Extension of Approval validation norms for academic year 2024-2025",
            status=RulePackStatusEnum.APPROVED,
        )
        db.add(pack)
        await db.flush()

        yaml_path = Path("data/rulepacks/eoa_checklist_v1.yaml")
        if yaml_path.exists():
            yaml_content = yaml_path.read_text(encoding="utf-8")
        else:
            yaml_content = "id: EOA-CHECKLIST-v1\nversion: v1\nitems: []\n"

        checksum = hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()
        version_obj = RulePackVersion(
            rule_pack_id="EOA-CHECKLIST-v1",
            version="v1",
            rules_yaml=yaml_content,
            checksum=checksum,
            status="Approved",
            is_active=True,
            approved_at=datetime.now(timezone.utc),
        )
        db.add(version_obj)
        seeded += 1
        await db.flush()
    return seeded


async def seed_demo_data(db: AsyncSession) -> Dict[str, int]:
    """Seeds demo institutions, users, ref_records, applications, encrypted documents, and rule packs."""
    seeded_counts = {
        "rule_packs": 0,
        "institutions": 0,
        "ref_records": 0,
        "users": 0,
        "applications": 0,
        "documents": 0,
    }

    # 1. Rule Pack
    seeded_counts["rule_packs"] = await seed_rule_packs(db)

    # 2. Institutions & RefRecords
    for inst_data in SYNTHETIC_INSTITUTIONS:
        res = await db.execute(select(Institution).where(Institution.id == inst_data["id"]))
        inst = res.scalar_one_or_none()
        if not inst:
            inst = Institution(
                id=inst_data["id"],
                name=inst_data["name"],
                address=inst_data["address"],
                state=inst_data["state"],
                district=inst_data["district"],
                pin_code=inst_data["pin_code"],
                contact_email=inst_data["contact_email"],
                contact_phone=inst_data["contact_phone"],
            )
            db.add(inst)
            seeded_counts["institutions"] += 1
        await db.flush()

        # RefRecord
        ref_res = await db.execute(select(RefRecord).where(RefRecord.institution_id == inst_data["id"]))
        ref_rec = ref_res.scalar_one_or_none()
        if not ref_rec:
            ref_rec = RefRecord(
                institution_id=inst_data["id"],
                previous_eoa={
                    "academic_year": "2023-2024",
                    "status": "APPROVED",
                    "extension_date": "2023-06-15",
                    "approval_letter_ref": f"AICTE/WR/EOA/{inst_data['id']}/2023",
                },
                approved_programmes_and_intake=inst_data["programmes"],
                faculty_count=inst_data["faculty_count"],
                ter_payment_status="PAID",
                deficiency_status="NO_DEFICIENCY",
            )
            db.add(ref_rec)
            seeded_counts["ref_records"] += 1
    await db.flush()

    # 3. Users
    for user_data in DEMO_USERS:
        res = await db.execute(select(User).where(User.email == user_data["email"]))
        if not res.scalar_one_or_none():
            u = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
                full_name=user_data["full_name"],
                institution_id=user_data["institution_id"],
                is_active=True,
            )
            db.add(u)
            seeded_counts["users"] += 1
    await db.flush()

    # 4. Generate Synthetic Applications & Documents
    synthetic_dir = Path("data/synthetic")
    synth_result = generate_synthetic_dataset(synthetic_dir)
    storage_root = Path(getattr(settings, "STORAGE_PATH", "storage"))
    storage_root.mkdir(parents=True, exist_ok=True)

    for app_info in synth_result["applications"]:
        app_id = app_info["id"]
        res = await db.execute(select(Application).where(Application.id == app_id))
        app = res.scalar_one_or_none()
        if not app:
            app = Application(
                id=app_id,
                institution_id=app_info["institution_id"],
                category=app_info["category"],
                academic_year=app_info["academic_year"],
                checklist_pack_version=app_info["checklist_pack_version"],
                state=ApplicationStateEnum.READY_FOR_SCRUTINY if "DEMO" in app_id else ApplicationStateEnum.SUBMITTED,
                priority_score=15.0,
                submitted_at=datetime.now(timezone.utc),
                form_data=app_info["form_data"],
            )
            db.add(app)
            seeded_counts["applications"] += 1
            await db.flush()

            # Seed documents for this application
            doc_idx = 1
            app_storage_dir = storage_root / "documents" / app_id
            app_storage_dir.mkdir(parents=True, exist_ok=True)

            for doc_meta in app_info["documents"]:
                doc_id = f"D-{app_id[-5:]}-{doc_idx:02d}"
                raw_file_path = Path(doc_meta["path"])
                if raw_file_path.exists():
                    raw_bytes = raw_file_path.read_bytes()
                    enc_bytes = encrypt_file_bytes(raw_bytes)
                    token = os.urandom(16).hex()
                    enc_filename = f"{token}.enc"
                    target_file = app_storage_dir / enc_filename
                    target_file.write_bytes(enc_bytes)
                    file_ref = f"/storage/documents/{app_id}/{enc_filename}"

                    doc = Document(
                        id=doc_id,
                        application_id=app_id,
                        class_name=doc_meta["class_name"],
                        file_ref=file_ref,
                        sha256=doc_meta["sha256"],
                        page_count=doc_meta["page_count"],
                        scan_status=ScanStatusEnum.COMPLETED,
                        classification_confidence=0.98,
                    )
                    db.add(doc)
                    seeded_counts["documents"] += 1
                    doc_idx += 1

    await db.commit()
    logger.info("Demo data seeding completed", extra={"seeded": seeded_counts})
    return seeded_counts


async def reset_demo_data(db: AsyncSession) -> Dict[str, Any]:
    """Purges demo state and clears documents from storage."""
    # Delete child tables first to respect foreign keys
    await db.execute(delete(Evidence))
    await db.execute(delete(Finding))
    await db.execute(delete(Alert))
    await db.execute(delete(OfficerAction))
    await db.execute(delete(VerificationRecord))
    await db.execute(delete(ChecklistResult))
    await db.execute(delete(ExtractedField))
    await db.execute(delete(PipelineJob))
    await db.execute(delete(Document))
    await db.execute(delete(Application))
    await db.execute(delete(AuditEntry))
    await db.commit()

    # Clear storage documents folder
    storage_docs = Path(getattr(settings, "STORAGE_PATH", "storage")) / "documents"
    if storage_docs.exists():
        for item in storage_docs.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    logger.info("Demo state reset successfully.")
    return {"status": "reset", "message": "Demo state reset and storage cleared."}


async def run_standalone_seed():
    get_async_engine()
    async with AsyncSessionLocal() as session:
        return await seed_demo_data(session)


if __name__ == "__main__":
    asyncio.run(run_standalone_seed())
