from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Application,
    Document,
    Evidence,
    Finding,
    OfficerAction,
    VerificationRecord,
)
from app.models.enums import (
    ApplicationStateEnum,
    FindingStatusEnum,
    FindingTypeEnum,
    OfficerActionEnum,
    RoleEnum,
    VerificationStatusEnum,
)

PRELIMINARY_INDICATOR_LABEL = "Preliminary indicator - human verification required"

# States allowed for automated system pipelines without an officer action
AUTOMATED_STATES = {
    ApplicationStateEnum.DRAFT,
    ApplicationStateEnum.SUBMITTED,
    ApplicationStateEnum.VALIDATION_IN_PROGRESS,
    ApplicationStateEnum.DEFICIENCIES_FOUND,
    ApplicationStateEnum.RECTIFICATION_REQUESTED,
    ApplicationStateEnum.VERIFICATION_PENDING,
    ApplicationStateEnum.READY_FOR_SCRUTINY,
}

# States strictly requiring authenticated officer action
OFFICER_GATED_STATES = {
    ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
    ApplicationStateEnum.REFERRED_FOR_INSPECTION,
    ApplicationStateEnum.CLOSED_BY_AUTHORITY,
}


class FindingRepository:
    """
    Statutory Finding Repository.
    RULES.md Constraints:
    - A finding without evidence cannot be saved.
    - Anomaly findings carry the label "Preliminary indicator - human verification required".
    - Institution users never see possible_anomaly or duplicate findings.
    """

    @staticmethod
    def create_finding(
        finding_id: str,
        application_id: str,
        type: FindingTypeEnum,
        severity: Any,
        title: str,
        reason: str,
        evidence: List[Dict[str, Any]],
        rule_refs: Optional[List[str]] = None,
        confidence: float = 1.0,
        label: Optional[str] = None,
        status: FindingStatusEnum = FindingStatusEnum.OPEN,
        model_versions: Optional[Dict[str, Any]] = None,
    ) -> Finding:
        if not evidence or len(evidence) == 0:
            raise ValueError("A finding without evidence cannot be saved.")

        # Anomaly findings carry standard statutory caveat label
        if type == FindingTypeEnum.POSSIBLE_ANOMALY and not label:
            label = PRELIMINARY_INDICATOR_LABEL

        finding = Finding(
            finding_id=finding_id,
            application_id=application_id,
            type=type,
            severity=severity,
            title=title,
            reason=reason,
            rule_refs=rule_refs or [],
            confidence=confidence,
            label=label,
            status=status,
            model_versions=model_versions or {},
            created_at=datetime.now(timezone.utc),
        )

        for ev_data in evidence:
            ev = Evidence(
                finding_id=finding_id,
                kind=ev_data["kind"],
                document_id=ev_data.get("document_id"),
                page=ev_data.get("page"),
                bbox=ev_data.get("bbox"),
                field=ev_data.get("field"),
                value=ev_data.get("value"),
                measure=ev_data.get("measure"),
                threshold=ev_data.get("threshold"),
                record_ref=ev_data.get("record_ref"),
                created_at=datetime.now(timezone.utc),
            )
            finding.evidence.append(ev)

        return finding

    @staticmethod
    def filter_findings_for_role(findings: List[Finding], role: RoleEnum) -> List[Finding]:
        """
        Visibility constraint from RULES.md:
        Institution users never see possible_anomaly or duplicate findings,
        review priority scores or internal notes. They see deficiencies in plain language.
        """
        if role == RoleEnum.INSTITUTION:
            hidden_types = {FindingTypeEnum.POSSIBLE_ANOMALY, FindingTypeEnum.DUPLICATE}
            return [f for f in findings if f.type not in hidden_types]
        return findings


class OfficerActionRepository:
    """
    Statutory Officer Action Repository.
    RULES.md Constraints:
    - Officer action: confirm, dismiss, request_rectification, escalate, refer_inspection.
    - A written reason is mandatory.
    """

    @staticmethod
    def create_action(
        application_id: str,
        officer_id: int,
        action: OfficerActionEnum,
        reason: str,
        finding_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> OfficerAction:
        if not reason or not reason.strip():
            raise ValueError("A written reason is mandatory for any officer action.")

        return OfficerAction(
            application_id=application_id,
            officer_id=officer_id,
            action=action,
            reason=reason.strip(),
            finding_id=finding_id,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )


class VerificationRepository:
    """
    Statutory Verification Repository.
    RULES.md Constraints:
    - verification_records (immutable, new attempt = new row)
    - Mock integrations return simulated=true
    """

    @staticmethod
    def record_verification(
        document_id: str,
        application_id: str,
        status: VerificationStatusEnum,
        source_name: str,
        simulated: bool = True,
        request_payload: Optional[Dict[str, Any]] = None,
        response_payload: Optional[Dict[str, Any]] = None,
        mismatch_details: Optional[Dict[str, Any]] = None,
        performed_by: Optional[int] = None,
    ) -> VerificationRecord:
        return VerificationRecord(
            document_id=document_id,
            application_id=application_id,
            status=status,
            source_name=source_name,
            simulated=simulated,
            request_payload=request_payload,
            response_payload=response_payload,
            mismatch_details=mismatch_details,
            performed_by=performed_by,
            timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def update_verification_record(*args, **kwargs):
        """Immutability enforcement."""
        raise NotImplementedError(
            "Verification records are strictly immutable. Record a new attempt instead."
        )


class ApplicationRepository:
    """
    Application State Governance.
    RULES.md Constraints:
    - The system may move a case only among the automated states up to READY_FOR_SCRUTINY.
    - UNDER_OFFICIAL_REVIEW and later need an authenticated officer action.
    """

    @staticmethod
    def validate_state_transition(
        current_state: ApplicationStateEnum,
        new_state: ApplicationStateEnum,
        is_officer_action: bool = False,
    ) -> bool:
        if new_state in OFFICER_GATED_STATES and not is_officer_action:
            raise PermissionError(
                f"Transition to statutory officer state '{new_state.value}' requires authenticated officer action."
            )
        return True
