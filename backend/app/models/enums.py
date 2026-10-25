from enum import Enum


class RoleEnum(str, Enum):
    INSTITUTION = "institution"
    SCRUTINY_OFFICER = "scrutiny_officer"
    VERIFICATION_OFFICER = "verification_officer"
    ADMIN = "admin"


class ApplicationStateEnum(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATION_IN_PROGRESS = "VALIDATION_IN_PROGRESS"
    DEFICIENCIES_FOUND = "DEFICIENCIES_FOUND"
    RECTIFICATION_REQUESTED = "RECTIFICATION_REQUESTED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    READY_FOR_SCRUTINY = "READY_FOR_SCRUTINY"
    UNDER_OFFICIAL_REVIEW = "UNDER_OFFICIAL_REVIEW"
    REFERRED_FOR_INSPECTION = "REFERRED_FOR_INSPECTION"
    CLOSED_BY_AUTHORITY = "CLOSED_BY_AUTHORITY"


class VerificationStatusEnum(str, Enum):
    VERIFIED = "VERIFIED"
    MISMATCH_DETECTED = "MISMATCH_DETECTED"
    EXPIRED = "EXPIRED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class ChecklistResultEnum(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    EXPIRED = "EXPIRED"
    INCONSISTENT = "INCONSISTENT"
    VERIFIED = "VERIFIED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"


class FindingSeverityEnum(str, Enum):
    INFO = "info"
    NEEDS_ATTENTION = "needs_attention"
    REVIEW_REQUIRED = "review_required"


class FindingTypeEnum(str, Enum):
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    EXPIRED = "expired"
    INCONSISTENT = "inconsistent"
    RECORD_MISMATCH = "record_mismatch"
    POSSIBLE_ANOMALY = "possible_anomaly"
    DUPLICATE = "duplicate"
    VERIFICATION = "verification"
    INFRASTRUCTURE = "infrastructure"


class InfrastructureOutputEnum(str, Enum):
    CONSISTENT = "consistent"
    NEEDS_ADDITIONAL_EVIDENCE = "needs_additional_evidence"
    RECOMMEND_INSPECTION = "recommend_inspection"


class OfficerActionEnum(str, Enum):
    CONFIRM = "confirm"
    DISMISS = "dismiss"
    REQUEST_RECTIFICATION = "request_rectification"
    ESCALATE = "escalate"
    REFER_INSPECTION = "refer_inspection"


class FindingStatusEnum(str, Enum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    RECTIFICATION_REQUESTED = "rectification_requested"
    ESCALATED = "escalated"


class EvidenceKindEnum(str, Enum):
    REGION = "region"
    RECORD = "record"
    METADATA = "metadata"
    SOURCE = "source"
    RULE = "rule"


class ScanStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RulePackStatusEnum(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class PipelineJobStatusEnum(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
