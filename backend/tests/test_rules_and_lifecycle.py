import hashlib
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
try:
    import pytest
except ImportError:
    import contextlib

    class _MockMark:
        @staticmethod
        def asyncio(fn):
            return fn

    class _MockPytest:
        mark = _MockMark()

        @staticmethod
        def fixture(fn):
            return fn

        @staticmethod
        def raises(exc, match=None):
            @contextlib.contextmanager
            def _cm():
                try:
                    yield
                except exc as e:
                    if match and match not in str(e):
                        raise AssertionError(f"Expected match '{match}', got '{str(e)}'")
                else:
                    raise AssertionError(f"Expected exception {exc} not raised")
            return _cm()

    pytest = _MockPytest()

try:
    from httpx import ASGITransport, AsyncClient
except ImportError:
    ASGITransport = None
    AsyncClient = None
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from app.core.auth import get_db
    from app.core.security import create_access_token, hash_password
    from app.main import app
    from app.models.base import Base
    from app.models.entities import (
        Application,
        AuditEntry,
        Document,
        Institution,
        RefRecord,
        RulePack,
        RulePackVersion,
        User,
    )
    from app.services.rule_pack_service import RulePackService
    HAS_SQLALCHEMY = True
except ImportError:
    create_engine = None
    Session = None
    sessionmaker = None
    RulePackService = None
    HAS_SQLALCHEMY = False

from app.models.enums import (
    ApplicationStateEnum,
    ChecklistResultEnum,
    FindingSeverityEnum,
    RoleEnum,
    ScanStatusEnum,
)
from app.rules.evaluator import evaluate
from app.services.state_machine import ApplicationStateMachine, IllegalStateTransitionError
from app.services.storage import (
    MockVirusScanner,
    decrypt_file_bytes,
    encrypt_file_bytes,
    validate_upload_file,
)


class AsyncSessionWrapper:
    """Wraps synchronous SQLite session for testing async FastAPI dependencies."""

    def __init__(self, sync_session):
        self.session = sync_session

    async def execute(self, statement, *args, **kwargs):
        return self.session.execute(statement, *args, **kwargs)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def close(self):
        self.session.close()

    def add(self, instance):
        self.session.add(instance)


@pytest.fixture
def db_session():
    if not HAS_SQLALCHEMY:
        yield None
        return
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sm = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = sm()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. TEST ALL 11 RULE EVALUATION TYPES (PASS & FAIL CASES + BOUNDARY DATES)
# ---------------------------------------------------------------------------

def test_rule_document_required():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-DOC-REQ",
                "type": "document_required",
                "clause_ref": "APH-2024-Clause-1.1",
                "severity": "review_required",
                "target_document_class": "affidavit",
                "message_template": "Affidavit required.",
            }
        ],
    }

    # Pass case
    ctx_pass = {"documents": [{"class_name": "affidavit", "scan_status": "COMPLETED"}]}
    res_pass = evaluate(pack, ctx_pass)
    assert res_pass[0]["result"] == ChecklistResultEnum.PRESENT.value

    # Fail case
    ctx_fail = {"documents": [{"class_name": "fire_safety", "scan_status": "COMPLETED"}]}
    res_fail = evaluate(pack, ctx_fail)
    assert res_fail[0]["result"] == ChecklistResultEnum.MISSING.value


