import asyncio
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.entities import Application, AuditEntry, Document, Finding, Institution, User
from app.models.enums import ApplicationStateEnum, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum, RoleEnum, ScanStatusEnum
from app.services.audit import (
    GENESIS_HASH,
    AuditService,
    compute_entry_hash,
    compute_payload_hash,
)


class AsyncSessionWrapper:
    """Wraps synchronous SQLite session for testing async FastAPI dependencies."""

    def __init__(self, sync_session: Session):
        self.session = sync_session

    async def execute(self, statement, *args, **kwargs):
        return self.session.execute(statement, *args, **kwargs)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def close(self):
        self.session.close()

    def add(self, instance):
        self.session.add(instance)


@pytest.fixture
def audit_db_session():
    """Sets up an in-memory SQLite database with SQLite trigger enforcing append-only immutability."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Attach SQLite triggers enforcing append-only behavior (mirroring PostgreSQL trigger)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TRIGGER trg_prevent_audit_update
            BEFORE UPDATE ON audit_entries
            BEGIN
                SELECT RAISE(ABORT, 'Audit trail is strictly append-only. UPDATE operations are forbidden.');
            END;
        """))
        conn.execute(text("""
            CREATE TRIGGER trg_prevent_audit_delete
            BEFORE DELETE ON audit_entries
            BEGIN
                SELECT RAISE(ABORT, 'Audit trail is strictly append-only. DELETE operations are forbidden.');
            END;
        """))
        conn.commit()

    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSessionLocal()

    # Seed test users
    admin = User(
        id=1,
        email="admin@aicte.gov.in",
        hashed_password=hash_password("Admin@Fixora2026!"),
        role=RoleEnum.ADMIN,
        full_name="AICTE Admin",
    )
    scrutiny = User(
        id=2,
        email="scrutiny@aicte.gov.in",
        hashed_password=hash_password("Scrutiny@Fixora2026!"),
        role=RoleEnum.SCRUTINY_OFFICER,
        full_name="Dr. Scrutiny",
    )
    verif = User(
        id=3,
        email="verification@aicte.gov.in",
        hashed_password=hash_password("Verification@Fixora2026!"),
        role=RoleEnum.VERIFICATION_OFFICER,
        full_name="Smt. Verifier",
    )
    inst = User(
        id=4,
        email="principal@gecpune.edu.in",
        hashed_password=hash_password("Inst1@Fixora2026!"),
        role=RoleEnum.INSTITUTION,
        full_name="Principal GEC",
        institution_id="1-33276541",
    )
    session.add_all([admin, scrutiny, verif, inst])

    # Seed an institution, application, document, and finding for action testing
    institution = Institution(
        id="1-33276541",
        name="Government Engineering College, Pune",
        address="Campus Road",
        state="Maharashtra",
        district="Pune",
        pin_code="411001",
        contact_email="principal@gecpune.edu.in",
    )
    session.add(institution)
    session.flush()

    app_entry = Application(
        id="APP-EOA-2024-00001",
        institution_id=institution.id,
        category="ENGINEERING_AND_TECHNOLOGY",
        academic_year="2024-2025",
        checklist_pack_version="aph-2024-25-v1",
        state=ApplicationStateEnum.SUBMITTED,
        form_data={"programmes": ["Computer Engineering"]},
    )
    session.add(app_entry)
    session.flush()

    doc = Document(
        id="D-001",
        application_id=app_entry.id,
        class_name="land_title_deed",
        file_ref="/storage/doc1.pdf",
        sha256="hash123",
        page_count=5,
        scan_status=ScanStatusEnum.COMPLETED,
    )
    session.add(doc)

    finding = Finding(
        finding_id="F-2024-000001",
        application_id=app_entry.id,
        type=FindingTypeEnum.MISSING,
        severity=FindingSeverityEnum.REVIEW_REQUIRED,
        title="Missing Fire NOC",
        reason="Fire Safety Certificate not uploaded.",
        confidence=1.0,
        status=FindingStatusEnum.OPEN,
    )
    session.add(finding)
    session.commit()

    yield session
    session.close()


@pytest.fixture
async def audit_client(audit_db_session):
    async def override_get_db():
        yield AsyncSessionWrapper(audit_db_session)

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =========================================================================
# Unit Tests: Chain Construction & Verification
# =========================================================================

