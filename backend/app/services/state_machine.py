from typing import Any, Dict, List, Optional, Set
from app.models.enums import ApplicationStateEnum, RoleEnum

OFFICER_ROLES: Set[RoleEnum] = {
    RoleEnum.SCRUTINY_OFFICER,
    RoleEnum.VERIFICATION_OFFICER,
    RoleEnum.ADMIN,
}

# Explicit statutory state transitions graph
ALLOWED_TRANSITIONS: Dict[ApplicationStateEnum, List[ApplicationStateEnum]] = {
    ApplicationStateEnum.DRAFT: [
        ApplicationStateEnum.SUBMITTED,
    ],
    ApplicationStateEnum.SUBMITTED: [
        ApplicationStateEnum.VALIDATION_IN_PROGRESS,
    ],
    ApplicationStateEnum.VALIDATION_IN_PROGRESS: [
        ApplicationStateEnum.DEFICIENCIES_FOUND,
        ApplicationStateEnum.RECTIFICATION_REQUESTED,
        ApplicationStateEnum.VERIFICATION_PENDING,
        ApplicationStateEnum.READY_FOR_SCRUTINY,
    ],
    ApplicationStateEnum.DEFICIENCIES_FOUND: [
        ApplicationStateEnum.RECTIFICATION_REQUESTED,
    ],
    ApplicationStateEnum.RECTIFICATION_REQUESTED: [
        ApplicationStateEnum.SUBMITTED,
    ],
    ApplicationStateEnum.VERIFICATION_PENDING: [
        ApplicationStateEnum.READY_FOR_SCRUTINY,
        ApplicationStateEnum.DEFICIENCIES_FOUND,
    ],
    ApplicationStateEnum.READY_FOR_SCRUTINY: [
        ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
    ],
    ApplicationStateEnum.UNDER_OFFICIAL_REVIEW: [
        ApplicationStateEnum.REFERRED_FOR_INSPECTION,
        ApplicationStateEnum.CLOSED_BY_AUTHORITY,
        ApplicationStateEnum.RECTIFICATION_REQUESTED,
    ],
    ApplicationStateEnum.REFERRED_FOR_INSPECTION: [
        ApplicationStateEnum.CLOSED_BY_AUTHORITY,
        ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
    ],
    ApplicationStateEnum.CLOSED_BY_AUTHORITY: [],
}

OFFICER_GATED_TARGET_STATES: Set[ApplicationStateEnum] = {
    ApplicationStateEnum.UNDER_OFFICIAL_REVIEW,
    ApplicationStateEnum.REFERRED_FOR_INSPECTION,
    ApplicationStateEnum.CLOSED_BY_AUTHORITY,
}


class IllegalStateTransitionError(ValueError):
    """Raised when an illegal or unauthorized statutory state transition is attempted."""
    pass


class ApplicationStateMachine:
    """
    Statutory Application State Machine helper.
    Validates legal transitions, automated boundary constraints, and officer gating.
    """

    def can_transition(self, current: ApplicationStateEnum, target: ApplicationStateEnum) -> bool:
        return target in ALLOWED_TRANSITIONS.get(current, [])

    def transition(
        self,
        current: ApplicationStateEnum,
        target: ApplicationStateEnum,
        is_automated: bool = True,
        officer_role: Optional[RoleEnum] = None,
        reason: Optional[str] = None,
    ) -> ApplicationStateEnum:
        if not self.can_transition(current, target):
            raise IllegalStateTransitionError(
                f"Illegal transition from '{current.value}' to '{target.value}'. "
                f"Allowed: {[s.value for s in ALLOWED_TRANSITIONS.get(current, [])]}"
            )
        if target in OFFICER_GATED_TARGET_STATES:
            if is_automated:
                raise IllegalStateTransitionError(
                    f"Automated system cannot transition into officer-gated state '{target.value}'."
                )
            if officer_role not in OFFICER_ROLES:
                raise IllegalStateTransitionError(
                    f"Role '{officer_role.value if officer_role else 'None'}' is unauthorized for transition to '{target.value}'."
                )
            if not reason or not reason.strip():
                raise ValueError("Officer gating requires a non-empty written reason")
        return target


class StateMachineService:
    """
    Statutory Application State Machine Service.
    Strictly enforces legal transitions and officer gating for API endpoints.
    """

    @staticmethod
    def validate_transition(
        current_state: ApplicationStateEnum,
        target_state: ApplicationStateEnum,
        user: Any,
    ) -> bool:
        sm = ApplicationStateMachine()
        user_role = getattr(user, "role", None)
        try:
            sm.transition(
                current_state,
                target_state,
                is_automated=False,
                officer_role=user_role,
                reason="State change validation",
            )
            return True
        except (IllegalStateTransitionError, ValueError) as e:
            if target_state in OFFICER_GATED_TARGET_STATES and user_role not in OFFICER_ROLES:
                raise PermissionError(str(e))
            raise ValueError(str(e))
