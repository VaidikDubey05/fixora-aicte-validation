from typing import Generic, List, TypeVar
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    def Field(default=..., **kwargs):
        return default

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of error")


class ErrorResponse(BaseModel):
    """Standard error response envelope matching RULES.md."""
    error: ErrorDetail


class PaginatedList(BaseModel, Generic[T]):
    """Standard list envelope matching RULES.md."""
    items: List[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