@pytest.mark.asyncio
async def test_audit_chain_sequential_linking(audit_db_session):
    wrapper = AsyncSessionWrapper(audit_db_session)

    # 1. First event (genesis)
    e1 = await AuditService.log_event(
        db=wrapper,
        actor="admin@aicte.gov.in",
        role="admin",
        action="LOGIN",
        target_type="USER",
        target_id="1",
        payload={"ip": "127.0.0.1"},
    )
    assert e1.seq == 1
    assert e1.prev_hash == GENESIS_HASH
    assert e1.payload_hash == compute_payload_hash({"ip": "127.0.0.1"})
    assert len(e1.current_hash) == 64

    # 2. Second event
    e2 = await AuditService.log_event(
        db=wrapper,
        actor="scrutiny@aicte.gov.in",
        role="scrutiny_officer",
        action="READ_DOCUMENT",
        target_type="DOCUMENT",
        target_id="D-001",
        payload={"doc_class": "land_deed"},
    )
    assert e2.seq == 2
    assert e2.prev_hash == e1.current_hash
    assert e2.current_hash != e1.current_hash

    # 3. Third event
    e3 = await AuditService.log_event(
        db=wrapper,
        actor="scrutiny@aicte.gov.in",
        role="scrutiny_officer",
        action="OFFICER_ACTION",
        target_type="FINDING",
        target_id="F-2024-000001",
        payload={"action": "refer_inspection", "reason": "Physical verification requested"},
    )
    assert e3.seq == 3
    assert e3.prev_hash == e2.current_hash

    # Verify chain
    result = await AuditService.verify_chain(wrapper)
    assert result["valid"] is True
    assert result["checked"] == 3
    assert result["first_broken_seq"] is None


@pytest.mark.asyncio
async def test_audit_chain_detects_tampered_payload(audit_db_session):
    wrapper = AsyncSessionWrapper(audit_db_session)

    # Log 3 events
    await AuditService.log_event(wrapper, "u1", "admin", "ACT1", "TARGET", "T1", {"val": 100})
    await AuditService.log_event(wrapper, "u2", "admin", "ACT2", "TARGET", "T2", {"val": 200})
    await AuditService.log_event(wrapper, "u3", "admin", "ACT3", "TARGET", "T3", {"val": 300})

    # Tamper with row 2 payload directly bypassing triggers if trigger disabled or simulating payload change
    # Note: To simulate database tampering for test, temporarily drop trigger, modify payload, and re-enable trigger
    with audit_db_session.bind.connect() as conn:
        conn.execute(text("DROP TRIGGER trg_prevent_audit_update;"))
        conn.execute(text("UPDATE audit_entries SET payload = '{\"val\": 9999}' WHERE seq = 2;"))
        conn.execute(text("""
            CREATE TRIGGER trg_prevent_audit_update
            BEFORE UPDATE ON audit_entries
            BEGIN
                SELECT RAISE(ABORT, 'Audit trail is strictly append-only. UPDATE operations are forbidden.');
            END;
        """))
        conn.commit()

    # Chain verification must now fail at seq 2
    result = await AuditService.verify_chain(wrapper)
    assert result["valid"] is False
    assert result["checked"] == 1
    assert result["first_broken_seq"] == 2


@pytest.mark.asyncio
async def test_audit_chain_detects_tampered_hash_and_broken_sequence(audit_db_session):
    wrapper = AsyncSessionWrapper(audit_db_session)

    await AuditService.log_event(wrapper, "u1", "admin", "ACT1", "TARGET", "T1", {"val": 1})
    await AuditService.log_event(wrapper, "u2", "admin", "ACT2", "TARGET", "T2", {"val": 2})
    await AuditService.log_event(wrapper, "u3", "admin", "ACT3", "TARGET", "T3", {"val": 3})

    # Simulate tampering with current_hash of seq 1
    with audit_db_session.bind.connect() as conn:
        conn.execute(text("DROP TRIGGER trg_prevent_audit_update;"))
        conn.execute(text("UPDATE audit_entries SET current_hash = 'tampered_hash_value' WHERE seq = 1;"))
        conn.execute(text("""
            CREATE TRIGGER trg_prevent_audit_update
            BEFORE UPDATE ON audit_entries
            BEGIN
                SELECT RAISE(ABORT, 'Audit trail is strictly append-only. UPDATE operations are forbidden.');
            END;
        """))
        conn.commit()

    # Verification fails at seq 1
    result = await AuditService.verify_chain(wrapper)
    assert result["valid"] is False
    assert result["checked"] == 0
    assert result["first_broken_seq"] == 1


