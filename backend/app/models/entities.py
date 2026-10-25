from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    ApplicationStateEnum,
    ChecklistResultEnum,
    EvidenceKindEnum,
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
    OfficerActionEnum,
    PipelineJobStatusEnum,
    RoleEnum,
    RulePackStatusEnum,
    ScanStatusEnum,
    VerificationStatusEnum,
)

# Portable JSON type: JSONB on PostgreSQL, standard JSON elsewhere
JsonType = JSONB().with_variant(JSON(), "sqlite")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(SAEnum(RoleEnum, native_enum=False), nullable=False)
    institution_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    institution = relationship("Institution", back_populates="users")
    assigned_applications = relationship(
        "Application", back_populates="assigned_officer", foreign_keys="Application.assigned_to"
    )
    actions = relationship("OfficerAction", back_populates="officer")


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "1-33276541"
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    pin_code: Mapped[str] = mapped_column(String(10), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    users = relationship("User", back_populates="institution")
    applications = relationship("Application", back_populates="institution")
    ref_record = relationship("RefRecord", back_populates="institution", uselist=False)


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "APP-EOA-2024-00001"
    institution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    checklist_pack_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[ApplicationStateEnum] = mapped_column(
        SAEnum(ApplicationStateEnum, native_enum=False),
        nullable=False,
        default=ApplicationStateEnum.DRAFT,
        index=True,
    )
    priority_score: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    form_data: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)

    # Relationships
    institution = relationship("Institution", back_populates="applications")
    assigned_officer = relationship("User", back_populates="assigned_applications", foreign_keys=[assigned_to])
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    checklist_results = relationship("ChecklistResult", back_populates="application", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="application", cascade="all, delete-orphan")
    verification_records = relationship("VerificationRecord", back_populates="application", cascade="all, delete-orphan")
    officer_actions = relationship("OfficerAction", back_populates="application", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="application", cascade="all, delete-orphan")
    pipeline_jobs = relationship("PipelineJob", back_populates="application", cascade="all, delete-orphan")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "D-001"
    application_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Named "class_name" in Python, mapped to column "class"
    class_name: Mapped[str] = mapped_column("class", String(100), nullable=False)
    file_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scan_status: Mapped[ScanStatusEnum] = mapped_column(
        SAEnum(ScanStatusEnum, native_enum=False), default=ScanStatusEnum.PENDING, nullable=False
    )
    classification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    application = relationship("Application", back_populates="documents")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    verification_records = relationship("VerificationRecord", back_populates="document")


class ExtractedField(Base, TimestampMixin):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bbox: Mapped[Optional[Any]] = mapped_column(JsonType, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    document = relationship("Document", back_populates="extracted_fields")


class ChecklistResult(Base, TimestampMixin):
    __tablename__ = "checklist_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[ChecklistResultEnum] = mapped_column(
        SAEnum(ChecklistResultEnum, native_enum=False), nullable=False
    )
    inputs_ref: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)

    # Relationships
    application = relationship("Application", back_populates="checklist_results")


