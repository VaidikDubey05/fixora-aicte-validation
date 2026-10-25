import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import check_institution_access, get_db
from app.core.config import settings
from app.core.masking import (
    mask_aadhaar,
    mask_dict,
    mask_email,
    mask_pan,
    mask_phone,
)
from app.core.rate_limit import LoginRateLimiter, login_rate_limiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.main import app
from app.models.base import Base
from app.models.entities import Application, Document, Institution, User
from app.models.enums import ApplicationStateEnum, RoleEnum, ScanStatusEnum


# =========================================================================
# Unit Tests: PII Masking Helpers
# =========================================================================

def test_mask_email():
    assert mask_email("principal@gecpune.edu.in") == "p***l@gecpune.edu.in"
    assert mask_email("ab@domain.com") == "a*@domain.com"
    assert mask_email("x@domain.com") == "x*@domain.com"
    assert mask_email("notanemail") == "[REDACTED]"
    assert mask_email(None) == "[REDACTED]"


def test_mask_phone():
    assert mask_phone("+91 9876543210") == "+91 ******3210"
    assert mask_phone("9876543210") == "******3210"
    assert mask_phone("123") == "****"
    assert mask_phone(None) == "[REDACTED]"


def test_mask_aadhaar():
    assert mask_aadhaar("1234 5678 9012") == "XXXX-XXXX-9012"
    assert mask_aadhaar("123456789012") == "XXXX-XXXX-9012"
    assert mask_aadhaar("12") == "XXXX-XXXX-XXXX"
    assert mask_aadhaar(None) == "[REDACTED]"


def test_mask_pan():
    assert mask_pan("ABCDE1234F") == "ABCDE****F"
    assert mask_pan("INVALID") == "[REDACTED]"
    assert mask_pan(None) == "[REDACTED]"


def test_mask_dict_recursive():
    sample_data = {
        "institution_name": "Government Engineering College, Pune",
        "email": "contact@gecpune.edu.in",
        "phone": "+91 9876543210",
        "password": "SecretPassword123!",
        "trustee": {
            "name": "Dr. A. K. Sharma",
            "aadhaar": "9876 5432 1098",
            "pan": "BNZPK1234M",
            "contact_email": "trustee@gecpune.edu.in",
            "account_number": "12345678901234",
        },
        "programmes": [
            {"name": "Computer Engineering", "hod_phone": "+91 9123456789"}
        ],
    }

    masked = mask_dict(sample_data)

    assert masked["institution_name"] == "Government Engineering College, Pune"
    assert masked["email"] == "c***t@gecpune.edu.in"
    assert masked["phone"] == "+91 ******3210"
    assert masked["password"] == "[REDACTED]"
    assert masked["trustee"]["aadhaar"] == "XXXX-XXXX-1098"
    assert masked["trustee"]["pan"] == "BNZPK****M"
    assert masked["trustee"]["contact_email"] == "t***e@gecpune.edu.in"
    assert masked["trustee"]["account_number"] == "**********1234"
    assert masked["programmes"][0]["hod_phone"] == "+91 ******6789"


# =========================================================================
# Unit Tests: Security & Password Hashing & Rate Limiting
# =========================================================================

def test_password_hashing_and_verification():
    raw_pwd = "DemoPassword@2026!"
    hashed = hash_password(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw_pwd, "") is False


def test_jwt_access_token_creation_and_expiration():
    payload = {"sub": "101", "role": "admin", "institution_id": None}
    # 60 minute token
    token = create_access_token(payload, expires_delta=timedelta(minutes=60))
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "101"
    assert decoded["role"] == "admin"
    assert decoded["institution_id"] is None
    assert "exp" in decoded

    # Expired token
    expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
    assert decode_access_token(expired_token) is None


def test_login_rate_limiter_sliding_window():
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client.host = "192.168.1.50"

    # 3 attempts allowed
    limiter.check_rate_limit(mock_request, identifier="test@example.com")
    limiter.check_rate_limit(mock_request, identifier="test@example.com")
    limiter.check_rate_limit(mock_request, identifier="test@example.com")

    # 4th attempt must raise HTTP 429
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit(mock_request, identifier="test@example.com")
    assert exc_info.value.status_code == 429
    assert "Too many login attempts" in exc_info.value.detail


# =========================================================================
# Async Test Fixture & In-Memory Database Session Wrapper
# =========================================================================

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


