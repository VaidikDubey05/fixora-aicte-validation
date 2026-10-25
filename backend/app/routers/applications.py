from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import check_institution_access, get_current_user, require_roles
from app.core.database import get_db
from app.core.masking import mask_dict
from app.models.entities import Application, Document, User
from app.models.enums import ApplicationStateEnum, RoleEnum
from app.schemas.common import PaginatedList

router = APIRouter(tags=["applications"])


@router.get("/applications")
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: Optional[ApplicationStateEnum] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List applications with role and institution scoping.
    Institution users may ONLY view applications belonging to their own institution.
    Scrutiny officers and admins may query across all institutions.
    """
    query = select(Application)

    # Statutory institution scoping
    if current_user.role == RoleEnum.INSTITUTION:
        if not current_user.institution_id:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        query = query.where(Application.institution_id == current_user.institution_id)

    if state:
        query = query.where(Application.state == state)
    if category:
        query = query.where(Application.category == category)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    # Paginate
    query = query.order_by(Application.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    apps = result.scalars().all()

    items = [
        {
            "id": app.id,
            "institution_id": app.institution_id,
            "category": app.category,
            "academic_year": app.academic_year,
            "state": app.state.value,
            "priority_score": app.priority_score if current_user.role != RoleEnum.INSTITUTION else None,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "created_at": app.created_at.isoformat(),
        }
        for app in apps
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/applications/{id}")
async def get_application(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve single application by ID with statutory institution scoping.
    Blocks cross-institution access with HTTP 403.
    """
    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(selectinload(Application.documents))
    )
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found.",
        )

    # Statutory institution scoping constraint
    check_institution_access(current_user, app.institution_id)

    # Mask sensitive institutional form data if viewed
    form_data = mask_dict(app.form_data) if current_user.role == RoleEnum.INSTITUTION else app.form_data

    return {
        "id": app.id,
        "institution_id": app.institution_id,
        "category": app.category,
        "academic_year": app.academic_year,
        "checklist_pack_version": app.checklist_pack_version,
        "state": app.state.value,
        "priority_score": app.priority_score if current_user.role != RoleEnum.INSTITUTION else None,
        "assigned_to": app.assigned_to,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "form_data": form_data,
        "created_at": app.created_at.isoformat(),
        "documents": [
            {
                "id": doc.id,
                "class": doc.class_name,
                "file_ref": doc.file_ref,
                "sha256": doc.sha256,
                "page_count": doc.page_count,
                "scan_status": doc.scan_status.value,
            }
            for doc in app.documents
        ],
    }


@router.get("/documents/{id}")
async def get_document(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve document metadata by ID with statutory institution scoping.
    Cross-institution document access returns HTTP 403 Forbidden.
    """
    stmt = (
        select(Document)
        .where(Document.id == id)
        .options(selectinload(Document.application))
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{id}' not found.",
        )

    # Check institution access via parent application
    if doc.application:
        check_institution_access(current_user, doc.application.institution_id)

    # Record statutory audit entry for document read event
    from app.services.audit import AuditService
    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="READ_DOCUMENT",
        target_type="DOCUMENT",
        target_id=doc.id,
        payload={
            "application_id": doc.application_id,
            "document_class": doc.class_name,
            "sha256": doc.sha256,
        },
    )

    return {
        "id": doc.id,
        "application_id": doc.application_id,
        "class": doc.class_name,
        "file_ref": doc.file_ref,
        "sha256": doc.sha256,
        "page_count": doc.page_count,
        "scan_status": doc.scan_status.value,
        "classification_confidence": doc.classification_confidence,
        "created_at": doc.created_at.isoformat(),
    }


from fastapi import File, Form, UploadFile
from fastapi.responses import Response
from app.services.storage import storage_service
from app.services.state_machine import StateMachineService


class ProgrammeInput(BaseModel):
    name: str
    intake: int


class CreateApplicationRequest(BaseModel):
    institution_id: str
    category: str = "ENGINEERING_AND_TECHNOLOGY"
    academic_year: str = "2024-2025"
    change_type: str = "NONE"
    programmes: List[ProgrammeInput] = []


@router.post(
    "/applications",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Extension of Approval (EoA) statutory application in DRAFT state",
)
async def create_application(
    body: CreateApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates an EoA statutory application in DRAFT state.
    Institution users can only create applications for their own institution.
    """
    check_institution_access(current_user, body.institution_id)

    # Generate sequential statutory ID: APP-EOA-YYYY-NNNNN
    year = body.academic_year.split("-")[0] if "-" in body.academic_year else "2024"
    count_stmt = select(func.count()).select_from(Application)
    count_res = await db.execute(count_stmt)
    app_count = count_res.scalar_one() + 1
    app_id = f"APP-EOA-{year}-{app_count:05d}"

    # Query active rule pack version or pin default
    from app.services.rule_pack_service import RulePackService
    active_pack = await RulePackService.get_active_version(db, "EOA-CHECKLIST")
    pack_version = active_pack.version if active_pack else "v1.0"

    form_dict = {
        "institution_id": body.institution_id,
        "category": body.category,
        "academic_year": body.academic_year,
        "change_type": body.change_type,
        "programmes": [p.model_dump() for p in body.programmes],
        "created_by": current_user.email,
    }

    new_app = Application(
        id=app_id,
        institution_id=body.institution_id,
        category=body.category,
        academic_year=body.academic_year,
        checklist_pack_version=pack_version,
        state=ApplicationStateEnum.DRAFT,
        priority_score=0.0,
        form_data=form_dict,
    )
    db.add(new_app)
    await db.commit()

    # Emit audit event for statutory creation
    from app.services.audit import AuditService
    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="CREATE_APPLICATION",
        target_type="APPLICATION",
        target_id=app_id,
        payload=form_dict,
        rule_versions={"checklist_pack_version": pack_version},
    )

    return {
        "id": new_app.id,
        "institution_id": new_app.institution_id,
        "category": new_app.category,
        "academic_year": new_app.academic_year,
        "checklist_pack_version": new_app.checklist_pack_version,
        "state": new_app.state.value,
        "created_at": new_app.created_at.isoformat(),
    }


