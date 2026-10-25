# FIXORA RULES
Product: AI-assisted application validation and document verification for AICTE Extension of Approval (EoA) applications. DECISION SUPPORT ONLY: the system flags issues with evidence; authorised humans decide. No endpoint or UI path may approve, reject or penalise an application automatically. Prototype uses synthetic data and mock integrations.

STACK (fixed): React + TypeScript + Vite + Tailwind CSS, Chart.js | FastAPI (Python 3.11), SQLAlchemy 2, Alembic, Pydantic v2 | PostgreSQL 16 + MongoDB 7 | Tesseract OCR (eng+hin), PyMuPDF, OpenCV, imagehash, spaCy, scikit-learn, pandas, NumPy, rapidfuzz, sentence-transformers (all-MiniLM-L6-v2) + FAISS | Docker Compose, GitHub Actions.

REPO LAYOUT: backend/app/{core,models,schemas,routers,services,workers,adapters,rules}, backend/tests, frontend/src, data/{aph,synthetic,rulepacks}, infra/, storage/ (private, git-ignored).

CONVENTIONS: JSON snake_case. Errors: {"error":{"code":"...","message":"..."}}. Lists: {"items":[],"total":0,"page":1,"page_size":20}. Timestamps ISO-8601 UTC. IDs: APP-EOA-YYYY-NNNNN, F-YYYY-NNNNNN, D-NNN. Every module has pytest tests. Config via env vars only.

VOCABULARY (use these exact strings everywhere):
- Roles: institution, scrutiny_officer, verification_officer, admin
- Application states: DRAFT, SUBMITTED, VALIDATION_IN_PROGRESS, DEFICIENCIES_FOUND, RECTIFICATION_REQUESTED, VERIFICATION_PENDING, READY_FOR_SCRUTINY, UNDER_OFFICIAL_REVIEW, REFERRED_FOR_INSPECTION, CLOSED_BY_AUTHORITY. The system may move a case only among the automated states up to READY_FOR_SCRUTINY. UNDER_OFFICIAL_REVIEW and later need an authenticated officer action.
- Verification status: VERIFIED, MISMATCH_DETECTED, EXPIRED, VERIFICATION_PENDING, SOURCE_UNAVAILABLE, MANUAL_REVIEW_REQUIRED
- Checklist result: PRESENT, MISSING, EXPIRED, INCONSISTENT, VERIFIED, NEEDS_EVIDENCE
- Severity: info, needs_attention, review_required
- Finding type: missing, incomplete, expired, inconsistent, record_mismatch, possible_anomaly, duplicate, verification, infrastructure
- Infrastructure output: consistent, needs_additional_evidence, recommend_inspection (never pass/fail)
- Officer action: confirm, dismiss, request_rectification, escalate, refer_inspection (a written reason is mandatory)

LANGUAGE: never write fake, forged or fraud in code strings, UI or reports. Anomaly findings carry the label "Preliminary indicator - human verification required". A source outage is never an adverse conclusion. Mock integrations return simulated=true and the UI shows SIMULATED SOURCE.

FINDING SHAPE: {finding_id, application_id, type, severity, title, reason, evidence:[{kind:region|record|metadata|source|rule, document_id, page, bbox, field, value, measure, threshold, record_ref}], rule_refs:[], confidence, label, status:open|confirmed|dismissed|rectification_requested|escalated, model_versions:{}, created_at}. A finding without evidence cannot be saved.

VISIBILITY: institution users never see possible_anomaly or duplicate findings, review priority scores or internal notes. They see deficiencies in plain language.

API CONTRACT (all under /api):
- POST auth/login; GET auth/me
- POST applications; GET applications (role-scoped, filters: status,state,category,severity,assignee,q,page); GET applications/{id}; POST applications/{id}/submit; GET applications/{id}/checklist; POST applications/{id}/validate; GET applications/{id}/status (pipeline stage progress); GET applications/{id}/findings; GET applications/{id}/report.pdf
- POST applications/{id}/documents (multipart); GET documents/{id}; GET documents/{id}/file (secure stream); GET documents/{id}/fields; GET documents/{id}/ocr; POST documents/{id}/verify
- GET findings/{id}; POST findings/{id}/actions
- GET verification/queue; POST verification/{id}/manual-confirm; GET inspection/queue
- GET/POST rule-packs; GET rule-packs/{id}; POST rule-packs/{id}/submit; POST rule-packs/{id}/approve; POST rule-packs/{id}/test
- POST chat; GET alerts; POST alerts/{id}/ack; GET analytics/overview
- GET audit; GET audit/verify-chain
- POST demo/seed; POST demo/reset

PRINCIPLES: rules are data (YAML), not code. Deterministic rules decide requirements; ML only extracts and flags. Low confidence routes to manual review. Original uploads are immutable. Every state change, rule run, source call, officer action and document read writes an audit event.
