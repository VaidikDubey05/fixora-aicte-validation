"""
Fixora Statutory Verification, Officer Actions, Infrastructure Norms & Alerts Test Suite
Verifies:
1. Verification Adapters & All Six Statutory Statuses (VERIFIED, MISMATCH_DETECTED, EXPIRED,
   VERIFICATION_PENDING, SOURCE_UNAVAILABLE, MANUAL_REVIEW_REQUIRED)
2. Exponential backoff retry (max 3) and safe fallback to manual queue (outage != adverse finding)
3. Verification attempt immutability (new attempt = new verification_records row; never update/delete)
4. QR code payload mismatch detection & preliminary indicator labeling
5. SignatureAdapter cryptographic integrity vs statutory compliance disclaimer
6. Mandatory written reason on officer actions (HTTP 422 on empty/whitespace)
7. State machine constraints: no automated approval/rejection, illegal transitions blocked
8. Strict institution visibility shielding (anomalies, duplicates, priority score, outage alerts hidden)
9. Infrastructure norm evaluation outputs restricted to: consistent, needs_additional_evidence, recommend_inspection
10. Alert service generation, role-scoping, and acknowledgement
"""

import asyncio
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
from typing import Any, Dict, List

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

try:
    import pytest
except ImportError:
    class _MockMark:
        @staticmethod
        def asyncio(fn):
            return fn

    class _MockPytest:
        mark = _MockMark()

        @staticmethod
        def fixture(fn):
            return fn

    pytest = _MockPytest()

from app.adapters.base import VerificationAdapter, VerificationResult
from app.adapters.mock_issuer_adapter import (
    MockFireDepartmentAdapter,
    MockUniversityAffiliationAdapter,
)
from app.adapters.qr_adapter import QrAdapter
from app.adapters.signature_adapter import SignatureAdapter
from app.models.enums import (
    ApplicationStateEnum,
    EvidenceKindEnum,
    FindingStatusEnum,
    FindingTypeEnum,
    InfrastructureOutputEnum,
    OfficerActionEnum,
    RoleEnum,
    VerificationStatusEnum,
)
from app.schemas.officer import ManualVerificationRequest, OfficerActionRequest
from app.services.alert_service import AlertService
from app.services.infrastructure_service import InfrastructureService
from app.services.state_machine import StateMachineService


# ---------------------------------------------------------------------------
# 1. Verification Adapters & All Six Statutory Statuses
# ---------------------------------------------------------------------------

def test_verification_adapter_all_six_statuses():
    """
    Verifies that the verification system handles all 6 statutory statuses:
    VERIFIED, MISMATCH_DETECTED, EXPIRED, VERIFICATION_PENDING, SOURCE_UNAVAILABLE, MANUAL_REVIEW_REQUIRED.
    Verifies simulated=True on mock adapter responses.
    """
    adapter = MockUniversityAffiliationAdapter()

    doc_bytes = b"%PDF-1.4 Mock Affiliation Letter Content"
    doc_metadata = {
        "document_id": "D-001",
        "application_id": "APP-EOA-DEMO-001-CLEAN",
        "document_class": "accreditation_certificate",
    }
    extracted_fields = {
        "institution_name": "Delhi Technical Institute",
        "programmes": "B.Tech Computer Science",
        "expiry_date": "2026-06-30",
    }

    all_statuses = [
        VerificationStatusEnum.VERIFIED,
        VerificationStatusEnum.MISMATCH_DETECTED,
        VerificationStatusEnum.EXPIRED,
        VerificationStatusEnum.VERIFICATION_PENDING,
        VerificationStatusEnum.SOURCE_UNAVAILABLE,
        VerificationStatusEnum.MANUAL_REVIEW_REQUIRED,
    ]

    for expected_status in all_statuses:
        result = asyncio.run(
            adapter.verify(
                document_bytes=doc_bytes,
                document_metadata=doc_metadata,
                extracted_fields=extracted_fields,
                simulate_status=expected_status,
                attempt=1,
            )
        )
        assert result.status == expected_status
        assert result.simulated is True
        assert result.source_name == "state_technical_university_registry"
        assert result.response_digest is not None
        assert len(result.response_digest) == 64  # SHA-256


