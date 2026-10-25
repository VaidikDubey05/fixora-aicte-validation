from app.routers.applications import router as applications_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.demo import router as demo_router
from app.routers.health import router as health_router
from app.routers.rule_packs import router as rule_packs_router

__all__ = [
    "health_router",
    "auth_router",
    "applications_router",
    "audit_router",
    "rule_packs_router",
    "demo_router",
]