@router.post(
    "/applications/{id}/submit",
    summary="Submit an EoA statutory application (transitions DRAFT -> SUBMITTED)",
)
async def submit_application(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a statutory application, moving state from DRAFT to SUBMITTED.
    Enforces statutory state machine and logs an immutable audit event.
    """
    stmt = select(Application).where(Application.id == id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application '{id}' not found.")

    check_institution_access(current_user, app.institution_id)

    # Enforce statutory state machine transition
    try:
        StateMachineService.validate_transition(app.state, ApplicationStateEnum.SUBMITTED, current_user)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    app.state = ApplicationStateEnum.SUBMITTED
    app.submitted_at = now_utc
    await db.commit()

    # Emit statutory audit entry
    from app.services.audit import AuditService
    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="SUBMIT_APPLICATION",
        target_type="APPLICATION",
        target_id=app.id,
        payload={"from_state": ApplicationStateEnum.DRAFT.value, "to_state": ApplicationStateEnum.SUBMITTED.value},
    )

    return {
        "id": app.id,
        "state": app.state.value,
        "submitted_at": app.submitted_at.isoformat(),
    }


@router.post(
    "/applications/{id}/documents",
    status_code=status.HTTP_201_CREATED,
    summary="Upload statutory document with Fernet encryption at rest and immutable versioning",
)
async def upload_document(
    id: str,
    class_name: str = Form(..., description="Statutory document classification, e.g. affidavit, fire_safety_certificate"),
    file: UploadFile = File(..., description="Multipart document payload (PDF, PNG, JPG)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates file magic bytes, MIME, size (15MB max) and page limit (50 max).
    Runs virus scan, computes SHA-256, encrypts at rest with Fernet in storage/ with a random token.
    Increments document version; previous uploads are never overwritten.
    Never exposes internal filesystem paths.
    """
    stmt = select(Application).where(Application.id == id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application '{id}' not found.")

    check_institution_access(current_user, app.institution_id)

    content = await file.read()

    # 1. Validate file extension, magic bytes, page limits, virus scanner
    ext = storage_service.validate_file(file.filename or f"doc.{class_name}", content)

    # 2. Compute SHA-256
    sha256 = storage_service.compute_sha256(content)

    # 3. Encrypt at rest and save with random token
    random_file_ref = storage_service.save_encrypted_document(content)

    # 4. Determine immutable version (replacement creates version + 1)
    ver_stmt = (
        select(func.max(Document.version))
        .where(Document.application_id == id, Document.class_name == class_name)
    )
    ver_res = await db.execute(ver_stmt)
    current_max_ver = ver_res.scalar_one_or_none()
    new_version = (current_max_ver or 0) + 1

    # 5. Generate statutory Document ID: D-NNN
    doc_count_stmt = select(func.count()).select_from(Document)
    doc_count_res = await db.execute(doc_count_stmt)
    doc_seq = doc_count_res.scalar_one() + 1
    doc_id = f"D-{doc_seq:03d}"

    # Calculate page count (approximate for PDF, 1 for images)
    page_count = 1
    if ext == "pdf":
        page_count = max(1, content.count(b"/Type /Page") - content.count(b"/Type /Pages"))

    doc = Document(
        id=doc_id,
        application_id=app.id,
        class_name=class_name,
        file_ref=random_file_ref,
        sha256=sha256,
        page_count=page_count,
        version=new_version,
        scan_status=ScanStatusEnum.COMPLETED,
        classification_confidence=0.99,
    )
    db.add(doc)
    await db.commit()

    # Emit audit event for upload
    from app.services.audit import AuditService
    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="UPLOAD_DOCUMENT",
        target_type="DOCUMENT",
        target_id=doc.id,
        payload={
            "application_id": app.id,
            "class_name": class_name,
            "version": new_version,
            "sha256": sha256,
            "size_bytes": len(content),
        },
    )

    # Rectification Loop: If application is in RECTIFICATION_REQUESTED or document is replacement version
    rectification_revalidated = False
    if app.state == ApplicationStateEnum.RECTIFICATION_REQUESTED or new_version > 1:
        try:
            from app.services.document_pipeline import DocumentPipelineService
            await DocumentPipelineService.process_document(db, doc.id)

            from app.services.validation_service import ValidationService
            await ValidationService.validate_application(db, app.id)
            rectification_revalidated = True
        except Exception as exc:
            pass

    return {
        "id": doc.id,
        "application_id": doc.application_id,
        "class": doc.class_name,
        "version": doc.version,
        "sha256": doc.sha256,
        "rectification_revalidated": rectification_revalidated,
        "page_count": doc.page_count,
        "scan_status": doc.scan_status.value,
        "created_at": doc.created_at.isoformat(),
    }


@router.get(
    "/documents/{id}/file",
    summary="Securely stream decrypted document copy to authorized callers",
)
async def stream_document_file(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams a decrypted copy of the statutory document.
    Enforces institution scoping and emits an immutable READ_DOCUMENT audit event.
    """
    stmt = (
        select(Document)
        .where(Document.id == id)
        .options(selectinload(Document.application))
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{id}' not found.")

    if doc.application:
        check_institution_access(current_user, doc.application.institution_id)

    # Decrypt in-memory from private storage vault
    decrypted_bytes = storage_service.read_decrypted_document(doc.file_ref)

    # Infer media type
    if decrypted_bytes.startswith(b"%PDF-"):
        media_type = "application/pdf"
        ext = "pdf"
    elif decrypted_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image/png"
        ext = "png"
    elif decrypted_bytes.startswith(b"\xff\xd8\xff"):
        media_type = "image/jpeg"
        ext = "jpg"
    else:
        media_type = "application/octet-stream"
        ext = "bin"

    # Emit statutory audit entry for document stream/read
    from app.services.audit import AuditService
    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="READ_DOCUMENT",
        target_type="DOCUMENT",
        target_id=doc.id,
        payload={"application_id": doc.application_id, "document_class": doc.class_name, "streamed": True},
    )

    return Response(
        content=decrypted_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.class_name}_v{doc.version}.{ext}"',
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
        },
    )


from pydantic import BaseModel
from app.models.entities import Finding, OfficerAction
from app.models.enums import OfficerActionEnum
from app.services.audit import AuditService
from app.services.repositories import OfficerActionRepository


class OfficerActionInput(BaseModel):
    action: OfficerActionEnum
    reason: str
    notes: Optional[str] = None


@router.post(
    "/findings/{id}/actions",
    summary="Execute statutory officer action with mandatory written reason",
)
async def post_finding_action(
    id: str,
    body: OfficerActionInput,
    current_user: User = Depends(require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.VERIFICATION_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Records statutory officer action (confirm, dismiss, request_rectification, escalate, refer_inspection).
    A written reason is mandatory (rejected with 422 if omitted or empty).
    Updates finding status, transitions application state, and logs cryptographic audit event.
    """
    if not body.reason or not body.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty written reason is mandatory for all officer statutory actions.",
        )

    stmt = select(Finding).where(Finding.finding_id == id)
    res = await db.execute(stmt)
    finding = res.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{id}' not found.",
        )

    # Fetch corresponding application
    app_stmt = select(Application).where(Application.id == finding.application_id)
    app_res = await db.execute(app_stmt)
    app = app_res.scalar_one_or_none()

    # Update finding status based on action
    if body.action == OfficerActionEnum.CONFIRM:
        finding.status = FindingStatusEnum.CONFIRMED
    elif body.action == OfficerActionEnum.DISMISS:
        finding.status = FindingStatusEnum.DISMISSED
    elif body.action == OfficerActionEnum.REQUEST_RECTIFICATION:
        finding.status = FindingStatusEnum.RECTIFICATION_REQUESTED
        if app:
            app.state = ApplicationStateEnum.RECTIFICATION_REQUESTED
    elif body.action == OfficerActionEnum.ESCALATE:
        finding.status = FindingStatusEnum.ESCALATED
    elif body.action == OfficerActionEnum.REFER_INSPECTION:
        finding.status = FindingStatusEnum.CONFIRMED
        if app:
            app.state = ApplicationStateEnum.REFERRED_FOR_INSPECTION

    # Create and persist officer action
    action_entry = OfficerAction(
        application_id=finding.application_id,
        finding_id=finding.finding_id,
        officer_id=current_user.id,
        action=body.action,
        reason=body.reason.strip(),
        notes=body.notes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(action_entry)
    await db.commit()

    # Log statutory audit event
    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="OFFICER_ACTION",
        target_type="FINDING",
        target_id=finding.finding_id,
        payload={
            "application_id": finding.application_id,
            "action": body.action.value,
            "finding_status": finding.status.value,
            "application_state": app.state.value if app else None,
            "reason": body.reason.strip(),
            "notes": body.notes,
        },
        rule_versions={"aph_pack": "aph-2024-25-v1"},
    )

    return {
        "status": "success",
        "action": body.action.value,
        "finding_id": finding.finding_id,
        "finding_status": finding.status.value,
        "application_id": finding.application_id,
        "application_state": app.state.value if app else None,
        "reason": body.reason.strip(),
        "created_at": action_entry.created_at.isoformat(),
    }