def test_rule_document_validity_and_boundary_dates():
    now = datetime.now(timezone.utc)
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-DOC-EXP",
                "type": "document_validity",
                "clause_ref": "APH-2024-Clause-1.2",
                "severity": "review_required",
                "target_document_class": "fire_safety",
                "validity_check": "must_not_be_expired",
                "field_name": "valid_until",
                "message_template": "Fire certificate must not be expired.",
            },
            {
                "id": "RULE-DOC-AGE",
                "type": "document_validity",
                "clause_ref": "APH-2024-Clause-1.3",
                "severity": "needs_attention",
                "target_document_class": "affidavit",
                "validity_check": "max_age_days",
                "max_age_days": 180,
                "field_name": "issue_date",
                "message_template": "Affidavit must not be older than 180 days.",
            },
        ],
    }

    # Pass case (future expiry, recent issue date)
    future_date = (now + timedelta(days=60)).strftime("%Y-%m-%d")
    recent_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    ctx_pass = {
        "documents": [
            {"class_name": "fire_safety", "scan_status": "COMPLETED"},
            {"class_name": "affidavit", "scan_status": "COMPLETED"},
        ],
        "extracted_fields": {
            "fire_safety": {"valid_until": future_date},
            "affidavit": {"issue_date": recent_date},
        },
    }
    res_pass = evaluate(pack, ctx_pass)
    assert res_pass[0]["result"] == ChecklistResultEnum.VERIFIED.value
    assert res_pass[1]["result"] == ChecklistResultEnum.VERIFIED.value

    # Fail case (expired, and aged > 180 days)
    past_date = (now - timedelta(days=10)).strftime("%Y-%m-%d")
    aged_date = (now - timedelta(days=200)).strftime("%Y-%m-%d")
    ctx_fail = {
        "documents": [
            {"class_name": "fire_safety", "scan_status": "COMPLETED"},
            {"class_name": "affidavit", "scan_status": "COMPLETED"},
        ],
        "extracted_fields": {
            "fire_safety": {"valid_until": past_date},
            "affidavit": {"issue_date": aged_date},
        },
    }
    res_fail = evaluate(pack, ctx_fail)
    assert res_fail[0]["result"] == ChecklistResultEnum.EXPIRED.value
    assert res_fail[1]["result"] == ChecklistResultEnum.EXPIRED.value


def test_rule_field_required():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-FIELD-REQ",
                "type": "field_required",
                "clause_ref": "APH-2024-Clause-2.1",
                "severity": "review_required",
                "field_name": "principal_name",
                "message_template": "Principal name is required.",
            }
        ],
    }
    # Pass
    res_pass = evaluate(pack, {"form_data": {"principal_name": "Dr. Ramesh"}})
    assert res_pass[0]["result"] == ChecklistResultEnum.VERIFIED.value

    # Fail
    res_fail = evaluate(pack, {"form_data": {"principal_name": ""}})
    assert res_fail[0]["result"] == ChecklistResultEnum.MISSING.value


def test_rule_field_format_regex():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-FMT",
                "type": "field_format",
                "clause_ref": "APH-2024-Clause-2.2",
                "severity": "needs_attention",
                "field_name": "pin_code",
                "regex_pattern": "^[1-9][0-9]{5}$",
                "message_template": "Invalid PIN code.",
            }
        ],
    }
    assert evaluate(pack, {"form_data": {"pin_code": "411005"}})[0]["result"] == ChecklistResultEnum.VERIFIED.value
    assert evaluate(pack, {"form_data": {"pin_code": "0123"}})[0]["result"] == ChecklistResultEnum.INCONSISTENT.value


def test_rule_cross_field_consistency():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-CROSS",
                "type": "cross_field_consistency",
                "clause_ref": "APH-2024-Clause-2.3",
                "severity": "needs_attention",
                "field_a": "programme_faculty_sum",
                "field_b": "total_faculty_count",
                "message_template": "Faculty count mismatch.",
            }
        ],
    }
    assert evaluate(pack, {"form_data": {"programme_faculty_sum": 50, "total_faculty_count": 50}})[0]["result"] == ChecklistResultEnum.VERIFIED.value
    assert evaluate(pack, {"form_data": {"programme_faculty_sum": 45, "total_faculty_count": 50}})[0]["result"] == ChecklistResultEnum.INCONSISTENT.value


