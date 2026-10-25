"""
Fixora Abstract Verification Adapter
Defines the base interface for statutory external verification mechanisms.
Every adapter returns a normalized VerificationResult.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional

from app.models.enums import VerificationStatusEnum


@dataclass
class VerificationResult:
    """
    Standardized result shape returned by all verification adapters.
    RULES.md:
    status, source_name, method, requested_at, responded_at, returned_fields,
    response_digest, retryable, error_category, simulated, message
    """
    status: VerificationStatusEnum
    source_name: str
    method: str  # e.g., "qr_decode", "digital_signature", "api_registry", "manual_officer"
    requested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    responded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    returned_fields: Dict[str, Any] = field(default_factory=dict)
    response_digest: str = ""
    retryable: bool = False
    error_category: Optional[str] = None  # "timeout", "network_error", "not_supported", "format_mismatch"
    simulated: bool = False  # Every mock response has simulated=True
    message: str = ""
    mismatch_details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.response_digest:
            canonical_json = json.dumps(self.returned_fields or {}, sort_keys=True, separators=(",", ":"), default=str)
            self.response_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if hasattr(self.status, "value") else str(self.status)
        return d


class VerificationAdapter(ABC):
    """
    Abstract interface for external and cryptographic document verification.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the verification source or authority."""
        pass

    @property
    @abstractmethod
    def method(self) -> str:
        """Verification method code."""
        pass

    @abstractmethod
    async def verify(
        self,
        document_bytes: bytes,
        document_metadata: Dict[str, Any],
        extracted_fields: Dict[str, Any],
    ) -> VerificationResult:
        """
        Executes verification and returns a normalized VerificationResult.
        Must never raise unhandled exceptions; return status=SOURCE_UNAVAILABLE or
        MANUAL_REVIEW_REQUIRED with retryable/error_category set.
        """
        pass
