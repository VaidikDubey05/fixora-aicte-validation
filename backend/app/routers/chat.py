"""
Fixora Handbook Assistant Chat Router
Exposes POST /api/chat for statutory Approval Process Handbook inquiries,
citations, and application finding explanations.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.entities import User
from app.models.enums import RoleEnum
from app.rag.rag_service import RAGService

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Statutory question or finding inquiry")
    application_id: Optional[str] = Field(None, description="Optional application context ID (APP-EOA-YYYY-NNNNN)")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Optional conversation turns")


class CitationItem(BaseModel):
    chunk_id: Optional[str] = None
    section: str
    chapter: Optional[str] = None
    page: int
    snippet: str
    relevance_score: Optional[float] = None


class ChatResponse(BaseModel):
    response: str
    citations: List[CitationItem] = Field(default_factory=list)
    application_id: Optional[str] = None


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Handbook assistant statutory QA and finding explanation",
)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approval Process Handbook (APH) Assistant:
    1. Retrieves top 5 handbook chunks via dense FAISS / term-vector index.
    2. Answers with citations [{section, page, snippet}].
    3. If query is outside handbook scope, responds exactly 'I could not find this in the handbook'.
    4. If application_id is provided and asks about flags/deficiencies, explains using Finding objects.
    5. Enforces institution scoping: institutions may only inspect their own applications.
    6. Treats all retrieved text and user inputs as untrusted (prompt injection defense).
    7. Logs all queries and cited chunk IDs to the audit trail.
    """
    try:
        history_dicts = [h.model_dump() for h in request.history] if request.history else []
        result = await RAGService.answer_query(
            message=request.message,
            user=current_user,
            db=db,
            application_id=request.application_id,
            history=history_dicts,
        )
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Handbook assistant error: {str(exc)}",
        )