def test_rule_form_to_document_match():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-FORM-DOC",
                "type": "form_to_document_match",
                "clause_ref": "APH-2024-Clause-3.1",
                "severity": "review_required",
                "form_field": "institution_name",
                "target_document_class": "land_deed",
                "document_field": "owner_name",
                "message_template": "Name on land deed must match form.",
            }
        ],
    }
    # Pass
    ctx_pass = {
        "form_data": {"institution_name": "Government Engineering College Pune"},
        "extracted_fields": {"land_deed": {"owner_name": "Government Engineering College Pune"}},
    }
    assert evaluate(pack, ctx_pass)[0]["result"] == ChecklistResultEnum.VERIFIED.value

    # Fail
    ctx_fail = {
        "form_data": {"institution_name": "Government Engineering College Pune"},
        "extracted_fields": {"land_deed": {"owner_name": "St. Peters Technical College"}},
    }
    assert evaluate(pack, ctx_fail)[0]["result"] == ChecklistResultEnum.INCONSISTENT.value


def test_rule_form_to_record_match_with_tolerance():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-RECORD-MATCH",
                "type": "form_to_record_match",
                "clause_ref": "APH-2024-Clause-3.2",
                "severity": "review_required",
                "form_field": "applied_intake",
                "record_field": "approved_intake",
                "tolerance_percent": 10.0,
                "message_template": "Intake variance exceeding tolerance.",
            }
        ],
    }
    # Within tolerance (+8%)
    ctx_pass = {
        "form_data": {"applied_intake": 108},
        "ref_records": {"approved_intake": 100},
    }
    assert evaluate(pack, ctx_pass)[0]["result"] == ChecklistResultEnum.VERIFIED.value

    # Exceeds tolerance (+50%)
    ctx_fail = {
        "form_data": {"applied_intake": 150},
        "ref_records": {"approved_intake": 100},
    }
    assert evaluate(pack, ctx_fail)[0]["result"] == ChecklistResultEnum.INCONSISTENT.value


def test_rule_record_status():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-REC-STATUS",
                "type": "record_status",
                "clause_ref": "APH-2024-Clause-4.1",
                "severity": "review_required",
                "record_field": "ter_payment_status",
                "expected_status": "PAID",
                "message_template": "TER payment must be PAID.",
            }
        ],
    }
    assert evaluate(pack, {"ref_records": {"ter_payment_status": "PAID"}})[0]["result"] == ChecklistResultEnum.VERIFIED.value
    assert evaluate(pack, {"ref_records": {"ter_payment_status": "PENDING"}})[0]["result"] == ChecklistResultEnum.INCONSISTENT.value


def test_rule_numeric_threshold():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-THRESH",
                "type": "numeric_threshold",
                "clause_ref": "APH-2024-Clause-5.1",
                "severity": "needs_attention",
                "field_name": "land_area_acres",
                "operator": ">=",
                "threshold_value": 7.5,
                "message_template": "Minimum 7.5 acres required.",
            }
        ],
    }
    assert evaluate(pack, {"form_data": {"land_area_acres": 10.0}})[0]["result"] == ChecklistResultEnum.VERIFIED.value
    assert evaluate(pack, {"form_data": {"land_area_acres": 5.0}})[0]["result"] == ChecklistResultEnum.INCONSISTENT.value


def test_rule_conditional():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-COND",
                "type": "conditional",
                "clause_ref": "APH-2024-Clause-6.1",
                "severity": "review_required",
                "if_condition": {"field": "is_minority_institution", "equals": True},
                "then_rule": {
                    "type": "document_required",
                    "target_document_class": "minority_certificate",
                },
                "message_template": "Minority certificate required for minority institutions.",
            }
        ],
    }
    # If condition not triggered -> VERIFIED
    assert evaluate(pack, {"form_data": {"is_minority_institution": False}})[0]["result"] == ChecklistResultEnum.VERIFIED.value

    # If triggered and document present -> PRESENT
    ctx_present = {
        "form_data": {"is_minority_institution": True},
        "documents": [{"class_name": "minority_certificate", "scan_status": "COMPLETED"}],
    }
    assert evaluate(pack, ctx_present)[0]["result"] == ChecklistResultEnum.PRESENT.value

    # If triggered and document missing -> MISSING
    ctx_missing = {
        "form_data": {"is_minority_institution": True},
        "documents": [],
    }
    assert evaluate(pack, ctx_missing)[0]["result"] == ChecklistResultEnum.MISSING.value