@pytest.fixture
def test_db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSessionLocal()

    # Seed test institutions
    inst1 = Institution(
        id="1-33276541",
        name="Government Engineering College, Pune",
        address="Campus Road",
        state="Maharashtra",
        district="Pune",
        pin_code="411001",
        contact_email="principal@gecpune.edu.in",
    )
    inst2 = Institution(
        id="1-44589210",
        name="Maharashtra Institute of Technology, Mumbai",
        address="BKC Road",
        state="Maharashtra",
        district="Mumbai",
        pin_code="400001",
        contact_email="director@mitmumbai.edu.in",
    )
    session.add_all([inst1, inst2])
    session.flush()

    # Seed test users
    admin_user = User(
        id=1,
        email="admin@aicte.gov.in",
        hashed_password=hash_password("Admin@Fixora2026!"),
        role=RoleEnum.ADMIN,
        full_name="AICTE Admin",
        institution_id=None,
    )
    scrutiny_user = User(
        id=2,
        email="scrutiny@aicte.gov.in",
        hashed_password=hash_password("Scrutiny@Fixora2026!"),
        role=RoleEnum.SCRUTINY_OFFICER,
        full_name="Dr. Scrutiny",
        institution_id=None,
    )
    verif_user = User(
        id=3,
        email="verification@aicte.gov.in",
        hashed_password=hash_password("Verification@Fixora2026!"),
        role=RoleEnum.VERIFICATION_OFFICER,
        full_name="Smt. Verifier",
        institution_id=None,
    )
    inst1_user = User(
        id=4,
        email="principal@gecpune.edu.in",
        hashed_password=hash_password("Inst1@Fixora2026!"),
        role=RoleEnum.INSTITUTION,
        full_name="Principal GEC",
        institution_id="1-33276541",
    )
    inst2_user = User(
        id=5,
        email="director@mitmumbai.edu.in",
        hashed_password=hash_password("Inst2@Fixora2026!"),
        role=RoleEnum.INSTITUTION,
        full_name="Director MIT",
        institution_id="1-44589210",
    )
    session.add_all([admin_user, scrutiny_user, verif_user, inst1_user, inst2_user])
    session.flush()

    # Seed test applications
    app1 = Application(
        id="APP-EOA-2024-00001",
        institution_id="1-33276541",
        category="ENGINEERING_AND_TECHNOLOGY",
        academic_year="2024-2025",
        checklist_pack_version="aph-2024-25-v1",
        state=ApplicationStateEnum.SUBMITTED,
        priority_score=15.0,
        form_data={"programmes": ["Computer Engineering"]},
    )
    app2 = Application(
        id="APP-EOA-2024-00002",
        institution_id="1-44589210",
        category="MANAGEMENT",
        academic_year="2024-2025",
        checklist_pack_version="aph-2024-25-v1",
        state=ApplicationStateEnum.READY_FOR_SCRUTINY,
        priority_score=25.0,
        form_data={"programmes": ["MBA"]},
    )
    session.add_all([app1, app2])
    session.flush()

    # Seed test documents
    doc1 = Document(
        id="D-001",
        application_id=app1.id,
        class_name="land_title_deed",
        file_ref="/storage/doc1.pdf",
        sha256="hash1",
        page_count=5,
        scan_status=ScanStatusEnum.COMPLETED,
    )
    doc2 = Document(
        id="D-002",
        application_id=app2.id,
        class_name="occupancy_certificate",
        file_ref="/storage/doc2.pdf",
        sha256="hash2",
        page_count=3,
        scan_status=ScanStatusEnum.COMPLETED,
    )
    session.add_all([doc1, doc2])
    session.commit()

    yield session
    session.close()


@pytest.fixture
async def auth_client(test_db_session):
    async def override_get_db():
        yield AsyncSessionWrapper(test_db_session)

    app.dependency_overrides[get_db] = override_get_db
    login_rate_limiter.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =========================================================================
# Integration Tests: Auth Endpoints & Token Authentication
# =========================================================================

