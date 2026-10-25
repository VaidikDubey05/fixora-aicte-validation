import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.entities import (
    Application,
    Document,
    Evidence,
    Finding,
    Institution,
    OfficerAction,
    User,
    VerificationRecord,
)
from app.models.enums import (
    ApplicationStateEnum,
    ChecklistResultEnum,
    EvidenceKindEnum,
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
    InfrastructureOutputEnum,
    OfficerActionEnum,
    RoleEnum,
    ScanStatusEnum,
    VerificationStatusEnum,
)
from app.services.repositories import (
    PRELIMINARY_INDICATOR_LABEL,
    ApplicationRepository,
    FindingRepository,
    OfficerActionRepository,
    VerificationRepository,
)


def test_rules_md_exact_vocabulary_enums():
    """Verify exact vocabulary strings specified in RULES.md."""
    # Roles
    assert set(r.value for r in RoleEnum) == {
        "institution",
        "scrutiny_officer",
        "verification_officer",
        "admin",
    }

    # Application states
    assert set(s.value for s in ApplicationStateEnum) == {
        "DRAFT",
        "SUBMITTED",
        "VALIDATION_IN_PROGRESS",
        "DEFICIENCIES_FOUND",
        "RECTIFICATION_REQUESTED",
        "VERIFICATION_PENDING",
        "READY_FOR_SCRUTINY",
        "UNDER_OFFICIAL_REVIEW",
        "REFERRED_FOR_INSPECTION",
        "CLOSED_BY_AUTHORITY",
    }

    # Verification status
    assert set(v.value for v in VerificationStatusEnum) == {
        "VERIFIED",
        "MISMATCH_DETECTED",
        "EXPIRED",
        "VERIFICATION_PENDING",
        "SOURCE_UNAVAILABLE",
        "MANUAL_REVIEW_REQUIRED",
    }

    # Checklist result
    assert set(c.value for c in ChecklistResultEnum) == {
        "PRESENT",
        "MISSING",
        "EXPIRED",
        "INCONSISTENT",
        "VERIFIED",
        "NEEDS_EVIDENCE",
    }

    # Severity
    assert set(sv.value for sv in FindingSeverityEnum) == {
        "info",
        "needs_attention",
        "review_required",
    }

    # Finding types
    assert set(ft.value for ft in FindingTypeEnum) == {
        "missing",
        "incomplete",
        "expired",
        "inconsistent",
        "record_mismatch",
        "possible_anomaly",
        "duplicate",
        "verification",
        "infrastructure",
    }

    # Infrastructure output
    assert set(io.value for io in InfrastructureOutputEnum) == {
        "consistent",
        "needs_additional_evidence",
        "recommend_inspection",
    }

    # Officer actions
    assert set(oa.value for oa in OfficerActionEnum) == {
        "confirm",
        "dismiss",
        "request_rectification",
        "escalate",
        "refer_inspection",
    }


def test_finding_cannot_be_saved_without_evidence():
    """RULES.md Constraint: A finding without evidence cannot be saved."""
    with pytest.raises(ValueError, match="A finding without evidence cannot be saved"):
        FindingRepository.create_finding(
            finding_id="F-2024-000001",
            application_id="APP-EOA-2024-00001",
            type=FindingTypeEnum.MISSING,
            severity=FindingSeverityEnum.REVIEW_REQUIRED,
            title="Missing Occupancy Certificate",
            reason="Mandatory structural document not uploaded.",
            evidence=[],  # Empty evidence must be rejected
        )


def test_finding_with_evidence_and_preliminary_indicator_label():
    """RULES.md Constraint: Anomaly findings carry the label 'Preliminary indicator - human verification required'."""
    evidence_data = [
        {
            "kind": EvidenceKindEnum.REGION,
            "document_id": "D-001",
            "page": 1,
            "bbox": [10, 20, 100, 200],
            "field": "land_area",
            "value": "1.5",
            "measure": "acres",
            "threshold": "2.5",
        }
    ]

    finding = FindingRepository.create_finding(
        finding_id="F-2024-000002",
        application_id="APP-EOA-2024-00001",
        type=FindingTypeEnum.POSSIBLE_ANOMALY,
        severity=FindingSeverityEnum.NEEDS_ATTENTION,
        title="Land Area Variance",
        reason="Discrepancy detected between deed and municipal record.",
        evidence=evidence_data,
    )

    assert finding.finding_id == "F-2024-000002"
    assert len(finding.evidence) == 1
    assert finding.label == PRELIMINARY_INDICATOR_LABEL
    assert finding.evidence[0].kind == EvidenceKindEnum.REGION


