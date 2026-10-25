"""0002_audit_chain_and_trigger

Revision ID: 0002_audit_chain_and_trigger
Revises: 0001_initial_schema
Create Date: 2026-10-24 12:00:00.000000 UTC

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_audit_chain_and_trigger"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop previous audit_entries table and recreate with full cryptographic chain columns
    op.drop_table("audit_entries")

    op.create_table(
        "audit_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("seq", sa.Integer(), nullable=False, unique=True),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("rule_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("current_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("idx_audit_seq", "audit_entries", ["seq"], unique=True)
    op.create_index("idx_audit_actor", "audit_entries", ["actor"])
    op.create_index("idx_audit_role", "audit_entries", ["role"])
    op.create_index("idx_audit_action", "audit_entries", ["action"])
    op.create_index("idx_audit_target", "audit_entries", ["target_type", "target_id"])
    op.create_index("idx_audit_created_at", "audit_entries", ["created_at"])
    op.create_index("idx_audit_current_hash", "audit_entries", ["current_hash"])

    # PostgreSQL trigger preventing UPDATE and DELETE on audit_entries
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_tampering()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit trail is strictly append-only. UPDATE and DELETE operations are forbidden.';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_entries_immutable
        BEFORE UPDATE OR DELETE ON audit_entries
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_tampering();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_entries_immutable ON audit_entries;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_tampering();")
    op.drop_table("audit_entries")