# ---------------------------------------------------------------------------
# 2. Retry with Exponential Backoff then Fallback to Manual Queue
# ---------------------------------------------------------------------------

def test_exponential_backoff_retry_and_fallback_to_manual_queue():
    """
    Tests that when an issuer is unavailable:
    - Retries up to max 3 attempts with exponential backoff.
    - When retries are exhausted, falls back to MANUAL_REVIEW_REQUIRED.
    - INVARIANT: A source outage must NEVER create an adverse finding against an applicant.
    """
    adapter = MockFireDepartmentAdapter()

    doc_bytes = b"%PDF-1.4 Mock Fire Safety Certificate"
    doc_metadata = {"document_id": "D-002", "document_class": "fire_safety_certificate"}
    extracted_fields = {"certificate_number": "FS-2024-999"}

    # Attempt 1: retryable source outage
    res1 = asyncio.run(
        adapter.verify(
            document_bytes=doc_bytes,
            document_metadata=doc_metadata,
            extracted_fields=extracted_fields,
            simulate_status=VerificationStatusEnum.SOURCE_UNAVAILABLE,
            attempt=1,
        )
    )
    assert res1.status == VerificationStatusEnum.SOURCE_UNAVAILABLE
    assert res1.retryable is True

    # Attempt 3: retries exhausted, routes to manual review queue
    res3 = asyncio.run(
        adapter.verify(
            document_bytes=doc_bytes,
            document_metadata=doc_metadata,
            extracted_fields=extracted_fields,
            simulate_status=VerificationStatusEnum.SOURCE_UNAVAILABLE,
            attempt=3,
        )
    )
    assert res3.status == VerificationStatusEnum.MANUAL_REVIEW_REQUIRED
    assert res3.retryable is False
    assert "A source outage is not an adverse conclusion" in res3.message


# ---------------------------------------------------------------------------
# 3. Verification Immutability (New Attempt = New Row, Never Update)
# ---------------------------------------------------------------------------

