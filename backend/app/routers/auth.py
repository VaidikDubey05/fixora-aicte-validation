from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import login_rate_limiter
from app.core.security import create_access_token, verify_password
from app.models.entities import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT access token",
)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates user credentials and issues a 60-minute JWT bearer token.
    Applies sliding-window rate limiting per client IP / email.
    """
    # 1. Apply basic rate limiting
    login_rate_limiter.check_rate_limit(request, identifier=payload.email)

    # 2. Query user by email
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    # 3. Create 60-minute access token
    token_payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "institution_id": user.institution_id,
    }
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(token_payload, expires_delta=expires_delta)

    # 4. Record statutory audit trail entry for authentication event
    client_ip = request.headers.get("X-Forwarded-For") or (request.client.host if request.client else "127.0.0.1")
    from app.services.audit import AuditService
    await AuditService.log_event(
        db=db,
        actor=user.email,
        role=user.role.value,
        action="LOGIN",
        target_type="USER",
        target_id=str(user.id),
        payload={"email": user.email, "role": user.role.value, "institution_id": user.institution_id},
        ip_address=client_ip,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            institution_id=user.institution_id,
            full_name=user.full_name,
            is_active=user.is_active,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Returns the profile information of the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        institution_id=current_user.institution_id,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
    )