def test_rule_infrastructure_norm():
    pack = {
        "id": "TEST-PACK",
        "version": "v1",
        "items": [
            {
                "id": "RULE-INFRA",
                "type": "infrastructure_norm",
                "clause_ref": "APH-2024-Clause-7.1",
                "severity": "needs_attention",
                "actual_field": "actual_carpet_area_sqm",
                "norm_field": "prescribed_carpet_area_sqm",
                "message_template": "Carpet area compliance.",
            }
        ],
    }
    # >= 1.0 -> consistent
    r1 = evaluate(pack, {"form_data": {"actual_carpet_area_sqm": 5000, "prescribed_carpet_area_sqm": 4800}})[0]
    assert r1["infrastructure_output"] == "consistent"
    assert r1["result"] == ChecklistResultEnum.VERIFIED.value

    # 0.8 to 1.0 -> needs_additional_evidence
    r2 = evaluate(pack, {"form_data": {"actual_carpet_area_sqm": 4200, "prescribed_carpet_area_sqm": 5000}})[0]
    assert r2["infrastructure_output"] == "needs_additional_evidence"
    assert r2["result"] == ChecklistResultEnum.NEEDS_EVIDENCE.value

    # < 0.8 -> recommend_inspection
    r3 = evaluate(pack, {"form_data": {"actual_carpet_area_sqm": 3000, "prescribed_carpet_area_sqm": 5000}})[0]
    assert r3["infrastructure_output"] == "recommend_inspection"
    assert r3["result"] == ChecklistResultEnum.INCONSISTENT.value


# ---------------------------------------------------------------------------
# 2. TEST MAKER-CHECKER LIFECYCLE & VERSION PINNING
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_maker_checker_lifecycle_and_approval_constraint(db_session=None):
    if not HAS_SQLALCHEMY or db_session is None:
        return
    wrapped_db = AsyncSessionWrapper(db_session)

    # Create users
    author = User(id=1, email="author@aicte.gov.in", hashed_password="pw", role=RoleEnum.ADMIN, full_name="Author")
    officer = User(id=2, email="officer@aicte.gov.in", hashed_password="pw", role=RoleEnum.SCRUTINY_OFFICER, full_name="Officer")
    db_session.add_all([author, officer])
    db_session.commit()

    service = RulePackService(wrapped_db)

    # 1. Author creates draft version
    yaml_v1 = "id: TEST-PACK\nversion: v1\nitems: []\n"
    v1 = await service.create_draft_version("TEST-PACK", "v1", yaml_v1, author_id=1)
    assert v1.status == "Draft"
    assert v1.is_active is False

    # 2. Submit for review
    v1_submitted = await service.submit_for_review("TEST-PACK", "v1")
    assert v1_submitted.status == "In review"

    # 3. Author attempts to approve own rulepack -> Violation raises ValueError
    with pytest.raises(ValueError, match="Maker-checker constraint violation"):
        await service.approve_version("TEST-PACK", "v1", approver_id=1)

    # 4. Different officer approves -> Succeeds
    v1_approved = await service.approve_version("TEST-PACK", "v1", approver_id=2)
    assert v1_approved.status == "Approved"
    assert v1_approved.is_active is True

    # 5. Author creates v2, submits, and officer approves -> v1 becomes Retired
    yaml_v2 = "id: TEST-PACK\nversion: v2\nitems: []\n"
    await service.create_draft_version("TEST-PACK", "v2", yaml_v2, author_id=1)
    await service.submit_for_review("TEST-PACK", "v2")
    v2_approved = await service.approve_version("TEST-PACK", "v2", approver_id=2)
    assert v2_approved.status == "Approved"
    assert v2_approved.is_active is True

    # Check v1 was retired
    assert v1_approved.status == "Retired"
    assert v1_approved.is_active is False


# ---------------------------------------------------------------------------
# 3. TEST APPLICATION STATUTORY STATE MACHINE
# ---------------------------------------------------------------------------