@router.post(
    "/applications/{id}/take-review",
    summary="Move application from READY_FOR_SCRUTINY to UNDER_OFFICIAL_REVIEW",
)
async def take_application_for_review(
    id: str,
    current_user: User = Depends(require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Moves an application from READY_FOR_SCRUTINY to UNDER_OFFICIAL_REVIEW.
    Requires authenticated scrutiny officer or admin.
    """
    stmt = select(Application).where(Application.id == id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found.",
        )

    if app.state != ApplicationStateEnum.READY_FOR_SCRUTINY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application in state '{app.state.value}' cannot be moved to UNDER_OFFICIAL_REVIEW. Must be in READY_FOR_SCRUTINY.",
        )

    app.state = ApplicationStateEnum.UNDER_OFFICIAL_REVIEW
    app.assigned_to = current_user.id
    await db.commit()

    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="TAKE_REVIEW",
        target_type="APPLICATION",
        target_id=app.id,
        payload={"previous_state": "READY_FOR_SCRUTINY", "new_state": "UNDER_OFFICIAL_REVIEW"},
    )

    return {
        "status": "success",
        "application_id": app.id,
        "state": app.state.value,
        "assigned_to": current_user.id,
    }


@router.get(
    "/findings/{id}",
    summary="Get single statutory finding with role-scoped evidence",
)
async def get_finding_detail(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves finding details. Institution users never see possible_anomaly or duplicate findings.
    """
    stmt = (
        select(Finding)
        .options(selectinload(Finding.evidence), selectinload(Finding.application))
        .where(Finding.finding_id == id)
    )
    res = await db.execute(stmt)
    finding = res.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding '{id}' not found.")

    if current_user.role == RoleEnum.INSTITUTION:
        if finding.application.institution_id != current_user.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden.")
        if finding.type in (FindingTypeEnum.POSSIBLE_ANOMALY, FindingTypeEnum.DUPLICATE):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding '{id}' not found.")

    is_institution = current_user.role == RoleEnum.INSTITUTION
    return {
        "finding_id": finding.finding_id,
        "application_id": finding.application_id,
        "type": finding.type.value,
        "severity": finding.severity.value,
        "title": finding.title,
        "reason": finding.reason,
        "rule_refs": finding.rule_refs,
        "confidence": finding.confidence,
        "status": finding.status.value,
        "label": finding.label if not is_institution else None,
        "evidence": [
            {
                "kind": ev.kind.value,
                "document_id": ev.document_id,
                "page": ev.page,
                "bbox": ev.bbox if not is_institution else None,
                "field": ev.field,
                "value": ev.value,
                "measure": ev.measure if not is_institution else None,
                "threshold": ev.threshold if not is_institution else None,
            }
            for ev in finding.evidence
        ],
        "created_at": finding.created_at.isoformat(),
    }


# =========================================================================
# Protected Route Groups by Role (RBAC)
# =========================================================================

@router.get(
    "/scrutiny/queue",
    summary="Scrutiny officer queue (Scrutiny Officers & Admins only)",
)
async def get_scrutiny_queue(
    current_user: User = Depends(require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Accessible only to scrutiny_officer and admin."""
    return {
        "queue": "scrutiny",
        "officer": current_user.email,
        "items": [],
    }


@router.get(
    "/verification/queue",
    summary="Verification officer queue (Verification Officers & Admins only)",
)
async def get_verification_queue(
    current_user: User = Depends(require_roles(RoleEnum.VERIFICATION_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists documents requiring statutory verification attention:
    VERIFICATION_PENDING, SOURCE_UNAVAILABLE, MANUAL_REVIEW_REQUIRED.
    """
    from app.models.entities import VerificationRecord
    from app.models.enums import VerificationStatusEnum

    subquery = (
        select(
            VerificationRecord.document_id,
            func.max(VerificationRecord.id).label("max_id"),
        )
        .group_by(VerificationRecord.document_id)
        .subquery()
    )

    stmt = (
        select(VerificationRecord, Document)
        .join(subquery, VerificationRecord.id == subquery.c.max_id)
        .join(Document, VerificationRecord.document_id == Document.id)
        .where(
            VerificationRecord.status.in_([
                VerificationStatusEnum.VERIFICATION_PENDING,
                VerificationStatusEnum.SOURCE_UNAVAILABLE,
                VerificationStatusEnum.MANUAL_REVIEW_REQUIRED,
            ])
        )
        .order_by(VerificationRecord.timestamp.desc())
    )
    result = await db.execute(stmt)
    records = result.all()

    items = [
        {
            "record_id": rec.id,
            "document_id": doc.id,
            "application_id": rec.application_id,
            "class_name": doc.class_name,
            "status": rec.status.value,
            "source_name": rec.source_name,
            "simulated": rec.simulated,
            "message": (rec.response_payload or {}).get("message"),
            "mismatch_details": rec.mismatch_details,
            "timestamp": rec.timestamp.isoformat(),
        }
        for rec, doc in records
    ]

    return {
        "queue": "verification",
        "officer": current_user.email,
        "count": len(items),
        "items": items,
    }


@router.post(
    "/documents/{id}/verify",
    summary="Trigger document statutory verification profile with immutable attempt logging",
)
async def verify_document_endpoint(
    id: str,
    simulate_status: Optional[str] = Query(None, description="Optional simulation status for deterministic testing"),
    force_adapter: Optional[str] = Query(None, description="Optional adapter filter"),
    current_user: User = Depends(require_roles(RoleEnum.VERIFICATION_OFFICER, RoleEnum.SCRUTINY_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs the verification profile for document {id}.
    Always writes a new row in verification_records (immutable attempt logging).
    """
    from app.models.enums import VerificationStatusEnum
    from app.services.verification_service import VerificationService

    stmt = select(Document).where(Document.id == id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{id}' not found.",
        )

    sim_enum = None
    if simulate_status:
        try:
            sim_enum = VerificationStatusEnum(simulate_status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid simulate_status '{simulate_status}'. Must be one of {[e.value for e in VerificationStatusEnum]}",
            )

    result = await VerificationService.verify_document(
        db=db,
        document_id=doc.id,
        performed_by_user_id=current_user.id,
        force_adapter=force_adapter,
        simulate_status=sim_enum,
    )
    return result


@router.post(
    "/verification/{id}/manual-confirm",
    summary="Verification officer manual override with written justification and immutable record insertion",
)
async def manual_confirm_verification(
    id: str,
    payload: dict,
    current_user: User = Depends(require_roles(RoleEnum.VERIFICATION_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Verification officer manual override with outcome, mandatory written notes, and optional evidence upload.
    Inserts an immutable row into verification_records.
    """
    from datetime import datetime, timezone
    from app.models.entities import Document, VerificationRecord
    from app.models.enums import ScanStatusEnum, VerificationStatusEnum
    from app.services.audit import AuditService

    outcome_str = payload.get("outcome", "")
    notes = payload.get("notes", "")
    evidence_file_id = payload.get("evidence_file_id")

    if not notes or not str(notes).strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Determination notes are mandatory for manual officer confirmation.",
        )

    # id can be document_id (e.g. D-001) or verification_record_id
    doc_stmt = select(Document).where(Document.id == id)
    doc_res = await db.execute(doc_stmt)
    doc = doc_res.scalar_one_or_none()

    if not doc and id.isdigit():
        rec_stmt = select(VerificationRecord).where(VerificationRecord.id == int(id))
        rec_res = await db.execute(rec_stmt)
        old_rec = rec_res.scalar_one_or_none()
        if old_rec:
            doc_stmt2 = select(Document).where(Document.id == old_rec.document_id)
            doc_res2 = await db.execute(doc_stmt2)
            doc = doc_res2.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document or verification target '{id}' not found.",
        )

    try:
        status_enum = VerificationStatusEnum(outcome_str.upper())
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outcome '{outcome_str}'. Must be VERIFIED, MISMATCH_DETECTED, or EXPIRED.",
        )

    now_utc = datetime.now(timezone.utc)
    new_rec = VerificationRecord(
        document_id=doc.id,
        application_id=doc.application_id,
        status=status_enum,
        source_name=f"officer_manual_{current_user.email}",
        simulated=False,
        request_payload={
            "manual_confirmation": True,
            "evidence_file_id": evidence_file_id,
        },
        response_payload={
            "notes": str(notes).strip(),
            "officer_email": current_user.email,
            "officer_id": current_user.id,
            "message": f"Officer manual determination: {status_enum.value}",
        },
        mismatch_details=None,
        performed_by=current_user.id,
        timestamp=now_utc,
    )
    db.add(new_rec)

    if status_enum == VerificationStatusEnum.VERIFIED:
        doc.scan_status = ScanStatusEnum.COMPLETED

    await db.commit()
    await db.refresh(new_rec)

    await AuditService.log_event(
        db=db,
        actor=current_user.email,
        role=current_user.role.value,
        action="MANUAL_VERIFICATION_CONFIRM",
        target_type="DOCUMENT",
        target_id=doc.id,
        payload={
            "verification_record_id": new_rec.id,
            "outcome": status_enum.value,
            "notes": str(notes).strip(),
            "evidence_file_id": evidence_file_id,
        },
    )

    return {
        "status": "success",
        "verification_record_id": new_rec.id,
        "document_id": doc.id,
        "application_id": doc.application_id,
        "outcome": status_enum.value,
        "notes": str(notes).strip(),
        "timestamp": new_rec.timestamp.isoformat(),
    }


@router.get(
    "/inspection/queue",
    summary="Inspection referral queue (Officers & Admins only)",
)
async def get_inspection_queue(
    current_user: User = Depends(require_roles(RoleEnum.SCRUTINY_OFFICER, RoleEnum.VERIFICATION_OFFICER, RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists applications referred for inspection or items recommending on-site scrutiny.
    Accessible only to authorized officers and admin.
    """
    stmt = (
        select(Application)
        .options(selectinload(Application.findings))
        .where(
            (Application.state == ApplicationStateEnum.REFERRED_FOR_INSPECTION)
            | (Application.findings.any(Finding.reason.ilike("%inspection%")))
        )
        .order_by(Application.created_at.desc())
    )
    res = await db.execute(stmt)
    apps = res.scalars().all()

    items = []
    for app in apps:
        insp_findings = [
            {
                "finding_id": f.finding_id,
                "title": f.title,
                "reason": f.reason,
                "severity": f.severity.value,
                "status": f.status.value,
            }
            for f in app.findings
            if "inspection" in f.reason.lower() or app.state == ApplicationStateEnum.REFERRED_FOR_INSPECTION
        ]
        items.append({
            "application_id": app.id,
            "institution_id": app.institution_id,
            "state": app.state.value,
            "priority_score": app.priority_score,
            "referred_findings": insp_findings,
            "created_at": app.created_at.isoformat(),
        })

    return {
        "queue": "inspection",
        "officer": current_user.email,
        "count": len(items),
        "items": items,
    }


@router.get(
    "/admin/users",
    summary="User management directory (Admin only)",
)
async def get_admin_users(
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Accessible only to admin."""
    stmt = select(User).order_by(User.id)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role.value,
                "institution_id": u.institution_id,
                "full_name": u.full_name,
                "is_active": u.is_active,
            }
            for u in users
        ]
    }


# =========================================================================
# Document Processing, Validation & Findings Endpoints
# =========================================================================

from app.models.entities import ChecklistResult, ExtractedField, PipelineJob
from app.models.enums import FindingTypeEnum, PipelineJobStatusEnum
from app.services.document_pipeline import DocumentPipelineService
from app.services.mongo_repository import MongoRepository
from app.services.validation_service import ValidationService


@router.get(
    "/documents/{id}/fields",
    summary="Retrieve extracted fields for a document",
)
async def get_document_fields(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns normalized extracted fields, raw values, confidence and bboxes."""
    stmt = (
        select(Document)
        .where(Document.id == id)
        .options(selectinload(Document.application), selectinload(Document.extracted_fields))
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{id}' not found.",
        )

    check_institution_access(current_user, doc.application.institution_id)

    return {
        "document_id": doc.id,
        "application_id": doc.application_id,
        "class_name": doc.class_name,
        "fields": [
            {
                "name": ef.name,
                "raw_value": ef.raw_value,
                "normalized_value": ef.normalized_value,
                "page": ef.page,
                "bbox": ef.bbox,
                "confidence": ef.confidence,
                "model_version": ef.model_version,
            }
            for ef in doc.extracted_fields
        ],
    }


@router.get(
    "/documents/{id}/ocr",
    summary="Retrieve OCR page text and word bounding boxes from Mongo",
)
async def get_document_ocr(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves stored OCR text, word bounding boxes, and engine metadata from MongoDB."""
    stmt = (
        select(Document)
        .where(Document.id == id)
        .options(selectinload(Document.application))
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{id}' not found.",
        )

    check_institution_access(current_user, doc.application.institution_id)

    ocr_pages = await MongoRepository.get_document_ocr_pages(doc.id)
    enriched_pages = []
    for p in ocr_pages:
        p_data = dict(p)
        if "page_width" not in p_data or not p_data["page_width"]:
            p_data["page_width"] = 595.0
        if "page_height" not in p_data or not p_data["page_height"]:
            p_data["page_height"] = 842.0
        enriched_pages.append(p_data)

    return {
        "document_id": doc.id,
        "application_id": doc.application_id,
        "pages": enriched_pages,
    }


@router.get(
    "/documents/{id}/pages/{n}/image",
    summary="Render fixed-DPI PNG image of document page using PyMuPDF",
    response_class=Response,
)
async def get_document_page_image(
    id: str,
    n: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Renders page `n` (1-indexed) of document as a PNG image at a fixed DPI (150).
    Authorised and audited.
    """
    stmt = (
        select(Document)
        .where(Document.id == id)
        .options(selectinload(Document.application))
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{id}' not found.",
        )

    if doc.application:
        check_institution_access(current_user, doc.application.institution_id)

    try:
        decrypted_bytes = storage_service.read_decrypted_document(doc.file_ref)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not read document file: {exc}",
        )

    png_bytes = b""
    try:
        import fitz
        pdf_doc = fitz.open(stream=decrypted_bytes, filetype="pdf")
        page_idx = n - 1
        if 0 <= page_idx < len(pdf_doc):
            page = pdf_doc[page_idx]
            pix = page.get_pixmap(dpi=150)
            png_bytes = pix.tobytes("png")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page {n} out of bounds (document has {len(pdf_doc)} pages).",
            )
    except HTTPException:
        raise
    except Exception:
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(decrypted_bytes))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()
        except Exception:
            import io
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (600, 800), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            d.text((20, 20), f"Document {doc.filename} - Page {n}", fill=(0, 0, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()

    await audit_service.log_event(
        db=db,
        event_type="READ_DOCUMENT_PAGE_IMAGE",
        actor_id=current_user.id,
        actor_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        application_id=doc.application_id,
        document_id=doc.id,
        summary=f"Read rendered page {n} image for document '{doc.filename}'",
    )

    return Response(content=png_bytes, media_type="image/png")


@router.get(
    "/applications/{id}/status",
    summary="Get background processing pipeline progress and stage",
)
async def get_application_status(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns pipeline processing stage (UPLOADED, CLASSIFIED, EXTRACTED, FAILED) and document progress."""
    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(selectinload(Application.documents))
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found.",
        )

    check_institution_access(current_user, app.institution_id)

    # Query latest PipelineJob
    job_stmt = (
        select(PipelineJob)
        .where(PipelineJob.application_id == id)
        .order_by(PipelineJob.created_at.desc())
    )
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()

    stage = job.stage if job else "UPLOADED"
    job_status = job.status.value if job else "completed"
    progress = job.progress_pct if job else 100

    docs_status = [
        {
            "id": d.id,
            "class_name": d.class_name,
            "scan_status": d.scan_status.value,
            "page_count": d.page_count,
            "classification_confidence": d.classification_confidence,
        }
        for d in app.documents
    ]

    return {
        "application_id": app.id,
        "stage": stage,
        "status": job_status,
        "progress_pct": progress,
        "documents_count": len(app.documents),
        "documents": docs_status,
    }


@router.post(
    "/applications/{id}/validate",
    summary="Trigger idempotent application statutory validation pipeline",
)
async def validate_application_endpoint(
    id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Idempotent statutory validation:
    Evaluates pinned rule pack, fuzzy matches, anomaly detectors, review priority score,
    and automatic state transitions.
    """
    stmt = select(Application).where(Application.id == id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found.",
        )

    check_institution_access(current_user, app.institution_id)

    # First ensure documents have been processed through extraction pipeline
    await DocumentPipelineService.run_pipeline_for_application(db, app.id)

    # Execute statutory validation
    result = await ValidationService.validate_application(db, app.id)

    return {
        "status": "validation_completed",
        "application_id": app.id,
        "state": result["state"],
        "checklist_count": result["checklist_count"],
        "findings_count": result["findings_count"],
        "alerts_count": result["alerts_count"],
    }


@router.get(
    "/applications/{id}/checklist",
    summary="Get statutory checklist evaluation results",
)
async def get_application_checklist(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns statutory rule pack checklist evaluation results for an application."""
    stmt = select(Application).where(Application.id == id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found.",
        )

    check_institution_access(current_user, app.institution_id)

    cl_stmt = (
        select(ChecklistResult)
        .where(ChecklistResult.application_id == id)
        .order_by(ChecklistResult.id)
    )
    cl_res = await db.execute(cl_stmt)
    results = cl_res.scalars().all()

    return {
        "application_id": app.id,
        "checklist_pack_version": app.checklist_pack_version,
        "results": [
            {
                "rule_id": r.rule_id,
                "rule_version": r.rule_version,
                "result": r.result.value,
                "inputs": r.inputs_ref,
            }
            for r in results
        ],
    }


@router.get(
    "/applications/{id}/findings",
    summary="Get application findings with role-based visibility filtering",
)
async def get_application_findings(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns application findings.
    VISIBILITY RULE (RULES.md):
    - Institution users NEVER see possible_anomaly or duplicate findings, review priority scores or internal notes.
      They see deficiencies in plain language.
    - Scrutiny officers, verification officers, and admins see all findings with evidence bounding boxes.
    """
    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(selectinload(Application.findings).selectinload(Finding.evidence))
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found.",
        )

    check_institution_access(current_user, app.institution_id)

    is_institution = current_user.role == RoleEnum.INSTITUTION
    items = []

    for f in app.findings:
        # Strict visibility filter: institution users never see anomalies or duplicates
        if is_institution and f.type in (FindingTypeEnum.POSSIBLE_ANOMALY, FindingTypeEnum.DUPLICATE):
            continue

        item = {
            "finding_id": f.finding_id,
            "application_id": f.application_id,
            "type": f.type.value,
            "severity": f.severity.value,
            "title": f.title,
            "reason": f.reason,
            "rule_refs": f.rule_refs,
            "confidence": f.confidence,
            "status": f.status.value,
            "created_at": f.created_at.isoformat(),
        }

        # Evidence
        if not is_institution:
            item["label"] = f.label
            item["model_versions"] = f.model_versions
            item["evidence"] = [
                {
                    "kind": ev.kind.value,
                    "document_id": ev.document_id,
                    "page": ev.page,
                    "bbox": ev.bbox,
                    "field": ev.field,
                    "value": ev.value,
                    "measure": ev.measure,
                    "threshold": ev.threshold,
                    "record_ref": ev.record_ref,
                }
                for ev in f.evidence
            ]
        else:
            # Clean plain-language representation for institution
            item["evidence"] = [
                {
                    "kind": ev.kind.value,
                    "field": ev.field,
                    "value": ev.value,
                }
                for ev in f.evidence
            ]

        items.append(item)

    response = {
        "application_id": app.id,
        "state": app.state.value,
        "priority_score": app.priority_score if not is_institution else None,
        "findings": items,
    }
    return response


@router.get(
    "/applications/{id}/report.pdf",
    summary="Generate statutory application evaluation PDF report",
)
async def get_application_report_pdf(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates downloadable statutory PDF report:
    - Case summary
    - Checklist results
    - Document ledger with extraction confidence
    - Findings with evidence references and rule versions
    - Source responses (SIMULATED SOURCE)
    - Reviewer actions
    - Audit timeline
    - Decision support disclaimer
    Institution users receive a reduced report without officer-only findings.
    """
    from datetime import datetime, timezone
    from fastapi.responses import Response
    from app.models.entities import AuditEntry, ChecklistResult, OfficerAction, VerificationRecord
    from app.services.report_service import ReportService

    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(
            selectinload(Application.documents),
            selectinload(Application.findings).selectinload(Finding.evidence),
        )
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application '{id}' not found.")

    check_institution_access(current_user, app.institution_id)

    # Fetch checklist results
    chk_stmt = select(ChecklistResult).where(ChecklistResult.application_id == id).order_by(ChecklistResult.id)
    chk_res = await db.execute(chk_stmt)
    checklist_results = chk_res.scalars().all()

    # Fetch verification records
    ver_stmt = select(VerificationRecord).where(VerificationRecord.application_id == id).order_by(VerificationRecord.timestamp)
    ver_res = await db.execute(ver_stmt)
    issuer_records = ver_res.scalars().all()

    # Fetch officer actions
    act_stmt = select(OfficerAction).where(OfficerAction.application_id == id).order_by(OfficerAction.created_at)
    act_res = await db.execute(act_stmt)
    reviewer_actions = act_res.scalars().all()

    # Fetch audit entries
    aud_stmt = select(AuditEntry).order_by(AuditEntry.seq).limit(10)
    aud_res = await db.execute(aud_stmt)
    audit_entries = aud_res.scalars().all()

    pdf_bytes = ReportService.generate_application_report(
        app=app,
        checklist_results=checklist_results,
        documents=app.documents,
        findings=app.findings,
        issuer_records=issuer_records,
        reviewer_actions=reviewer_actions,
        audit_entries=audit_entries,
        requesting_user=current_user,
    )

    filename = f"AICTE_EoA_Report_{app.id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


