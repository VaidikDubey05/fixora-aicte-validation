"""
Fixora Officer Statutory Actions Schemas
"""

from typing import Optional
try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            # Run field validation on instantiation
            if hasattr(self, "reason"):
                self.reason = self.__class__.validate_reason_non_empty(self.reason)
            if hasattr(self, "notes") and hasattr(self.__class__, "validate_notes_non_empty"):
                self.notes = self.__class__.validate_notes_non_empty(self.notes)

    def Field(default=..., **kwargs):
        return default

    def field_validator(*args, **kwargs):
        def dec(f):
            return f
        return dec

from app.models.enums import OfficerActionEnum


class OfficerActionRequest(BaseModel):
    action: OfficerActionEnum = Field(..., description="Statutory officer action to perform")
    reason: str = Field(..., description="Mandatory non-empty written justification")
    notes: Optional[str] = Field(None, description="Optional internal notes")

    @field_validator("reason")
    @classmethod
    def validate_reason_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("A non-empty written reason is mandatory for all officer statutory actions.")
        return v.strip()


class ManualVerificationRequest(BaseModel):
    outcome: str = Field(..., description="Manual determination: VERIFIED, MISMATCH_DETECTED, or EXPIRED")
    notes: str = Field(..., description="Mandatory written determination notes")
    evidence_file_id: Optional[str] = Field(None, description="Optional document ID of uploaded verification evidence")

    @field_validator("notes")
    @classmethod
    def validate_notes_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Determination notes are mandatory for manual officer confirmation.")
        return v.strip()
