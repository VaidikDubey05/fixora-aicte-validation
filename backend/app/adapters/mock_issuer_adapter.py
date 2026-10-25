"""
Fixora Mock Issuer Adapters
Implements deterministic statutory verification against external authority mock endpoints:
1. MockUniversityAffiliationAdapter (affiliating state technical university registry)
2. MockFireDepartmentAdapter (state fire prevention & safety services department)

Rules:
- Every response sets simulated=True
- Covers all 6 statuses: VERIFIED, MISMATCH_DETECTED, EXPIRED, VERIFICATION_PENDING,
  SOURCE_UNAVAILABLE, MANUAL_REVIEW_REQUIRED
- Exponential backoff retry simulation (max 3 retries) before routing to manual queue
- A source outage must NEVER create an adverse finding
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Optional

from app.adapters.base import VerificationAdapter, VerificationResult
from app.models.enums import VerificationStatusEnum


class BaseMockIssuerAdapter(VerificationAdapter):
    """Base class for mock external statutory authority adapters with retry tracking."""

    @property
    def method(self) -> str:
        return "api_registry_lookup"

    def _generate_digest(self, payload: Dict[str, Any]) -> str:
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class MockUniversityAffiliationAdapter(BaseMockIssuerAdapter):
    """
    Simulated University Affiliation Board API.
    Validates institution affiliation status, approved intake, and academic validity period.
    """

    @property
    def source_name(self) -> str:
        return "state_technical_university_registry"

    async def verify(
        self,
        document_bytes: bytes,
        document_metadata: Dict[str, Any],
        extracted_fields: Dict[str, Any],
        simulate_status: Optional[VerificationStatusEnum] = None,
        attempt: int = 1,
    ) -> VerificationResult:
        requested_at = datetime.now(timezone.utc).isoformat()
        inst_id = document_metadata.get("institution_id") or extracted_fields.get("institution_id", "")
        inst_name = document_metadata.get("institution_name") or extracted_fields.get("institution_name", "")

        # Test hook to force specific status or simulate timeouts
        if simulate_status == VerificationStatusEnum.SOURCE_UNAVAILABLE:
            if attempt < 3:
                # Exponential backoff simulation: wait 2^(attempt-1) * 10ms for unit tests
                await asyncio.sleep(0.01 * (2 ** (attempt - 1)))
                return VerificationResult(
                    status=VerificationStatusEnum.SOURCE_UNAVAILABLE,
                    source_name=self.source_name,
                    method=self.method,
                    requested_at=requested_at,
                    responded_at=datetime.now(timezone.utc).isoformat(),
                    returned_fields={"attempt": attempt, "max_retries": 3},
                    retryable=True,
                    error_category="timeout",
                    simulated=True,
                    message="Affiliating University API gateway timed out. Request is retryable.",
                )
            else:
                # After 3 failed retries, route to manual review queue
                return VerificationResult(
                    status=VerificationStatusEnum.MANUAL_REVIEW_REQUIRED,
                    source_name=self.source_name,
                    method=self.method,
                    requested_at=requested_at,
                    responded_at=datetime.now(timezone.utc).isoformat(),
                    returned_fields={"attempt": attempt, "max_retries": 3, "final_fallback": "manual_review"},
                    retryable=False,
                    error_category="timeout_exhausted",
                    simulated=True,
                    message=(
                        "External registry connection timed out after 3 retries. "
                        "A source outage is not an adverse conclusion. Document routed to manual review queue."
                    ),
                )

        if simulate_status == VerificationStatusEnum.VERIFICATION_PENDING:
            return VerificationResult(
                status=VerificationStatusEnum.VERIFICATION_PENDING,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"queue_position": 14, "expected_wait_hours": 24},
                retryable=True,
                simulated=True,
                message="External university affiliation verification request submitted and pending processing by registrar.",
            )

        if simulate_status == VerificationStatusEnum.EXPIRED:
            return VerificationResult(
                status=VerificationStatusEnum.EXPIRED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"affiliation_valid_until": "2023-06-30"},
                simulated=True,
                message="External registry records indicate university affiliation expired on 2023-06-30.",
            )

        if simulate_status == VerificationStatusEnum.MISMATCH_DETECTED:
            return VerificationResult(
                status=VerificationStatusEnum.MISMATCH_DETECTED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"approved_intake": 120, "declared_intake": 240},
                mismatch_details=[{"field": "intake", "expected": 120, "found": 240, "label": "Preliminary indicator - human verification required"}],
                simulated=True,
                message="Discrepancy detected between university registry intake and declared application intake.",
            )

        if simulate_status == VerificationStatusEnum.MANUAL_REVIEW_REQUIRED:
            return VerificationResult(
                status=VerificationStatusEnum.MANUAL_REVIEW_REQUIRED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={},
                simulated=True,
                message="Ambiguous registry response. Document routed to officer manual review queue.",
            )

        if simulate_status == VerificationStatusEnum.VERIFIED:
            return VerificationResult(
                status=VerificationStatusEnum.VERIFIED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"affiliation_status": "ACTIVE", "valid_until": "2026-06-30"},
                simulated=True,
                message="University affiliation confirmed active in state technical university registry.",
            )

        # Deterministic resolution from synthetic archetypes
        app_id = document_metadata.get("application_id", "")

        # Archetype 3: Swapped institution / mismatch
        if "MISMATCH" in app_id or "003" in app_id or "St. Peters" in inst_name:
            returned = {
                "institution_id": inst_id,
                "registered_name": "Karnataka Institute of Technology & Management, Bengaluru",
                "declared_name": inst_name,
                "approved_intake": 120,
                "applied_intake": 360,
                "affiliation_status": "PROVISIONAL",
                "valid_till": "2024-05-31",
            }
            return VerificationResult(
                status=VerificationStatusEnum.MISMATCH_DETECTED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields=returned,
                response_digest=self._generate_digest(returned),
                retryable=False,
                simulated=True,
                message="University records state approved intake is 120 vs applied intake of 360 without sanction.",
                mismatch_details={"field": "intake", "expected": 120, "found": 360},
            )

        # Archetype 2: Expired affiliation
        if "EXPIRED" in app_id or "002" in app_id:
            returned = {
                "institution_id": inst_id,
                "registered_name": inst_name,
                "affiliation_status": "EXPIRED",
                "expiry_date": "2023-06-30",
            }
            return VerificationResult(
                status=VerificationStatusEnum.EXPIRED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields=returned,
                response_digest=self._generate_digest(returned),
                retryable=False,
                simulated=True,
                message="University affiliation expired on 2023-06-30.",
            )

        # Standard clean verified response
        returned = {
            "institution_id": inst_id,
            "registered_name": inst_name,
            "affiliation_status": "ACTIVE_AFFILIATION",
            "academic_year": "2024-2025",
            "autonomous_status": False,
            "valid_till": "2025-06-30",
        }
        return VerificationResult(
            status=VerificationStatusEnum.VERIFIED,
            source_name=self.source_name,
            method=self.method,
            requested_at=requested_at,
            responded_at=datetime.now(timezone.utc).isoformat(),
            returned_fields=returned,
            response_digest=self._generate_digest(returned),
            retryable=False,
            simulated=True,
            message="Institutional affiliation successfully verified in state technical university registry.",
        )


class MockFireDepartmentAdapter(BaseMockIssuerAdapter):
    """
    Simulated State Fire Prevention & Safety Department API.
    Validates Fire Safety Certificate / NOC issuance, validity dates, and building clearance.
    """

    @property
    def source_name(self) -> str:
        return "state_fire_prevention_services_registry"

    async def verify(
        self,
        document_bytes: bytes,
        document_metadata: Dict[str, Any],
        extracted_fields: Dict[str, Any],
        simulate_status: Optional[VerificationStatusEnum] = None,
        attempt: int = 1,
    ) -> VerificationResult:
        requested_at = datetime.now(timezone.utc).isoformat()
        cert_no = extracted_fields.get("certificate_number") or extracted_fields.get("fire_safety_certificate.certificate_number", "")
        expiry_date = extracted_fields.get("expiry_date") or extracted_fields.get("fire_safety_certificate.expiry_date", "")

        # Test hook to force specific status or simulate timeouts
        if simulate_status == VerificationStatusEnum.SOURCE_UNAVAILABLE:
            if attempt < 3:
                await asyncio.sleep(0.01 * (2 ** (attempt - 1)))
                return VerificationResult(
                    status=VerificationStatusEnum.SOURCE_UNAVAILABLE,
                    source_name=self.source_name,
                    method=self.method,
                    requested_at=requested_at,
                    responded_at=datetime.now(timezone.utc).isoformat(),
                    returned_fields={"attempt": attempt, "max_retries": 3},
                    retryable=True,
                    error_category="timeout",
                    simulated=True,
                    message="State Fire Services API is temporarily unreachable. Request is retryable.",
                )
            else:
                return VerificationResult(
                    status=VerificationStatusEnum.MANUAL_REVIEW_REQUIRED,
                    source_name=self.source_name,
                    method=self.method,
                    requested_at=requested_at,
                    responded_at=datetime.now(timezone.utc).isoformat(),
                    returned_fields={"attempt": attempt, "max_retries": 3, "final_fallback": "manual_review"},
                    retryable=False,
                    error_category="timeout_exhausted",
                    simulated=True,
                    message=(
                        "Fire Services registry connection timed out after 3 retries. "
                        "A source outage is not an adverse conclusion. Document routed to manual review queue."
                    ),
                )

        if simulate_status == VerificationStatusEnum.VERIFICATION_PENDING:
            return VerificationResult(
                status=VerificationStatusEnum.VERIFICATION_PENDING,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"service_ticket": "FIRE-REG-88192"},
                retryable=True,
                simulated=True,
                message="Fire safety clearance inspection verification ticket is pending divisional officer signoff.",
            )

        if simulate_status == VerificationStatusEnum.EXPIRED:
            return VerificationResult(
                status=VerificationStatusEnum.EXPIRED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"fire_safety_valid_until": "2023-12-31"},
                simulated=True,
                message="State Fire Services records indicate certificate expired on 2023-12-31.",
            )

        if simulate_status == VerificationStatusEnum.MISMATCH_DETECTED:
            return VerificationResult(
                status=VerificationStatusEnum.MISMATCH_DETECTED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"registered_floors": 3, "declared_floors": 5},
                mismatch_details=[{"field": "floors", "expected": 3, "found": 5, "label": "Preliminary indicator - human verification required"}],
                simulated=True,
                message="Discrepancy detected between fire clearance certificate and building plan declaration.",
            )

        if simulate_status == VerificationStatusEnum.MANUAL_REVIEW_REQUIRED:
            return VerificationResult(
                status=VerificationStatusEnum.MANUAL_REVIEW_REQUIRED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={},
                simulated=True,
                message="Fire Services registry response unconfirmed. Routed to manual review queue.",
            )

        if simulate_status == VerificationStatusEnum.VERIFIED:
            return VerificationResult(
                status=VerificationStatusEnum.VERIFIED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields={"noc_status": "APPROVED", "valid_until": "2026-12-31"},
                simulated=True,
                message="Fire safety certificate confirmed active in State Fire Services portal.",
            )

        app_id = document_metadata.get("application_id", "")

        # Archetype 2: Fire safety certificate expired
        if "EXPIRED" in app_id or "002" in app_id or (expiry_date and expiry_date < "2024-01-01"):
            returned = {
                "certificate_number": cert_no,
                "status": "EXPIRED",
                "issue_date": "2022-12-01",
                "expiry_date": "2023-11-30",
                "cleared_blocks": ["Main Block"],
            }
            return VerificationResult(
                status=VerificationStatusEnum.EXPIRED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields=returned,
                response_digest=self._generate_digest(returned),
                retryable=False,
                simulated=True,
                message="Fire Safety Certificate record in state registry expired on 2023-11-30.",
            )

        # Archetype 4 or altered: Certificate number not recognized in registry
        if "ALTERED" in app_id or "004" in app_id or "UNKNOWN" in cert_no:
            returned = {
                "certificate_number": cert_no,
                "status": "RECORD_NOT_FOUND",
            }
            return VerificationResult(
                status=VerificationStatusEnum.MISMATCH_DETECTED,
                source_name=self.source_name,
                method=self.method,
                requested_at=requested_at,
                responded_at=datetime.now(timezone.utc).isoformat(),
                returned_fields=returned,
                response_digest=self._generate_digest(returned),
                retryable=False,
                simulated=True,
                message="Certificate identifier does not exist in State Fire Services portal registry.",
                mismatch_details={"field": "certificate_number", "status": "NOT_FOUND"},
            )

        # Standard verified fire certificate
        returned = {
            "certificate_number": cert_no or "FIRE/NOC/2024/0912",
            "status": "VALID",
            "issue_date": "2023-08-01",
            "expiry_date": "2025-07-31",
            "building_height_meters": 18.5,
            "fire_fighting_arrangements": "SATISFACTORY",
        }
        return VerificationResult(
            status=VerificationStatusEnum.VERIFIED,
            source_name=self.source_name,
            method=self.method,
            requested_at=requested_at,
            responded_at=datetime.now(timezone.utc).isoformat(),
            returned_fields=returned,
            response_digest=self._generate_digest(returned),
            retryable=False,
            simulated=True,
            message="Fire safety certificate validated against state fire prevention services registry.",
        )
