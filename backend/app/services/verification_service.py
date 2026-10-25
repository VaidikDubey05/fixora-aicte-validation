"""
Fixora Verification Service
Orchestrates document verification profiles across priority adapters,
enforces exponential backoff retry policies, guarantees audit logging,
and preserves strict immutability (new attempt = new verification_records row).
"""

import asyncio
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload
    from app.models.entities import Document, VerificationRecord
    HAS_SQLALCHEMY = True
except ImportError:
    select = None
    AsyncSession = Any  # type: ignore
    selectinload = None
    Document = None  # type: ignore
    VerificationRecord = None  # type: ignore
    HAS_SQLALCHEMY = False

from app.adapters.base import VerificationAdapter, VerificationResult
from app.adapters.mock_issuer_adapter import (
    MockFireDepartmentAdapter,
    MockUniversityAffiliationAdapter,
)
from app.adapters.qr_adapter import QrAdapter
from app.adapters.signature_adapter import SignatureAdapter
from app.core.logging import logger
from app.models.enums import ScanStatusEnum, VerificationStatusEnum
from app.services.audit import AuditService
from app.services.storage import storage_service


class VerificationService:
    """
    Manages document verification profiles and asynchronous execution.
    """

    # Priority order mapping of document classes to verification adapters
    VERIFICATION_PROFILES: Dict[str, List[VerificationAdapter]] = {
        "accreditation_certificate": [QrAdapter(), MockUniversityAffiliationAdapter()],
        "fire_safety_certificate": [MockFireDepartmentAdapter(), SignatureAdapter()],
        "affidavit": [SignatureAdapter()],
        "building_occupancy_certificate": [SignatureAdapter(), MockUniversityAffiliationAdapter()],
        "land_title_deed": [SignatureAdapter()],
    }

    @classmethod
    def get_profile_adapters(cls, document_class: str) -> List[VerificationAdapter]:
        """Returns ordered list of verification adapters for a given document class."""
        clean_cls = document_class.lower().strip()
        return cls.VERIFICATION_PROFILES.get(clean_cls, [SignatureAdapter()])

    @classmethod
    async def verify_document(
        cls,
        db: AsyncSession,
        document_id: str,
        performed_by_user_id: Optional[int] = None,
        force_adapter: Optional[str] = None,
        simulate_status: Optional[VerificationStatusEnum] = None,
    ) -> Dict[str, Any]:
        """
        Executes the verification profile for a document in priority order.
        Inserts an immutable VerificationRecord row per attempt.
        Never updates historical attempts.
        """
        stmt = (
            select(Document)
            .options(selectinload(Document.extracted_fields))
            .where(Document.id == document_id)
        )
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        # Read document file bytes
        try:
            doc_bytes = storage_service.read_decrypted_document(doc.file_ref)
        except Exception as e:
            logger.error(f"Cannot read document {doc.id} for verification: {e}")
            doc_bytes = b""

        # Build extracted fields map
        fields_map = {}
        for ef in doc.extracted_fields:
            fields_map[ef.name] = ef.normalized_value or ef.raw_value
            fields_map[f"{doc.class_name}.{ef.name}"] = ef.normalized_value or ef.raw_value

        doc_metadata = {
            "document_id": doc.id,
            "application_id": doc.application_id,
            "document_class": doc.class_name,
            "file_name": doc.file_ref,
            "sha256": doc.sha256,
        }

        adapters = cls.get_profile_adapters(doc.class_name)
        if force_adapter:
            adapters = [a for a in adapters if force_adapter.lower() in a.source_name.lower() or force_adapter.lower() in a.method.lower()] or adapters

        final_result: Optional[VerificationResult] = None

        # Execute adapters in priority sequence
        for adapter in adapters:
            attempt = 1
            max_retries = 3

            while attempt <= max_retries:
                # Call adapter with timeout / retry simulation
                if isinstance(adapter, (MockUniversityAffiliationAdapter, MockFireDepartmentAdapter)):
                    result = await adapter.verify(
                        document_bytes=doc_bytes,
                        document_metadata=doc_metadata,
                        extracted_fields=fields_map,
                        simulate_status=simulate_status,
                        attempt=attempt,
                    )
                else:
                    result = await adapter.verify(
                        document_bytes=doc_bytes,
                        document_metadata=doc_metadata,
                        extracted_fields=fields_map,
                    )

                # If retryable source outage, backoff and retry up to max_retries
                if result.status == VerificationStatusEnum.SOURCE_UNAVAILABLE and result.retryable and attempt < max_retries:
                    attempt += 1
                    await asyncio.sleep(0.01 * (2 ** (attempt - 1)))
                    continue

                final_result = result
                break

            # If adapter verified, detected mismatch, or expired, we don't need lower-priority fallback
            if final_result and final_result.status in (
                VerificationStatusEnum.VERIFIED,
                VerificationStatusEnum.MISMATCH_DETECTED,
                VerificationStatusEnum.EXPIRED,
            ):
                break

        if not final_result:
            final_result = VerificationResult(
                status=VerificationStatusEnum.MANUAL_REVIEW_REQUIRED,
                source_name="verification_orchestrator",
                method="system_fallback",
                message="No verification adapter was able to definitively verify the document. Routed to manual review queue.",
                simulated=False,
            )

        # Ensure source outages NEVER create an adverse conclusion
        if final_result.status == VerificationStatusEnum.SOURCE_UNAVAILABLE:
            final_result.status = VerificationStatusEnum.MANUAL_REVIEW_REQUIRED
            final_result.message = (
                f"Source '{final_result.source_name}' was unavailable. "
                "A source outage is not an adverse conclusion. Document routed to officer manual review queue."
            )

        # Insert IMMUTABLE VerificationRecord (always insert new row, never update)
        verification_record = VerificationRecord(
            document_id=doc.id,
            application_id=doc.application_id,
            status=final_result.status,
            source_name=final_result.source_name,
            simulated=final_result.simulated,
            request_payload={
                "document_id": doc.id,
                "document_class": doc.class_name,
                "method": final_result.method,
                "requested_at": final_result.requested_at,
            },
            response_payload={
                "returned_fields": final_result.returned_fields,
                "response_digest": final_result.response_digest,
                "responded_at": final_result.responded_at,
                "error_category": final_result.error_category,
                "message": final_result.message,
            },
            mismatch_details=final_result.mismatch_details,
            performed_by=performed_by_user_id,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(verification_record)

        # Update document scan_status
        if final_result.status == VerificationStatusEnum.VERIFIED:
            doc.scan_status = ScanStatusEnum.COMPLETED
        elif final_result.status in (VerificationStatusEnum.MANUAL_REVIEW_REQUIRED, VerificationStatusEnum.VERIFICATION_PENDING):
            doc.scan_status = ScanStatusEnum.PROCESSING

        await db.commit()
        await db.refresh(verification_record)

        # Cryptographic Audit Logging
        await AuditService.log_event(
            db=db,
            actor=f"user_{performed_by_user_id}" if performed_by_user_id else "system_verifier",
            role="verification_officer" if performed_by_user_id else "system",
            action="VERIFY_DOCUMENT",
            target_type="DOCUMENT",
            target_id=doc.id,
            payload={
                "document_id": doc.id,
                "application_id": doc.application_id,
                "verification_record_id": verification_record.id,
                "status": final_result.status.value,
                "source_name": final_result.source_name,
                "method": final_result.method,
                "simulated": final_result.simulated,
            },
            rule_versions={"verification_profile": "v1.0"},
            model_versions={"qr_detector": "opencv-4.9", "adapter": final_result.source_name},
        )

        return {
            "verification_record_id": verification_record.id,
            "document_id": doc.id,
            "application_id": doc.application_id,
            "status": final_result.status.value,
            "source_name": final_result.source_name,
            "method": final_result.method,
            "simulated": final_result.simulated,
            "message": final_result.message,
            "mismatch_details": final_result.mismatch_details,
            "timestamp": verification_record.timestamp.isoformat(),
        }