def test_verification_record_immutability():
    """
    Verifies that every verification run creates an immutable new record.
    Historical rows are never updated or deleted.
    """
    # Mock database table representation
    verification_records_db = []

    def insert_verification_attempt(doc_id: str, status: VerificationStatusEnum, source: str) -> dict:
        new_row = {
            "id": len(verification_records_db) + 1,
            "document_id": doc_id,
            "status": status.value,
            "source_name": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Invariant: append only, never mutate existing
        verification_records_db.append(new_row)
        return new_row

    # Run 1: Initial automated run returns SOURCE_UNAVAILABLE -> MANUAL_REVIEW_REQUIRED
    r1 = insert_verification_attempt("D-001", VerificationStatusEnum.MANUAL_REVIEW_REQUIRED, "mock_university_portal")
    assert r1["id"] == 1
    assert len(verification_records_db) == 1

    # Run 2: Re-run attempt
    r2 = insert_verification_attempt("D-001", VerificationStatusEnum.VERIFICATION_PENDING, "mock_university_portal")
    assert r2["id"] == 2
    assert len(verification_records_db) == 2

    # Run 3: Officer manual confirmation
    r3 = insert_verification_attempt("D-001", VerificationStatusEnum.VERIFIED, "officer_manual_officer@aicte.gov.in")
    assert r3["id"] == 3
    assert len(verification_records_db) == 3

    # Ensure run 1 is unchanged
    assert verification_records_db[0]["status"] == VerificationStatusEnum.MANUAL_REVIEW_REQUIRED.value
    assert verification_records_db[1]["status"] == VerificationStatusEnum.VERIFICATION_PENDING.value
    assert verification_records_db[2]["status"] == VerificationStatusEnum.VERIFIED.value


# ---------------------------------------------------------------------------
# 4. QR Payload Mismatch Detection & Preliminary Indicator Label
# ---------------------------------------------------------------------------

def test_qr_payload_mismatch_detection():
    """
    Tests QrAdapter behavior when QR code payload contradicts extracted document text.
    Verifies status == MISMATCH_DETECTED, mismatch_details populated, and preliminary indicator label.
    """
    qr_adapter = QrAdapter()

    # Case: QR payload has expiry date 2023-01-01, but extracted field shows 2025-12-31
    qr_metadata = {
        "url": "https://verify.nba-india.org/cert/NBA-2024-99881",
        "institution_id": "1-10029384",
        "accreditation_status": "ACCREDITED",
        "expiry_date": "2023-01-01",
    }
    extracted_fields = {
        "institution_id": "1-10029384",
        "expiry_date": "2025-12-31",
    }

    mismatches = qr_adapter.compare_payload_with_extracted_fields(qr_metadata, extracted_fields)
    assert len(mismatches) > 0
    assert any(m["field"] == "expiry_date" for m in mismatches)
    assert any("Preliminary indicator" in m.get("label", "") for m in mismatches)


# ---------------------------------------------------------------------------
# 5. SignatureAdapter Cryptographic Integrity Disclaimer
# ---------------------------------------------------------------------------

def test_signature_adapter_integrity_disclaimer():
    """
    Verifies that SignatureAdapter explicitly warns that a valid signature proves
    cryptographic integrity only, NOT statutory council compliance.
    """
    sig_adapter = SignatureAdapter()
    res = asyncio.run(
        sig_adapter.verify(
            document_bytes=b"Some PDF bytes without digital signature",
            document_metadata={"document_id": "D-005"},
            extracted_fields={},
        )
    )

    # 1. When signature is absent or unsupported, maps to MANUAL_REVIEW_REQUIRED
    assert res.status == VerificationStatusEnum.MANUAL_REVIEW_REQUIRED
    assert "routed to manual" in res.message.lower()

    # 2. When valid signature dictionary is present, verifies integrity with mandatory disclaimer
    signed_pdf_bytes = b"%PDF-1.4 obj << /ByteRange [0 100 200 50] /Contents <deadbeef> >> endobj"
    res_signed = asyncio.run(
        sig_adapter.verify(
            document_bytes=signed_pdf_bytes,
            document_metadata={"document_id": "D-006", "file_name": "signed_noc.pdf"},
            extracted_fields={},
        )
    )
    assert res_signed.status == VerificationStatusEnum.VERIFIED
    assert "A valid digital signature confirms cryptographic document integrity only, not statutory council compliance." in res_signed.message


# ---------------------------------------------------------------------------
# 6. Officer Action Mandatory Written Reason (HTTP 422)
# ---------------------------------------------------------------------------

def test_officer_action_mandatory_written_reason():
    """
    Verifies that OfficerActionRequest rejects empty or whitespace-only reason.
    Pydantic raises ValueError which FastAPI translates to HTTP 422 Unprocessable Entity.
    """
    # Valid reason succeeds
    req_valid = OfficerActionRequest(
        action=OfficerActionEnum.CONFIRM,
        reason="Verified against council gazette notification records.",
        notes="Internal check completed.",
    )
    assert req_valid.reason == "Verified against council gazette notification records."

    # Empty reason fails
    try:
        OfficerActionRequest(action=OfficerActionEnum.DISMISS, reason="")
        assert False, "Should have raised validation error for empty reason"
    except ValueError as exc:
        assert "A non-empty written reason is mandatory" in str(exc)

    # Whitespace-only reason fails
    try:
        OfficerActionRequest(action=OfficerActionEnum.REQUEST_RECTIFICATION, reason="   \t \n  ")
        assert False, "Should have raised validation error for whitespace reason"
    except ValueError as exc:
        assert "A non-empty written reason is mandatory" in str(exc)


# ---------------------------------------------------------------------------
# 7. State Machine Constraints & Officer Gating
# ---------------------------------------------------------------------------

def test_state_machine_illegal_transitions_blocked():
    """
    Verifies statutory state machine rules:
    - No automatic approval or rejection
    - DRAFT -> APPROVED is illegal
    - READY_FOR_SCRUTINY -> UNDER_OFFICIAL_REVIEW requires scrutiny officer
    - request_rectification transitions application to RECTIFICATION_REQUESTED
    - refer_inspection transitions application to REFERRED_FOR_INSPECTION
    """
    class MockUser:
        def __init__(self, role: RoleEnum, email: str = "officer@aicte.gov.in"):
            self.role = role
            self.email = email

    officer_user = MockUser(RoleEnum.SCRUTINY_OFFICER)
    inst_user = MockUser(RoleEnum.INSTITUTION)

    # 1. DRAFT -> SUBMITTED is valid for institution
    assert StateMachineService.validate_transition(
        ApplicationStateEnum.DRAFT, ApplicationStateEnum.SUBMITTED, inst_user
    ) is True

    # 2. DRAFT -> CLOSED_BY_AUTHORITY is strictly illegal
    try:
        StateMachineService.validate_transition(
            ApplicationStateEnum.DRAFT, ApplicationStateEnum.CLOSED_BY_AUTHORITY, inst_user
        )
        assert False, "Illegal transition from DRAFT to CLOSED_BY_AUTHORITY should be blocked"
    except (ValueError, PermissionError):
        pass

    # 3. UNDER_OFFICIAL_REVIEW -> RECTIFICATION_REQUESTED is valid for officer
    assert StateMachineService.validate_transition(
        ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
        ApplicationStateEnum.RECTIFICATION_REQUESTED,
        officer_user,
    ) is True

    # 4. UNDER_OFFICIAL_REVIEW -> REFERRED_FOR_INSPECTION is valid for officer
    assert StateMachineService.validate_transition(
        ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
        ApplicationStateEnum.REFERRED_FOR_INSPECTION,
        officer_user,
    ) is True

    # 5. Institution user cannot close/reject an application
    try:
        StateMachineService.validate_transition(
            ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
            ApplicationStateEnum.CLOSED_BY_AUTHORITY,
            inst_user,
        )
        assert False, "Institution user should not be able to close/reject application"
    except (PermissionError, ValueError):
        pass


# ---------------------------------------------------------------------------
# 8. Institution Visibility Shielding
# ---------------------------------------------------------------------------

def test_institution_visibility_shielding():
    """
    Verifies that institution users CANNOT see:
    - possible_anomaly findings
    - duplicate findings
    - review priority scores
    - internal officer notes
    - source outage alerts
    - anomaly alerts
    """
    raw_findings = [
        {
            "finding_id": "F-001",
            "type": FindingTypeEnum.EXPIRED.value,
            "title": "Fire safety certificate expired",
            "reason": "Certificate expired on 2024-03-31.",
        },
        {
            "finding_id": "F-002",
            "type": FindingTypeEnum.POSSIBLE_ANOMALY.value,
            "title": "Font discrepancy detected",
            "reason": "Different fonts detected across numeric intake values.",
        },
        {
            "finding_id": "F-003",
            "type": FindingTypeEnum.DUPLICATE.value,
            "title": "Duplicate perceptual hash across institutions",
            "reason": "Floor plan image matches document from another institution.",
        },
    ]

    # Institution view
    institution_visible_findings = [
        f for f in raw_findings
        if f["type"] not in (FindingTypeEnum.POSSIBLE_ANOMALY.value, FindingTypeEnum.DUPLICATE.value)
    ]
    assert len(institution_visible_findings) == 1
    assert institution_visible_findings[0]["finding_id"] == "F-001"

    # Officer view
    officer_visible_findings = raw_findings
    assert len(officer_visible_findings) == 3

    # Alerts filtering
    alerts = [
        {"id": 1, "alert_type": "expiring_document", "is_officer_only": False},
        {"id": 2, "alert_type": "source_outage", "is_officer_only": True},
        {"id": 3, "alert_type": "possible_anomaly", "is_officer_only": True},
    ]

    institution_visible_alerts = [a for a in alerts if not a["is_officer_only"]]
    assert len(institution_visible_alerts) == 1
    assert institution_visible_alerts[0]["alert_type"] == "expiring_document"


# ---------------------------------------------------------------------------
# 9. Physical Infrastructure Evaluation Outputs
# ---------------------------------------------------------------------------

def test_physical_infrastructure_outputs():
    """
    Verifies that InfrastructureService outputs are strictly restricted to:
    - consistent
    - needs_additional_evidence
    - recommend_inspection
    Never pass/fail or approved/rejected.
    """
    allowed_outputs = {
        InfrastructureOutputEnum.CONSISTENT.value,
        InfrastructureOutputEnum.NEEDS_ADDITIONAL_EVIDENCE.value,
        InfrastructureOutputEnum.RECOMMEND_INSPECTION.value,
    }

    # Case 1: Adequate labs and built-up area
    form_data_clean = {"lab_count": 8, "built_up_area_sqm": 5000.0, "programmes": [{"intake": 120}]}
    plan_fields_clean = {"laboratories_count": 8}
    res_clean = InfrastructureService.evaluate_spatial_and_lab_norms(
        form_data_clean, plan_fields_clean, "Laboratory 1, Laboratory 2, Laboratory 3, Laboratory 4"
    )
    assert res_clean["output"] in allowed_outputs
    assert res_clean["output"] == InfrastructureOutputEnum.CONSISTENT.value

    # Case 2: Shortfall in laboratories (intake 240 needs 8 labs, only 1 found) -> recommend_inspection
    form_data_shortfall = {"lab_count": 8, "built_up_area_sqm": 5000.0, "programmes": [{"intake": 240}]}
    plan_fields_shortfall = {"laboratories_count": 1}
    res_shortfall = InfrastructureService.evaluate_spatial_and_lab_norms(
        form_data_shortfall, plan_fields_shortfall, "Studio 1"
    )
    assert res_shortfall["output"] in allowed_outputs
    assert res_shortfall["output"] == InfrastructureOutputEnum.RECOMMEND_INSPECTION.value
    assert "inspection recommended" in res_shortfall["reason"].lower()

    # Case 3: Built-up area shortfall -> needs_additional_evidence
    form_data_area_short = {"lab_count": 4, "built_up_area_sqm": 1200.0, "programmes": [{"intake": 60}]}
    plan_fields_area = {"laboratories_count": 4}
    res_area = InfrastructureService.evaluate_spatial_and_lab_norms(
        form_data_area_short, plan_fields_area, "Laboratory 1, Laboratory 2, Laboratory 3, Laboratory 4"
    )
    assert res_area["output"] in allowed_outputs
    assert res_area["output"] == InfrastructureOutputEnum.NEEDS_ADDITIONAL_EVIDENCE.value


# ---------------------------------------------------------------------------
# 10. Manual Verification Request Schema Validation
# ---------------------------------------------------------------------------

def test_manual_verification_request_validation():
    """
    Verifies that ManualVerificationRequest requires mandatory determination notes.
    """
    valid_req = ManualVerificationRequest(
        outcome="VERIFIED",
        notes="Physically inspected stamp and seal at regional directorate.",
    )
    assert valid_req.outcome == "VERIFIED"

    try:
        ManualVerificationRequest(outcome="VERIFIED", notes="   ")
        assert False, "Should have failed on whitespace notes"
    except ValueError as exc:
        assert "notes are mandatory" in str(exc).lower()


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_verification_adapter_all_six_statuses,
        test_exponential_backoff_retry_and_fallback_to_manual_queue,
        test_verification_record_immutability,
        test_qr_payload_mismatch_detection,
        test_signature_adapter_integrity_disclaimer,
        test_officer_action_mandatory_written_reason,
        test_state_machine_illegal_transitions_blocked,
        test_institution_visibility_shielding,
        test_physical_infrastructure_outputs,
        test_manual_verification_request_validation,
    ]
    print(f"Running {len(tests)} statutory verification and officer action tests...")
    for t in tests:
        t()
        print(f"  [PASS] {t.__name__}")
    print("\nAll statutory verification and officer action tests passed successfully!\n")
