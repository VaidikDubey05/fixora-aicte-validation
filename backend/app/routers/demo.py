from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.seed import reset_demo_data, seed_demo_data

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_demo(db: AsyncSession = Depends(get_db)):
    """Seeds synthetic demo institutions, users per role, applications, and documents."""
    result = await seed_demo_data(db)
    return {
        "status": "seeded",
        "counts": result,
        "message": "Demo users, institutions, and applications successfully populated.",
    }


@router.post("/reset")
async def reset_demo(db: AsyncSession = Depends(get_db)):
    """Resets demo environment state, purges generated applications and clears encrypted storage."""
    result = await reset_demo_data(db)
    return result