@pytest.mark.asyncio
async def test_login_success_and_token_shape(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/auth/login",
        json={"email": "admin@aicte.gov.in", "password": "Admin@Fixora2026!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
    assert data["user"]["email"] == "admin@aicte.gov.in"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_invalid_password(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/auth/login",
        json={"email": "admin@aicte.gov.in", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Invalid email or password" in data["error"]["message"]


@pytest.mark.asyncio
async def test_login_rate_limiting(auth_client: AsyncClient):
    login_rate_limiter.reset()
    # 5 attempts allowed by default
    for _ in range(5):
        await auth_client.post(
            "/api/auth/login",
            json={"email": "admin@aicte.gov.in", "password": "WrongPassword!"},
        )

    # 6th attempt must trigger HTTP 429 RATE_LIMIT_EXCEEDED
    response = await auth_client.post(
        "/api/auth/login",
        json={"email": "admin@aicte.gov.in", "password": "WrongPassword!"},
    )
    assert response.status_code == 429
    data = response.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    login_rate_limiter.reset()


@pytest.mark.asyncio
async def test_get_me_endpoint(auth_client: AsyncClient):
    # 1. Unauthenticated request -> 401
    unauth_res = await auth_client.get("/api/auth/me")
    assert unauth_res.status_code == 401
    assert unauth_res.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Authenticated request -> 200
    token = create_access_token({"sub": "4", "email": "principal@gecpune.edu.in", "role": "institution"})
    auth_res = await auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_res.status_code == 200
    user_info = auth_res.json()
    assert user_info["id"] == 4
    assert user_info["email"] == "principal@gecpune.edu.in"
    assert user_info["role"] == "institution"
    assert user_info["institution_id"] == "1-33276541"


# =========================================================================
# RBAC Tests: Every Role Against Every Protected Route Group
# =========================================================================

@pytest.mark.asyncio
async def test_every_role_against_protected_route_groups(auth_client: AsyncClient):
    tokens = {
        "admin": create_access_token({"sub": "1", "role": "admin"}),
        "scrutiny_officer": create_access_token({"sub": "2", "role": "scrutiny_officer"}),
        "verification_officer": create_access_token({"sub": "3", "role": "verification_officer"}),
        "institution": create_access_token({"sub": "4", "role": "institution", "institution_id": "1-33276541"}),
    }

    # 1. Scrutiny Queue (/api/scrutiny/queue) -> Allowed: scrutiny_officer, admin
    for role, token in tokens.items():
        headers = {"Authorization": f"Bearer {token}"}
        res = await auth_client.get("/api/scrutiny/queue", headers=headers)
        if role in ("admin", "scrutiny_officer"):
            assert res.status_code == 200, f"Role {role} should access scrutiny queue"
        else:
            assert res.status_code == 403, f"Role {role} should be denied scrutiny queue"
            assert res.json()["error"]["code"] == "FORBIDDEN"

    # 2. Verification Queue (/api/verification/queue) -> Allowed: verification_officer, admin
    for role, token in tokens.items():
        headers = {"Authorization": f"Bearer {token}"}
        res = await auth_client.get("/api/verification/queue", headers=headers)
        if role in ("admin", "verification_officer"):
            assert res.status_code == 200, f"Role {role} should access verification queue"
        else:
            assert res.status_code == 403, f"Role {role} should be denied verification queue"
            assert res.json()["error"]["code"] == "FORBIDDEN"

    # 3. Admin Users Directory (/api/admin/users) -> Allowed: admin only
    for role, token in tokens.items():
        headers = {"Authorization": f"Bearer {token}"}
        res = await auth_client.get("/api/admin/users", headers=headers)
        if role == "admin":
            assert res.status_code == 200, f"Role {role} should access admin users"
        else:
            assert res.status_code == 403, f"Role {role} should be denied admin users"
            assert res.json()["error"]["code"] == "FORBIDDEN"


# =========================================================================
# Statutory Institution Scoping Tests: Cross-Institution Access Denied
# =========================================================================

@pytest.mark.asyncio
async def test_cross_institution_application_access_denied(auth_client: AsyncClient):
    token_inst1 = create_access_token({"sub": "4", "role": "institution", "institution_id": "1-33276541"})
    token_inst2 = create_access_token({"sub": "5", "role": "institution", "institution_id": "1-44589210"})
    token_scrutiny = create_access_token({"sub": "2", "role": "scrutiny_officer"})

    headers_inst1 = {"Authorization": f"Bearer {token_inst1}"}
    headers_inst2 = {"Authorization": f"Bearer {token_inst2}"}
    headers_scrutiny = {"Authorization": f"Bearer {token_scrutiny}"}

    # Inst 1 accessing own application (APP-EOA-2024-00001) -> 200 OK
    res = await auth_client.get("/api/applications/APP-EOA-2024-00001", headers=headers_inst1)
    assert res.status_code == 200
    assert res.json()["id"] == "APP-EOA-2024-00001"

    # Inst 1 attempting cross-institution access to Inst 2's application (APP-EOA-2024-00002) -> 403 FORBIDDEN
    cross_res1 = await auth_client.get("/api/applications/APP-EOA-2024-00002", headers=headers_inst1)
    assert cross_res1.status_code == 403
    assert cross_res1.json()["error"]["code"] == "FORBIDDEN"
    assert "cross-institution" in cross_res1.json()["error"]["message"]

    # Inst 2 accessing own application (APP-EOA-2024-00002) -> 200 OK
    res = await auth_client.get("/api/applications/APP-EOA-2024-00002", headers=headers_inst2)
    assert res.status_code == 200
    assert res.json()["id"] == "APP-EOA-2024-00002"

    # Inst 2 attempting cross-institution access to Inst 1's application (APP-EOA-2024-00001) -> 403 FORBIDDEN
    cross_res2 = await auth_client.get("/api/applications/APP-EOA-2024-00001", headers=headers_inst2)
    assert cross_res2.status_code == 403
    assert cross_res2.json()["error"]["code"] == "FORBIDDEN"

    # Scrutiny officer accessing applications across institutions -> 200 OK for both
    res_app1 = await auth_client.get("/api/applications/APP-EOA-2024-00001", headers=headers_scrutiny)
    res_app2 = await auth_client.get("/api/applications/APP-EOA-2024-00002", headers=headers_scrutiny)
    assert res_app1.status_code == 200
    assert res_app2.status_code == 200


@pytest.mark.asyncio
async def test_cross_institution_document_access_denied(auth_client: AsyncClient):
    token_inst1 = create_access_token({"sub": "4", "role": "institution", "institution_id": "1-33276541"})
    token_inst2 = create_access_token({"sub": "5", "role": "institution", "institution_id": "1-44589210"})
    token_scrutiny = create_access_token({"sub": "2", "role": "scrutiny_officer"})

    headers_inst1 = {"Authorization": f"Bearer {token_inst1}"}
    headers_inst2 = {"Authorization": f"Bearer {token_inst2}"}
    headers_scrutiny = {"Authorization": f"Bearer {token_scrutiny}"}

    # Inst 1 reads own document D-001 -> 200 OK
    res = await auth_client.get("/api/documents/D-001", headers=headers_inst1)
    assert res.status_code == 200

    # Inst 1 reads Inst 2's document D-002 -> 403 FORBIDDEN
    cross_res = await auth_client.get("/api/documents/D-002", headers=headers_inst1)
    assert cross_res.status_code == 403
    assert cross_res.json()["error"]["code"] == "FORBIDDEN"

    # Inst 2 reads own document D-002 -> 200 OK
    res = await auth_client.get("/api/documents/D-002", headers=headers_inst2)
    assert res.status_code == 200

    # Inst 2 reads Inst 1's document D-001 -> 403 FORBIDDEN
    cross_res = await auth_client.get("/api/documents/D-001", headers=headers_inst2)
    assert cross_res.status_code == 403
    assert cross_res.json()["error"]["code"] == "FORBIDDEN"

    # Scrutiny officer reads both documents -> 200 OK
    assert (await auth_client.get("/api/documents/D-001", headers=headers_scrutiny)).status_code == 200
    assert (await auth_client.get("/api/documents/D-002", headers=headers_scrutiny)).status_code == 200


@pytest.mark.asyncio
async def test_list_applications_institution_scoping(auth_client: AsyncClient):
    token_inst1 = create_access_token({"sub": "4", "role": "institution", "institution_id": "1-33276541"})
    token_inst2 = create_access_token({"sub": "5", "role": "institution", "institution_id": "1-44589210"})
    token_scrutiny = create_access_token({"sub": "2", "role": "scrutiny_officer"})

    # Inst 1 only sees their 1 application
    res1 = await auth_client.get("/api/applications", headers={"Authorization": f"Bearer {token_inst1}"})
    assert res1.status_code == 200
    items1 = res1.json()["items"]
    assert len(items1) == 1
    assert items1[0]["institution_id"] == "1-33276541"

    # Inst 2 only sees their 1 application
    res2 = await auth_client.get("/api/applications", headers={"Authorization": f"Bearer {token_inst2}"})
    assert res2.status_code == 200
    items2 = res2.json()["items"]
    assert len(items2) == 1
    assert items2[0]["institution_id"] == "1-44589210"

    # Scrutiny officer sees both applications
    res_scrutiny = await auth_client.get("/api/applications", headers={"Authorization": f"Bearer {token_scrutiny}"})
    assert res_scrutiny.status_code == 200
    assert len(res_scrutiny.json()["items"]) == 2
