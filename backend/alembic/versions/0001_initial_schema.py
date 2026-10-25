"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-23 06:00:00.000000 UTC

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Institutions
    op.create_table(
        "institutions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("pin_code", sa.String(length=10), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_institutions_name", "institutions", ["name"])
    op.create_index("idx_institutions_state", "institutions", ["state"])

    # 2. Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("institution_id", sa.String(length=64), sa.ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_institution_id", "users", ["institution_id"])

    # 3. Applications
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("institution_id", sa.String(length=64), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("checklist_pack_version", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=True, server_default=sa.text("0.0")),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("form_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_applications_institution_id", "applications", ["institution_id"])
    op.create_index("idx_applications_state", "applications", ["state"])
    op.create_index("idx_applications_assigned_to", "applications", ["assigned_to"])

    # 4. Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class", sa.String(length=100), nullable=False),
        sa.Column("file_ref", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("phash", sa.String(length=64), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("scan_status", sa.String(length=64), nullable=False),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_documents_application_id", "documents", ["application_id"])
    op.create_index("idx_documents_sha256", "documents", ["sha256"])

    # 5. Extracted Fields
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=64), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_extracted_fields_doc_id", "extracted_fields", ["document_id"])
    op.create_index("idx_extracted_fields_name", "extracted_fields", ["name"])

    # 6. Checklist Results
    op.create_table(
        "checklist_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=64), nullable=False),
        sa.Column("inputs_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_checklist_results_app_id", "checklist_results", ["application_id"])
    op.create_index("idx_checklist_results_rule_id", "checklist_results", ["rule_id"])

    # 7. Findings
    op.create_table(
        "findings",
        sa.Column("finding_id", sa.String(length=64), primary_key=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("rule_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("model_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_findings_application_id", "findings", ["application_id"])
    op.create_index("idx_findings_type", "findings", ["type"])
    op.create_index("idx_findings_severity", "findings", ["severity"])
    op.create_index("idx_findings_status", "findings", ["status"])

    # 8. Evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("finding_id", sa.String(length=64), sa.ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("field", sa.String(length=128), nullable=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("measure", sa.String(length=128), nullable=True),
        sa.Column("threshold", sa.String(length=128), nullable=True),
        sa.Column("record_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_evidence_finding_id", "evidence", ["finding_id"])
    op.create_index("idx_evidence_document_id", "evidence", ["document_id"])

    # 9. Verification Records
    op.create_table(
        "verification_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=64), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mismatch_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("performed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_verif_doc_id", "verification_records", ["document_id"])
    op.create_index("idx_verif_app_id", "verification_records", ["application_id"])
    op.create_index("idx_verif_status", "verification_records", ["status"])

    # 10. Officer Actions
    op.create_table(
        "officer_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", sa.String(length=64), sa.ForeignKey("findings.finding_id", ondelete="SET NULL"), nullable=True),
        sa.Column("officer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_officer_action_written_reason_required"),
    )
    op.create_index("idx_officer_actions_app_id", "officer_actions", ["application_id"])
    op.create_index("idx_officer_actions_finding_id", "officer_actions", ["finding_id"])
    op.create_index("idx_officer_actions_officer_id", "officer_actions", ["officer_id"])

    # 11. Alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_alerts_app_id", "alerts", ["application_id"])
    op.create_index("idx_alerts_user_id", "alerts", ["user_id"])

    # 12. Audit Entries
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("application_id", sa.String(length=64), nullable=True),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("prev_hash", sa.String(length=64), nullable=True),
        sa.Column("current_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_audit_event_type", "audit_entries", ["event_type"])
    op.create_index("idx_audit_app_id", "audit_entries", ["application_id"])
    op.create_index("idx_audit_created_at", "audit_entries", ["created_at"])

    # 13. Rule Packs
    op.create_table(
        "rule_packs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 14. Rule Pack Versions
    op.create_table(
        "rule_pack_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rule_pack_id", sa.String(length=64), sa.ForeignKey("rule_packs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("rules_yaml", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_rule_pack_version", "rule_pack_versions", ["rule_pack_id", "version"], unique=True)

    # 15. Ref Records
    op.create_table(
        "ref_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("institution_id", sa.String(length=64), sa.ForeignKey("institutions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("previous_eoa", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approved_programmes_and_intake", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("faculty_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ter_payment_status", sa.String(length=50), nullable=False, server_default="PAID"),
        sa.Column("deficiency_status", sa.String(length=50), nullable=False, server_default="NO_DEFICIENCY"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. Pipeline Jobs
    op.create_table(
        "pipeline_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_pipeline_jobs_app_id", "pipeline_jobs", ["application_id"])


def downgrade() -> None:
    op.drop_table("pipeline_jobs")
    op.drop_table("ref_records")
    op.drop_table("rule_pack_versions")
    op.drop_table("rule_packs")
    op.drop_table("audit_entries")
    op.drop_table("alerts")
    op.drop_table("officer_actions")
    op.drop_table("verification_records")
    op.drop_table("evidence")
    op.drop_table("findings")
    op.drop_table("checklist_results")
    op.drop_table("extracted_fields")
    op.drop_table("documents")
    op.drop_table("applications")
    op.drop_table("users")
    op.drop_table("institutions")