def test_finding_institution_visibility_filter():
    """RULES.md Constraint: Institution users never see possible_anomaly or duplicate findings."""
    ev = [{"kind": EvidenceKindEnum.RECORD, "field": "status", "value": "test"}]

    f1 = FindingRepository.create_finding(
        "F-1", "APP-1", FindingTypeEnum.MISSING, FindingSeverityEnum.INFO, "Doc Missing", "Reason", ev
    )
    f2 = FindingRepository.create_finding(
        "F-2", "APP-1", FindingTypeEnum.POSSIBLE_ANOMALY, FindingSeverityEnum.NEEDS_ATTENTION, "Anomaly", "Reason", ev
    )
    f3 = FindingRepository.create_finding(
        "F-3", "APP-1", FindingTypeEnum.DUPLICATE, FindingSeverityEnum.NEEDS_ATTENTION, "Duplicate", "Reason", ev
    )
    f4 = FindingRepository.create_finding(
        "F-4", "APP-1", FindingTypeEnum.EXPIRED, FindingSeverityEnum.REVIEW_REQUIRED, "Expired", "Reason", ev
    )

    all_findings = [f1, f2, f3, f4]

    # For institution role:
    inst_visible = FindingRepository.filter_findings_for_role(all_findings, RoleEnum.INSTITUTION)
    assert len(inst_visible) == 2
    assert {f.type for f in inst_visible} == {FindingTypeEnum.MISSING, FindingTypeEnum.EXPIRED}

    # For scrutiny officer role:
    officer_visible = FindingRepository.filter_findings_for_role(all_findings, RoleEnum.SCRUTINY_OFFICER)
    assert len(officer_visible) == 4


def test_officer_action_mandatory_written_reason():
    """RULES.md Constraint: Officer action requires a mandatory written reason."""
    # Blank / whitespace reasons must fail
    with pytest.raises(ValueError, match="A written reason is mandatory"):
        OfficerActionRepository.create_action(
            application_id="APP-EOA-2024-00001",
            officer_id=1,
            action=OfficerActionEnum.CONFIRM,
            reason="",
        )

    with pytest.raises(ValueError, match="A written reason is mandatory"):
        OfficerActionRepository.create_action(
            application_id="APP-EOA-2024-00001",
            officer_id=1,
            action=OfficerActionEnum.REFER_INSPECTION,
            reason="   ",
        )

    # Valid reason succeeds
    action = OfficerActionRepository.create_action(
        application_id="APP-EOA-2024-00001",
        officer_id=1,
        action=OfficerActionEnum.REFER_INSPECTION,
        reason="Physical verification of laboratory equipment required per APH norms.",
    )
    assert action.reason == "Physical verification of laboratory equipment required per APH norms."
    assert action.action == OfficerActionEnum.REFER_INSPECTION


def test_verification_record_immutability():
    """RULES.md Constraint: verification_records (immutable, new attempt = new row)."""
    rec1 = VerificationRepository.record_verification(
        document_id="D-001",
        application_id="APP-EOA-2024-00001",
        status=VerificationStatusEnum.SOURCE_UNAVAILABLE,
        source_name="LandRecordsAPI",
        simulated=True,
    )
    assert rec1.simulated is True
    assert rec1.status == VerificationStatusEnum.SOURCE_UNAVAILABLE

    # Updating existing verification record must be prevented
    with pytest.raises(NotImplementedError, match="strictly immutable"):
        VerificationRepository.update_verification_record(rec1, status=VerificationStatusEnum.VERIFIED)

    # New attempt = new row
    rec2 = VerificationRepository.record_verification(
        document_id="D-001",
        application_id="APP-EOA-2024-00001",
        status=VerificationStatusEnum.VERIFIED,
        source_name="LandRecordsAPI",
        simulated=True,
    )
    assert rec2 is not rec1
    assert rec2.status == VerificationStatusEnum.VERIFIED


