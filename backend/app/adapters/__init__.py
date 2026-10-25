"""Fixora Verification Adapters Package."""

from app.adapters.base import VerificationAdapter, VerificationResult
from app.adapters.mock_issuer_adapter import (
    MockFireDepartmentAdapter,
    MockUniversityAffiliationAdapter,
)
from app.adapters.qr_adapter import QrAdapter
from app.adapters.signature_adapter import SignatureAdapter

__all__ = [
    "VerificationAdapter",
    "VerificationResult",
    "QrAdapter",
    "SignatureAdapter",
    "MockUniversityAffiliationAdapter",
    "MockFireDepartmentAdapter",
]