class Finding(Base):
    """
    Statutory finding entity.
    RULES.md:
    {finding_id, application_id, type, severity, title, reason, evidence:[...], rule_refs:[],
     confidence, label, status:open|confirmed|dismissed|rectification_requested|escalated,
     model_versions:{}, created_at}
    A finding without evidence cannot be saved.
    """
    __tablename__ = "findings"

    finding_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "F-2024-000001"
    application_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[FindingTypeEnum] = mapped_column(
        SAEnum(FindingTypeEnum, native_enum=False), nullable=False, index=True
    )
    severity: Mapped[FindingSeverityEnum] = mapped_column(
        SAEnum(FindingSeverityEnum, native_enum=False), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    rule_refs: Mapped[List[str]] = mapped_column(JsonType, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[FindingStatusEnum] = mapped_column(
        SAEnum(FindingStatusEnum, native_enum=False),
        default=FindingStatusEnum.OPEN,
        nullable=False,
        index=True,
    )
    model_versions: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    application = relationship("Application", back_populates="findings")
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="finding", cascade="all, delete-orphan", lazy="joined"
    )
    actions = relationship("OfficerAction", back_populates="finding")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[EvidenceKindEnum] = mapped_column(
        SAEnum(EvidenceKindEnum, native_enum=False), nullable=False
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bbox: Mapped[Optional[Any]] = mapped_column(JsonType, nullable=True)
    field: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    measure: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    threshold: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    record_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    finding = relationship("Finding", back_populates="evidence")


class VerificationRecord(Base):
    """
    Immutable verification log record.
    RULES.md: verification_records (immutable, new attempt = new row)
    """
    __tablename__ = "verification_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[VerificationStatusEnum] = mapped_column(
        SAEnum(VerificationStatusEnum, native_enum=False), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    request_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    response_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    mismatch_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    performed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    document = relationship("Document", back_populates="verification_records")
    application = relationship("Application", back_populates="verification_records")


class OfficerAction(Base):
    """
    Officer statutory action log.
    RULES.md: confirm, dismiss, request_rectification, escalate, refer_inspection
    (a written reason is mandatory).
    """
    __tablename__ = "officer_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("findings.finding_id", ondelete="SET NULL"), nullable=True, index=True
    )
    officer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    action: Mapped[OfficerActionEnum] = mapped_column(
        SAEnum(OfficerActionEnum, native_enum=False), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # Mandatory non-empty written reason
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Constraints: Reason must not be empty or blank spaces
    __table_args__ = (
        CheckConstraint("length(trim(reason)) > 0", name="ck_officer_action_written_reason_required"),
    )

    # Relationships
    application = relationship("Application", back_populates="officer_actions")
    finding = relationship("Finding", back_populates="actions")
    officer = relationship("User", back_populates="actions")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    role: Mapped[Optional[RoleEnum]] = mapped_column(
        SAEnum(RoleEnum, native_enum=False), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FindingSeverityEnum] = mapped_column(
        SAEnum(FindingSeverityEnum, native_enum=False),
        default=FindingSeverityEnum.INFO,
        nullable=False,
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    application = relationship("Application", back_populates="alerts")


class AuditEntry(Base):
    """
    Cryptographic tamper-evident audit trail.
    Every state change, rule run, source call, officer action and document read writes an audit event.
    RULES.md: SHA-256 chain with seq, payload_hash and prev_hash.
    """
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seq: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_versions: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    model_versions: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class RulePack(Base, TimestampMixin):
    __tablename__ = "rule_packs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "aicte_aph_norms"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[RulePackStatusEnum] = mapped_column(
        SAEnum(RulePackStatusEnum, native_enum=False),
        default=RulePackStatusEnum.DRAFT,
        nullable=False,
    )

    # Relationships
    versions = relationship("RulePackVersion", back_populates="rule_pack", cascade="all, delete-orphan")


class RulePackVersion(Base):
    __tablename__ = "rule_pack_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_pack_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rule_packs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    rules_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="Draft", nullable=False)  # Draft, In review, Approved, Retired
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    rule_pack = relationship("RulePack", back_populates="versions")

    __table_args__ = (
        Index("uq_rule_pack_version", "rule_pack_id", "version", unique=True),
    )


class RefRecord(Base, TimestampMixin):
    """
    Mock AICTE statutory institutional records:
    previous_eoa, approved_programmes_and_intake, faculty_count, ter_payment_status, deficiency_status
    """
    __tablename__ = "ref_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("institutions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    previous_eoa: Mapped[Dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    approved_programmes_and_intake: Mapped[List[Dict[str, Any]]] = mapped_column(
        JsonType, nullable=False, default=list
    )
    faculty_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ter_payment_status: Mapped[str] = mapped_column(String(50), default="PAID", nullable=False)
    deficiency_status: Mapped[str] = mapped_column(String(50), default="NO_DEFICIENCY", nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    institution = relationship("Institution", back_populates="ref_record")


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PipelineJobStatusEnum] = mapped_column(
        SAEnum(PipelineJobStatusEnum, native_enum=False),
        default=PipelineJobStatusEnum.QUEUED,
        nullable=False,
    )
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    application = relationship("Application", back_populates="pipeline_jobs")
