from typing import Optional
try:
    from pydantic import BaseModel, EmailStr, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    def Field(default=..., **kwargs):
        return default
    EmailStr = str

from app.models.enums import RoleEnum


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserResponse(BaseModel):
    id: int
    email: str
    role: RoleEnum
    institution_id: Optional[str] = None
    full_name: str
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 60 minutes in seconds
    user: UserResponse