@pytest.mark.asyncio
async def test_trigger_strictly_prevents_update_and_delete(audit_db_session):
    wrapper = AsyncSessionWrapper(audit_db_session)
    await AuditService.log_event(wrapper, "admin", "admin", "INIT", "SYSTEM", "SYS1", {})

    # Attempt direct UPDATE -> Must be aborted by trigger
    with pytest.raises(Exception) as exc_update:
        audit_db_session.execute(text("UPDATE audit_entries SET actor = 'hacker' WHERE seq = 1;"))
        audit_db_session.commit()
    assert "Audit trail is strictly append-only" in str(exc_update.value)

    audit_db_session.rollback()

    # Attempt direct DELETE -> Must be aborted by trigger
    with pytest.raises(Exception) as exc_delete:
        audit_db_session.execute(text("DELETE FROM audit_entries WHERE seq = 1;"))
        audit_db_session.commit()
    assert "Audit trail is strictly append-only" in str(exc_delete.value)


# =========================================================================
# Integration Tests: Endpoints & Automatic Event Logging
# =========================================================================

@pytest.mark.asyncio
async def test_automatic_logging_of_login_and_document_reads(audit_client: AsyncClient):
    # 1. Login should automatically write an audit entry
    login_res = await audit_client.post(
        "/api/auth/login",
        json={"email": "admin@aicte.gov.in", "password": "Admin@Fixora2026!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Document read should automatically write an audit entry
    doc_res = await audit_client.get("/api/documents/D-001", headers=headers)
    assert doc_res.status_code == 200

    # 3. Officer action should automatically write an audit entry
    action_res = await audit_client.post(
        "/api/findings/F-2024-000001/actions",
        headers=headers,
        json={
            "action": "request_rectification",
            "reason": "Fire NOC mandatory as per APH Chapter II norms.",
        },
    )
    assert action_res.status_code == 200

    # 4. Check audit log via GET /api/audit
    audit_res = await audit_client.get("/api/audit", headers=headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total"] >= 3

    actions_recorded = [item["action"] for item in audit_data["items"]]
    assert "LOGIN" in actions_recorded
    assert "READ_DOCUMENT" in actions_recorded
    assert "OFFICER_ACTION" in actions_recorded

    # 5. Verify the cryptographic chain
    verify_res = await audit_client.get("/api/audit/verify-chain", headers=headers)
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["valid"] is True
    assert v_data["checked"] >= 3
    assert v_data["first_broken_seq"] is None


@pytest.mark.asyncio
async def test_audit_endpoints_role_permissions(audit_client: AsyncClient):
    tokens = {
        "admin": create_access_token({"sub": "1", "role": "admin"}),
        "scrutiny_officer": create_access_token({"sub": "2", "role": "scrutiny_officer"}),
        "verification_officer": create_access_token({"sub": "3", "role": "verification_officer"}),
        "institution": create_access_token({"sub": "4", "role": "institution", "institution_id": "1-33276541"}),
    }

    # GET /api/audit and GET /api/audit/verify-chain are visible only to scrutiny_officer and admin
    for role, token in tokens.items():
        headers = {"Authorization": f"Bearer {token}"}

        res_list = await audit_client.get("/api/audit", headers=headers)
        res_verify = await audit_client.get("/api/audit/verify-chain", headers=headers)

        if role in ("admin", "scrutiny_officer"):
            assert res_list.status_code == 200, f"Role {role} should access /api/audit"
            assert res_verify.status_code == 200, f"Role {role} should access /api/audit/verify-chain"
        else:
            assert res_list.status_code == 403, f"Role {role} should be forbidden on /api/audit"
            assert res_list.json()["error"]["code"] == "FORBIDDEN"

            assert res_verify.status_code == 403, f"Role {role} should be forbidden on /api/audit/verify-chain"
            assert res_verify.json()["error"]["code"] == "FORBIDDEN"
