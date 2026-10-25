from typing import Optional
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    def Field(default=..., **kwargs):
        return default


class ServiceConnectivity(BaseModel):
    status: str = Field(..., description="Service connection state ('connected' or 'unavailable')")
    details: Optional[str] = Field(None, description="Diagnostic details or error message")
    latency_ms: Optional[float] = Field(None, description="Round-trip check duration in milliseconds")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall health state ('ok' or 'degraded')")
    environment: str = Field(..., description="Current environment setting")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of the health check")
    postgres: ServiceConnectivity
    mongodb: ServiceConnectivity