def test_application_state_machine_transitions():
    sm = ApplicationStateMachine()

    # Valid automated transitions
    assert sm.can_transition(ApplicationStateEnum.DRAFT, ApplicationStateEnum.SUBMITTED) is True
    assert sm.can_transition(ApplicationStateEnum.SUBMITTED, ApplicationStateEnum.VALIDATION_IN_PROGRESS) is True
    assert sm.can_transition(ApplicationStateEnum.VALIDATION_IN_PROGRESS, ApplicationStateEnum.READY_FOR_SCRUTINY) is True

    # Automated process cannot transition beyond READY_FOR_SCRUTINY
    with pytest.raises(IllegalStateTransitionError):
        sm.transition(
            ApplicationStateEnum.READY_FOR_SCRUTINY,
            ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
            is_automated=True,
        )

    # Officer-gated transitions require reason
    with pytest.raises(ValueError, match="Officer gating requires a non-empty written reason"):
        sm.transition(
            ApplicationStateEnum.READY_FOR_SCRUTINY,
            ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
            is_automated=False,
            officer_role=RoleEnum.SCRUTINY_OFFICER,
            reason="",
        )

    # Valid officer transition with reason
    next_state = sm.transition(
        ApplicationStateEnum.READY_FOR_SCRUTINY,
        ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
        is_automated=False,
        officer_role=RoleEnum.SCRUTINY_OFFICER,
        reason="Assigned for formal scrutiny review",
    )
    assert next_state == ApplicationStateEnum.UNDER_OFFICIAL_REVIEW

    # Unauthorized role rejected
    with pytest.raises(IllegalStateTransitionError):
        sm.transition(
            ApplicationStateEnum.READY_FOR_SCRUTINY,
            ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
            is_automated=False,
            officer_role=RoleEnum.INSTITUTION,
            reason="Illegal attempt",
        )

    # Direct jump from DRAFT to CLOSED_BY_AUTHORITY is forbidden
    with pytest.raises(IllegalStateTransitionError):
        sm.transition(
            ApplicationStateEnum.DRAFT,
            ApplicationStateEnum.CLOSED_BY_AUTHORITY,
            is_automated=False,
            officer_role=RoleEnum.ADMIN,
            reason="Skip",
        )


# ---------------------------------------------------------------------------
# 4. TEST DOCUMENT UPLOAD VALIDATION & STORAGE ENCRYPTION ROUND-TRIP
# ---------------------------------------------------------------------------

def test_upload_magic_bytes_and_file_validation():
    # 1. Valid PDF bytes
    valid_pdf = b"%PDF-1.4\n1 0 obj <</Type /Catalog>> endobj\nxref\n0 1\n0000000000 65535 f\ntrailer <</Size 1>>\nstartxref\n9\n%%EOF"
    val = validate_upload_file("affidavit.pdf", "application/pdf", valid_pdf)
    assert val.is_valid is True
    assert val.detected_ext == ".pdf"

    # 2. Fake PDF with wrong magic bytes
    bad_pdf = b"FAKE PDF CONTENT"
    val_bad = validate_upload_file("affidavit.pdf", "application/pdf", bad_pdf)
    assert val_bad.is_valid is False
    assert "magic bytes do not match" in val_bad.error_message.lower()

    # 3. File exceeding size limit (>15MB)
    huge_data = b"0" * (16 * 1024 * 1024)
    val_huge = validate_upload_file("huge.pdf", "application/pdf", huge_data)
    assert val_huge.is_valid is False
    assert "exceeds maximum" in val_huge.error_message.lower()

    # 4. PNG Magic bytes
    valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    val_png = validate_upload_file("plan.png", "image/png", valid_png)
    assert val_png.is_valid is True
    assert val_png.detected_ext == ".png"


def test_fernet_storage_encryption_and_decryption_round_trip():
    original_payload = b"AICTE Extension of Approval Statutory Legal Content 2024-2025"
    
    # Encrypt
    encrypted_payload = encrypt_file_bytes(original_payload)
    assert encrypted_payload != original_payload
    assert not original_payload in encrypted_payload

    # Decrypt
    decrypted_payload = decrypt_file_bytes(encrypted_payload)
    assert decrypted_payload == original_payload