def test_application_automated_vs_officer_state_transitions():
    """RULES.md Constraint: System may move case only up to READY_FOR_SCRUTINY. Later states need officer action."""
    # Automated transitions up to READY_FOR_SCRUTINY are valid
    assert ApplicationRepository.validate_state_transition(
        ApplicationStateEnum.DRAFT, ApplicationStateEnum.SUBMITTED, is_officer_action=False
    )
    assert ApplicationRepository.validate_state_transition(
        ApplicationStateEnum.SUBMITTED, ApplicationStateEnum.READY_FOR_SCRUTINY, is_officer_action=False
    )

    # Automated transition into UNDER_OFFICIAL_REVIEW must fail without officer action
    with pytest.raises(PermissionError, match="requires authenticated officer action"):
        ApplicationRepository.validate_state_transition(
            ApplicationStateEnum.READY_FOR_SCRUTINY,
            ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
            is_officer_action=False,
        )

    # With officer action, it succeeds
    assert ApplicationRepository.validate_state_transition(
        ApplicationStateEnum.READY_FOR_SCRUTINY,
        ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
        is_officer_action=True,
    )


def test_sqlalchemy_models_creation_and_database_persistence():
    """Verifies that all SQLAlchemy 2 mapped tables create cleanly and foreign keys link properly."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Create Institution
        inst = Institution(
            id="1-33276541",
            name="Government Engineering College",
            address="Campus Road, Tech City",
            state="Maharashtra",
            district="Pune",
            pin_code="411001",
            contact_email="principal@gecpune.edu.in",
        )
        session.add(inst)
        session.flush()

        # Create User
        user = User(
            email="scrutiny1@aicte.gov.in",
            hashed_password="pbkdf2_sha256$mock",
            role=RoleEnum.SCRUTINY_OFFICER,
            full_name="Dr. A. K. Sharma",
        )
        session.add(user)
        session.flush()

        # Create Application (ID: APP-EOA-YYYY-NNNNN)
        app = Application(
            id="APP-EOA-2024-00101",
            institution_id=inst.id,
            category="ENGINEERING_AND_TECHNOLOGY",
            academic_year="2024-2025",
            checklist_pack_version="aph-2024-25-v1",
            state=ApplicationStateEnum.SUBMITTED,
            assigned_to=user.id,
            form_data={"programmes": ["Computer Science", "Mechanical"]},
        )
        session.add(app)
        session.flush()

        # Create Document (ID: D-NNN)
        doc = Document(
            id="D-101",
            application_id=app.id,
            class_name="land_title_deed",
            file_ref="/storage/documents/APP-EOA-2024-00101/D-101.pdf",
            sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            page_count=5,
            version=1,
            scan_status=ScanStatusEnum.COMPLETED,
        )
        session.add(doc)
        session.flush()

        # Create Finding with Evidence (ID: F-YYYY-NNNNNN)
        finding = Finding(
            finding_id="F-2024-000101",
            application_id=app.id,
            type=FindingTypeEnum.INCONSISTENT,
            severity=FindingSeverityEnum.REVIEW_REQUIRED,
            title="Land Title vs Municipal Record Discrepancy",
            reason="Plot boundary measurements in deed do not match surveyor registry.",
            rule_refs=["APH-2024-CLAUSE-4.2"],
            confidence=0.94,
            status=FindingStatusEnum.OPEN,
            model_versions={"ocr": "tesseract-5.3", "layout": "v1.2"},
        )
        ev = Evidence(
            finding_id=finding.finding_id,
            kind=EvidenceKindEnum.REGION,
            document_id=doc.id,
            page=2,
            bbox=[50, 100, 300, 450],
            field="survey_number",
            value="Plot 44-B",
        )
        finding.evidence.append(ev)
        session.add(finding)
        session.flush()

        # Create Officer Action with Written Reason
        action = OfficerAction(
            application_id=app.id,
            finding_id=finding.finding_id,
            officer_id=user.id,
            action=OfficerActionEnum.REQUEST_RECTIFICATION,
            reason="Institution requested to submit certified surveyor endorsement.",
        )
        session.add(action)

        # Create Immutable Verification Record
        verif = VerificationRecord(
            document_id=doc.id,
            application_id=app.id,
            status=VerificationStatusEnum.VERIFIED,
            source_name="StateLandRevenuePortal",
            simulated=True,
            performed_by=user.id,
        )
        session.add(verif)

        session.commit()

        # Verify query back
        queried_app = session.get(Application, "APP-EOA-2024-00101")
        assert queried_app is not None
        assert len(queried_app.documents) == 1
        assert len(queried_app.findings) == 1
        assert len(queried_app.findings[0].evidence) == 1
        assert len(queried_app.officer_actions) == 1
        assert queried_app.officer_actions[0].action == OfficerActionEnum.REQUEST_RECTIFICATION
