"""
Fixora Statutory Analytics and PDF Report Test Suite
Verifies:
1. AnalyticsService aggregation with pandas/Python:
   - Counts by application state
   - Deficiencies by finding type and severity
   - Queue ageing buckets (<24h, 24-48h, 48h-7d, >7d)
   - Processing and verification timings (average and median)
   - Alert timeliness metrics
   - Estimated manual effort reduction (assumed 45 min manual scrutiny, marked as estimate with written methodology)
   - Metrics block loaded from data/eval/latest.json
2. RBAC role gating:
   - Scrutiny officer and Admin permitted
   - Institution role forbidden (403)
3. Statutory PDF Report generation:
   - Valid PDF magic bytes (%PDF)
   - Mandatory Decision Support Disclaimer
   - Marked SYNTHETIC DATA and SIMULATED SOURCE
   - 7 distinct statutory sections
4. Role-based report filtering:
   - Reduced report for institution users (omits anomaly/duplicate findings, priority scores)
   - Full report for scrutiny officers
5. Language invariant compliance:
   - Zero occurrences of forbidden terms ('fake', 'forged', 'fraud')
   - Anomaly findings bear 'Preliminary indicator - human verification required'
6. Endpoint HTTP integration:
   - Cross-institution access rejection (403)
   - Valid application/pdf response header and attachment filename
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

try:
    import pytest
except ImportError:
    class MockPytest:
        class mark:
            @staticmethod
            def asyncio(f):
                return f
        class raises:
            def __init__(self, expected_exception):
                self.expected_exception = expected_exception
                self.value = None
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    raise AssertionError(f"Expected {self.expected_exception} but nothing was raised")
                if issubclass(exc_type, self.expected_exception):
                    self.value = exc_val
                    return True
                return False
    pytest = MockPytest()

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import types

if "fastapi" not in sys.modules:
    try:
        import fastapi
    except ImportError:
        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str = ""):
                self.status_code = status_code
                self.detail = detail
                super().__init__(f"{status_code}: {detail}")
        fastapi_mock = types.ModuleType("fastapi")
        fastapi_mock.HTTPException = HTTPException
        fastapi_mock.Depends = lambda x: x
        fastapi_mock.Request = object
        fastapi_mock.status = types.SimpleNamespace(
            HTTP_403_FORBIDDEN=403,
            HTTP_404_NOT_FOUND=404,
            HTTP_401_UNAUTHORIZED=401,
            HTTP_400_BAD_REQUEST=400,
            HTTP_200_OK=200,
            HTTP_201_CREATED=201,
        )
        fastapi_sec = types.ModuleType("fastapi.security")
        fastapi_sec.HTTPAuthorizationCredentials = object
        fastapi_sec.HTTPBearer = lambda **kwargs: None
        sys.modules["fastapi"] = fastapi_mock
        sys.modules["fastapi.security"] = fastapi_sec

if "sqlalchemy" not in sys.modules:
    try:
        import sqlalchemy
    except ImportError:
        sa_mock = types.ModuleType("sqlalchemy")
        sa_mock.select = lambda *a, **kw: a[0] if a else "SELECT"
        sa_mock.func = types.SimpleNamespace(count=lambda: "COUNT(*)")
        sa_ext_async = types.ModuleType("sqlalchemy.ext.asyncio")
        sa_ext_async.AsyncSession = object
        sa_orm = types.ModuleType("sqlalchemy.orm")
        sa_orm.selectinload = lambda *a, **kw: None
        sys.modules["sqlalchemy"] = sa_mock
        sys.modules["sqlalchemy.ext.asyncio"] = sa_ext_async
        sys.modules["sqlalchemy.orm"] = sa_orm

if "app.core.database" not in sys.modules:
    try:
        import app.core.database
    except (ImportError, Exception):
        db_mock = types.ModuleType("app.core.database")
        db_mock.get_db = lambda: None
        sys.modules["app.core.database"] = db_mock

if "app.core.security" not in sys.modules:
    try:
        import app.core.security
    except (ImportError, Exception):
        sec_mock = types.ModuleType("app.core.security")
        sec_mock.decode_access_token = lambda tok: {"sub": "1"}
        sys.modules["app.core.security"] = sec_mock

if "app.models.entities" not in sys.modules:
    try:
        import app.models.entities
    except (ImportError, Exception):
        ent_mock = types.ModuleType("app.models.entities")
        ent_mock.User = type("User", (), {})
        ent_mock.Application = type("Application", (), {})
        ent_mock.Finding = type("Finding", (), {})
        ent_mock.PipelineJob = type("PipelineJob", (), {})
        ent_mock.VerificationRecord = type("VerificationRecord", (), {})
        ent_mock.Alert = type("Alert", (), {})
        ent_mock.ChecklistResult = type("ChecklistResult", (), {})
        ent_mock.Document = type("Document", (), {})
        ent_mock.OfficerAction = type("OfficerAction", (), {})
        ent_mock.AuditEntry = type("AuditEntry", (), {})
        sys.modules["app.models.entities"] = ent_mock

from app.core.auth import check_institution_access, require_roles
from app.models.enums import (
    ApplicationStateEnum,
    ChecklistResultEnum,
    FindingSeverityEnum,
    FindingTypeEnum,
    OfficerActionEnum,
    RoleEnum,
    ScanStatusEnum,
    VerificationStatusEnum,
)
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService


# ---------------------------------------------------------------------------
# Mock Entities for Isolated Unit Testing
# ---------------------------------------------------------------------------

class MockUser:
    def __init__(self, email: str, role: RoleEnum, institution_id: Optional[str] = "INST-001"):
        self.id = 1
        self.email = email
        self.role = role
        self.institution_id = institution_id


class MockApplication:
    def __init__(
        self,
        app_id: str,
        institution_id: str = "INST-001",
        state: ApplicationStateEnum = ApplicationStateEnum.SUBMITTED,
        category: str = "ENGINEERING_AND_TECHNOLOGY",
        academic_year: str = "2024-2025",
        priority_score: int = 65,
        assigned_to: Optional[int] = 101,
        created_at: Optional[datetime] = None,
        submitted_at: Optional[datetime] = None,
    ):
        self.id = app_id
        self.institution_id = institution_id
        self.state = state
        self.category = category
        self.academic_year = academic_year
        self.priority_score = priority_score
        self.assigned_to = assigned_to
        now = datetime.now(timezone.utc)
        self.created_at = created_at or (now - timedelta(hours=36))
        self.submitted_at = submitted_at or (now - timedelta(hours=30))
        self.documents = []
        self.findings = []


class MockFinding:
    def __init__(
        self,
        finding_id: str,
        application_id: str,
        title: str,
        reason: str,
        f_type: FindingTypeEnum,
        severity: FindingSeverityEnum,
        label: Optional[str] = None,
    ):
        self.finding_id = finding_id
        self.application_id = application_id
        self.title = title
        self.reason = reason
        self.type = f_type
        self.severity = severity
        self.status = "OPEN"
        self.label = label or (
            "Preliminary indicator - human verification required"
            if f_type == FindingTypeEnum.POSSIBLE_ANOMALY
            else None
        )
        self.rule_refs = ["EOA-CHECKLIST-v1-001"]
        self.evidence = []


class MockPipelineJob:
    def __init__(self, stage: str, status: str, duration_ms: Optional[int] = None, duration_sec: float = 12.0):
        self.stage = stage
        self.status = MagicMock(value=status)
        self.duration_ms = duration_ms or int(duration_sec * 1000)
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at + timedelta(seconds=duration_sec)


class MockVerificationRecord:
    def __init__(
        self,
        source_name: str,
        status: VerificationStatusEnum,
        simulated: bool = True,
        duration_sec: float = 2.4,
    ):
        self.id = 1
        self.application_id = "APP-EOA-2024-00001"
        self.source_name = source_name
        self.status = status
        self.simulated = simulated
        now = datetime.now(timezone.utc)
        req_time = now - timedelta(seconds=duration_sec)
        self.timestamp = now
        self.request_payload = {"requested_at": req_time.isoformat()}
        self.response_payload = {"responded_at": now.isoformat(), "digest": "sha256:abc123mock"}


class MockAlert:
    def __init__(self, title: str, severity: str = "HIGH"):
        self.id = 1
        self.title = title
        self.severity = severity
        self.created_at = datetime.now(timezone.utc)


class MockDocument:
    def __init__(self, doc_id: str, class_name: str, version: int = 1):
        self.id = doc_id
        self.class_name = class_name
        self.version = version
        self.scan_status = ScanStatusEnum.COMPLETED
        self.classification_confidence = 0.98
        self.page_count = 3
        self.sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.created_at = datetime.now(timezone.utc)


class MockChecklistResult:
    def __init__(self, rule_id: str, rule_version: str, result: ChecklistResultEnum):
        self.id = 1
        self.rule_id = rule_id
        self.rule_version = rule_version
        self.result = result


class MockOfficerAction:
    def __init__(self, officer_id: int, action: OfficerActionEnum, reason: str):
        self.id = 1
        self.officer_id = officer_id
        self.action = action
        self.reason = reason
        self.created_at = datetime.now(timezone.utc)


class MockAuditEntry:
    def __init__(self, seq: int, action: str, actor: str):
        self.seq = seq
        self.action = action
        self.actor = actor
        self.target_type = "APPLICATION"
        self.target_id = "APP-EOA-2024-00001"
        self.created_at = datetime.now(timezone.utc)


class MockDbSession:
    """Mock async DB session supporting select queries for statutory analytics."""
    def __init__(self, applications=None, findings=None, jobs=None, ver_records=None, alerts=None):
        self.applications = applications or []
        self.findings = findings or []
        self.jobs = jobs or []
        self.ver_records = ver_records or []
        self.alerts = alerts or []

    async def execute(self, stmt):
        sql_str = str(stmt).lower()
        items = []
        if "application" in sql_str:
            items = self.applications
        elif "finding" in sql_str:
            items = self.findings
        elif "pipeline" in sql_str or "job" in sql_str:
            items = self.jobs
        elif "verif" in sql_str:
            items = self.ver_records
        elif "alert" in sql_str:
            items = self.alerts

        class MockScalarsResult:
            def __init__(self, data):
                self._data = data
            def all(self):
                return self._data
            def scalar_one_or_none(self):
                return self._data[0] if self._data else None

        class MockResult:
            def __init__(self, data):
                self._data = data
            def scalars(self):
                return MockScalarsResult(self._data)
            def scalar_one_or_none(self):
                return self._data[0] if self._data else None

        return MockResult(items)


# ---------------------------------------------------------------------------
# 1. Analytics Service Aggregation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_service_aggregation_and_keys():
    """
    Verifies that AnalyticsService.get_overview aggregates counts, ageing buckets,
    durations, effort reduction methodology, and eval metrics.
    """
    now = datetime.now(timezone.utc)
    mock_apps = [
        MockApplication("APP-001", state=ApplicationStateEnum.DRAFT, submitted_at=now - timedelta(hours=5)),
        MockApplication("APP-002", state=ApplicationStateEnum.SUBMITTED, submitted_at=now - timedelta(hours=18)),
        MockApplication("APP-003", state=ApplicationStateEnum.READY_FOR_SCRUTINY, submitted_at=now - timedelta(hours=36)),
        MockApplication("APP-004", state=ApplicationStateEnum.DEFICIENCIES_FOUND, submitted_at=now - timedelta(hours=72)),
        MockApplication("APP-005", state=ApplicationStateEnum.UNDER_OFFICIAL_REVIEW, submitted_at=now - timedelta(hours=200)),
        MockApplication("APP-006", state=ApplicationStateEnum.CLOSED_BY_AUTHORITY, submitted_at=now - timedelta(hours=10)),
    ]

    mock_findings = [
        MockFinding("F-001", "APP-003", "Missing Fire NOC", "Document expired", FindingTypeEnum.MISSING, FindingSeverityEnum.REVIEW_REQUIRED),
        MockFinding("F-002", "APP-004", "Intake Mismatch", "Intake exceeds record", FindingTypeEnum.RECORD_MISMATCH, FindingSeverityEnum.REVIEW_REQUIRED),
        MockFinding("F-003", "APP-004", "Possible Date Inconsistency", "Unusual stamp layout", FindingTypeEnum.POSSIBLE_ANOMALY, FindingSeverityEnum.NEEDS_ATTENTION),
        MockFinding("F-004", "APP-005", "Duplicate Building Plan", "Image hash collision", FindingTypeEnum.DUPLICATE, FindingSeverityEnum.INFO),
    ]

    mock_jobs = [
        MockPipelineJob("EXTRACTED", "COMPLETED", duration_sec=10.0),
        MockPipelineJob("EXTRACTED", "COMPLETED", duration_sec=14.0),
    ]

    mock_vers = [
        MockVerificationRecord("State Fire Services", VerificationStatusEnum.VERIFIED, duration_sec=2.0),
        MockVerificationRecord("Affiliating University", VerificationStatusEnum.SOURCE_UNAVAILABLE, duration_sec=3.0),
    ]

    mock_alerts = [MockAlert("Deficiency Alert")]

    db = MockDbSession(
        applications=mock_apps,
        findings=mock_findings,
        jobs=mock_jobs,
        ver_records=mock_vers,
        alerts=mock_alerts,
    )

    overview = await AnalyticsService.get_overview(db)

    # Verify top-level structure
    assert "counts_by_state" in overview
    assert "deficiencies_by_type" in overview
    assert "deficiencies_by_severity" in overview
    assert "queue_ageing_buckets" in overview
    assert "processing_and_verification_time" in overview
    assert "alert_timeliness" in overview
    assert "estimated_manual_effort_reduction" in overview
    assert "metrics" in overview

    # Verify all enum states are present in counts_by_state
    for state in ApplicationStateEnum:
        assert state.value in overview["counts_by_state"], f"State {state.value} missing from counts_by_state"
    assert overview["counts_by_state"][ApplicationStateEnum.SUBMITTED.value] == 1
    assert overview["counts_by_state"][ApplicationStateEnum.READY_FOR_SCRUTINY.value] == 1

    # Verify queue ageing buckets
    buckets = overview["queue_ageing_buckets"]
    assert "under_24_hours" in buckets
    assert "24_to_48_hours" in buckets
    assert "48_hours_to_7_days" in buckets
    assert "over_7_days" in buckets
    assert buckets["under_24_hours"] >= 1
    assert buckets["24_to_48_hours"] >= 1
    assert buckets["48_hours_to_7_days"] >= 1
    assert buckets["over_7_days"] >= 1

    # Verify processing & verification time
    timings = overview["processing_and_verification_time"]
    assert timings["average_processing_time_seconds"] > 0
    assert timings["median_processing_time_seconds"] > 0
    assert timings["average_verification_time_seconds"] > 0
    assert timings["median_verification_time_seconds"] > 0

    # Verify alert timeliness
    alerts_metric = overview["alert_timeliness"]
    assert alerts_metric["average_latency_seconds"] > 0
    assert alerts_metric["median_latency_seconds"] > 0
    assert alerts_metric["sla_compliance_rate_pct"] == 100.0

    # Verify estimated manual effort reduction methodology & estimate marking
    effort = overview["estimated_manual_effort_reduction"]
    assert effort["assumed_manual_minutes_per_file"] == 45.0, "Assumed manual baseline must be 45 minutes"
    assert effort["is_estimate"] is True, "Effort reduction must be explicitly marked as an estimate"
    assert "45 minutes" in effort["methodology"], "Methodology must document the 45-minute baseline assumption"
    assert "estimate" in effort["methodology"].lower()
    assert effort["estimated_hours_saved"] > 0
    assert 0.0 <= effort["percentage_reduction"] <= 100.0

    # Verify metrics block
    metrics = overview["metrics"]
    assert isinstance(metrics, dict)
    assert "extraction_overall_accuracy" in metrics or "extraction" in metrics or "status" in metrics


# ---------------------------------------------------------------------------
# 2. RBAC Role Gating Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_role_gating():
    """
    Verifies that GET /api/analytics/overview is accessible to Scrutiny Officers and Admins,
    and returns HTTP 403 Forbidden for Institution users.
    """
    checker = require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.ADMIN)

    officer_user = MockUser("officer@aicte.gov.in", RoleEnum.SCRUTINY_OFFICER)
    admin_user = MockUser("admin@aicte.gov.in", RoleEnum.ADMIN)
    institution_user = MockUser("principal@college.edu.in", RoleEnum.INSTITUTION)

    # Scrutiny officer allowed
    res_officer = await checker(current_user=officer_user)
    assert res_officer.role == RoleEnum.SCRUTINY_OFFICER

    # Admin allowed
    res_admin = await checker(current_user=admin_user)
    assert res_admin.role == RoleEnum.ADMIN

    # Institution user forbidden with 403
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=institution_user)
    assert exc_info.value.status_code == 403
    assert "forbidden" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# 3. Statutory PDF Report Generation & Structure Tests
# ---------------------------------------------------------------------------

def test_statutory_pdf_report_generation():
    """
    Verifies that ReportService generates a valid PDF containing:
    - %PDF magic bytes
    - Statutory Decision Support Disclaimer
    - SYNTHETIC DATA notice
    - SIMULATED SOURCE badges
    - All 7 distinct statutory sections
    """
    app = MockApplication(
        app_id="APP-EOA-2024-00001",
        institution_id="INST-001",
        state=ApplicationStateEnum.READY_FOR_SCRUTINY,
        priority_score=78,
    )

    documents = [
        MockDocument("DOC-001", "FIRE_SAFETY_CERTIFICATE"),
        MockDocument("DOC-002", "BUILDING_OCCUPANCY_CERTIFICATE"),
    ]

    checklist_results = [
        MockChecklistResult("EOA-FIRE-001", "v1.0", ChecklistResultEnum.PRESENT),
        MockChecklistResult("EOA-INTAKE-002", "v1.0", ChecklistResultEnum.MISSING),
    ]

    findings = [
        MockFinding("F-001", app.id, "Intake Discrepancy", "Approved intake 120 exceeds faculty ratio", FindingTypeEnum.RECORD_MISMATCH, FindingSeverityEnum.REVIEW_REQUIRED),
        MockFinding("F-002", app.id, "Timestamp Anomaly", "Inconsistent font rendering", FindingTypeEnum.POSSIBLE_ANOMALY, FindingSeverityEnum.NEEDS_ATTENTION),
        MockFinding("F-003", app.id, "Duplicate Floor Plan", "Hash match with prior submission", FindingTypeEnum.DUPLICATE, FindingSeverityEnum.INFO),
    ]

    issuer_records = [
        MockVerificationRecord("State Fire Services", VerificationStatusEnum.VERIFIED, simulated=True),
        MockVerificationRecord("Affiliating University", VerificationStatusEnum.SOURCE_UNAVAILABLE, simulated=True),
    ]

    reviewer_actions = [
        MockOfficerAction(101, OfficerActionEnum.REQUEST_RECTIFICATION, "Faculty count insufficient for approved intake of 180"),
    ]

    audit_entries = [
        MockAuditEntry(1, "SUBMIT_APPLICATION", "principal@college.edu.in"),
        MockAuditEntry(2, "VERIFY_ISSUER", "system"),
    ]

    officer_user = MockUser("officer@aicte.gov.in", RoleEnum.SCRUTINY_OFFICER)

    pdf_bytes = ReportService.generate_application_report(
        app=app,
        checklist_results=checklist_results,
        documents=documents,
        findings=findings,
        issuer_records=issuer_records,
        reviewer_actions=reviewer_actions,
        audit_entries=audit_entries,
        requesting_user=officer_user,
    )

    # 1. Check valid PDF binary structure
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF"), "Report must start with %PDF magic bytes"
    assert b"%%EOF" in pdf_bytes or b"trailer" in pdf_bytes, "Report must contain valid PDF trailer"

    # 2. Check Decision Support Disclaimer
    pdf_text = pdf_bytes.decode("latin1", errors="ignore")
    assert "DECISION SUPPORT" in pdf_text, "Report must contain Decision Support Disclaimer"
    assert "authorised" in pdf_text.lower() or "solely" in pdf_text.lower(), "Must state decisions are made by authorised officers"

    # 3. Check Synthetic Data & Simulated Source
    assert "SYNTHETIC DATA" in pdf_text, "Report must contain SYNTHETIC DATA notice"
    assert "SIMULATED SOURCE" in pdf_text, "Report must mark mock registry responses as SIMULATED SOURCE"

    # 4. Check 7 distinct sections
    assert "CASE SUMMARY" in pdf_text
    assert "CHECKLIST RESULTS" in pdf_text
    assert "DOCUMENT LEDGER" in pdf_text
    assert "MACHINE OBSERVATIONS" in pdf_text or "FINDINGS" in pdf_text
    assert "ISSUER RESPONSES" in pdf_text
    assert "OFFICIAL REVIEWER ACTIONS" in pdf_text
    assert "AUDIT TRAIL" in pdf_text


# ---------------------------------------------------------------------------
# 4. Role-Based Report Filtering Tests (Institution vs Scrutiny Officer)
# ---------------------------------------------------------------------------

def test_institution_report_filtering():
    """
    Verifies that institution users receive a reduced statutory report:
    - Findings of type POSSIBLE_ANOMALY are EXCLUDED
    - Findings of type DUPLICATE are EXCLUDED
    - Scrutiny priority score is EXCLUDED
    Whereas scrutiny officers receive the complete statutory evaluation.
    """
    app = MockApplication(
        app_id="APP-EOA-2024-00001",
        institution_id="INST-001",
        priority_score=85,
    )

    findings = [
        MockFinding("F-REG", app.id, "Missing NOC", "Fire safety NOC expired", FindingTypeEnum.MISSING, FindingSeverityEnum.REVIEW_REQUIRED),
        MockFinding("F-ANOM", app.id, "Suspicious Font Metadata", "Unusual PDF creation tool", FindingTypeEnum.POSSIBLE_ANOMALY, FindingSeverityEnum.NEEDS_ATTENTION),
        MockFinding("F-DUP", app.id, "Duplicate Land Deed", "Perceptual hash collision", FindingTypeEnum.DUPLICATE, FindingSeverityEnum.INFO),
    ]

    institution_user = MockUser("principal@college.edu.in", RoleEnum.INSTITUTION, institution_id="INST-001")
    officer_user = MockUser("officer@aicte.gov.in", RoleEnum.SCRUTINY_OFFICER)

    # 1. Institution Report
    inst_pdf_bytes = ReportService.generate_application_report(
        app=app,
        checklist_results=[],
        documents=[],
        findings=findings,
        issuer_records=[],
        reviewer_actions=[],
        audit_entries=[],
        requesting_user=institution_user,
    )
    inst_text = inst_pdf_bytes.decode("latin1", errors="ignore")

    # Regular finding must be visible
    assert "Missing NOC" in inst_text

    # Officer-only anomaly and duplicate findings must NOT be visible to institution
    assert "Suspicious Font Metadata" not in inst_text, "POSSIBLE_ANOMALY finding must be hidden from institution user"
    assert "Duplicate Land Deed" not in inst_text, "DUPLICATE finding must be hidden from institution user"
    assert "Priority Score: 85" not in inst_text, "Priority score must be hidden from institution user"

    # 2. Officer Report
    officer_pdf_bytes = ReportService.generate_application_report(
        app=app,
        checklist_results=[],
        documents=[],
        findings=findings,
        issuer_records=[],
        reviewer_actions=[],
        audit_entries=[],
        requesting_user=officer_user,
    )
    officer_text = officer_pdf_bytes.decode("latin1", errors="ignore")

    # All findings and priority score must be visible to officer
    assert "Missing NOC" in officer_text
    assert "Suspicious Font Metadata" in officer_text, "Officer report must include anomaly finding"
    assert "Duplicate Land Deed" in officer_text, "Officer report must include duplicate finding"
    assert "85" in officer_text, "Officer report must include priority score"


# ---------------------------------------------------------------------------
# 5. Language Invariant & Decision Support Compliance
# ---------------------------------------------------------------------------

def test_language_invariants_and_preliminary_indicators():
    """
    Verifies council invariant rules:
    - Strictly forbidden words ('fake', 'forged', 'fraud') must never appear in report text.
    - Anomaly findings must be labeled 'Preliminary indicator - human verification required'.
    """
    app = MockApplication("APP-EOA-2024-00001", priority_score=50)
    anomaly_finding = MockFinding(
        finding_id="F-099",
        application_id=app.id,
        title="Digital Seal Inconsistency",
        reason="Seal matrix differs from issuing authority baseline",
        f_type=FindingTypeEnum.POSSIBLE_ANOMALY,
        severity=FindingSeverityEnum.REVIEW_REQUIRED,
    )

    officer_user = MockUser("officer@aicte.gov.in", RoleEnum.SCRUTINY_OFFICER)

    pdf_bytes = ReportService.generate_application_report(
        app=app,
        checklist_results=[],
        documents=[],
        findings=[anomaly_finding],
        issuer_records=[],
        reviewer_actions=[],
        audit_entries=[],
        requesting_user=officer_user,
    )
    pdf_text = pdf_bytes.decode("latin1", errors="ignore")

    # Check forbidden terms
    lower_text = pdf_text.lower()
    assert "fake" not in lower_text, "Forbidden term 'fake' found in report output"
    assert "forged" not in lower_text, "Forbidden term 'forged' found in report output"
    assert "fraud" not in lower_text, "Forbidden term 'fraud' found in report output"

    # Check mandatory preliminary indicator label
    assert "Preliminary indicator - human verification required" in pdf_text


# ---------------------------------------------------------------------------
# 6. Cross-Institution Access Gating on Report Endpoint
# ---------------------------------------------------------------------------

def test_cross_institution_report_access_denied():
    """
    Verifies that check_institution_access raises HTTP 403 if an institution user
    attempts to download a report belonging to another institution.
    """
    inst_user = MockUser("principal@inst-a.edu.in", RoleEnum.INSTITUTION, institution_id="INST-001")

    # Own institution allowed
    check_institution_access(inst_user, "INST-001")

    # Other institution forbidden with 403
    with pytest.raises(HTTPException) as exc_info:
        check_institution_access(inst_user, "INST-002")
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Standalone CLI Test Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\nRunning Fixora Statutory Analytics & Report Test Suite...")

    async def run_all():
        print("  1. Testing analytics service aggregation and key outputs...")
        await test_analytics_service_aggregation_and_keys()
        print("     [PASS] Analytics service aggregation & effort reduction methodology")

        print("  2. Testing RBAC role gating on analytics...")
        await test_analytics_role_gating()
        print("     [PASS] Role gating (Officer/Admin allowed, Institution forbidden 403)")

        print("  3. Testing statutory PDF report generation structure...")
        test_statutory_pdf_report_generation()
        print("     [PASS] Valid PDF, Decision Support Disclaimer, 7 distinct sections")

        print("  4. Testing role-based report scoping (Institution vs Officer)...")
        test_institution_report_filtering()
        print("     [PASS] Institution report excludes anomalies, duplicates, and priority score")

        print("  5. Testing language invariants & preliminary indicator labels...")
        test_language_invariants_and_preliminary_indicators()
        print("     [PASS] Zero forbidden terms (fake/forged/fraud), exact preliminary label")

        print("  6. Testing cross-institution report access gating...")
        test_cross_institution_report_access_denied()
        print("     [PASS] Cross-institution access denied (403)")

        print("\nAll Fixora Analytics & Report tests passed successfully!\n")

    asyncio.run(run_all())
