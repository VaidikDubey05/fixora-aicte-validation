"""
Fixora Handbook Assistant RAG Service
Implements:
1. Top-5 vector chunk retrieval against FAISS/term-vector index.
2. Similarity threshold gating: answers exactly "I could not find this in the handbook" if below threshold.
3. Extractive answer synthesis with citations [{section, page, snippet}].
4. Application finding explanation from Finding objects with structured templates.
5. Untrusted input and document instruction boundary fences (prompt injection defense).
6. Strict institution scoping and cryptographic audit logging.
"""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload
    from app.models.entities import Application, Finding, User
    HAS_SQLALCHEMY = True
except ImportError:
    select = None
    AsyncSession = Any  # type: ignore
    selectinload = None
    Application = None  # type: ignore
    Finding = None  # type: ignore
    User = None  # type: ignore
    HAS_SQLALCHEMY = False

from app.core.config import settings
from app.core.logging import logger
from app.models.enums import FindingTypeEnum, RoleEnum
from app.rag.ingest import APHIngestionService
from app.services.audit import AuditService

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_NEURAL_RAG = True
except ImportError:
    HAS_NEURAL_RAG = False


OUT_OF_SCOPE_RESPONSE = "I could not find this in the handbook"


class RAGService:
    """
    Approval Process Handbook Assistant RAG Engine.
    """

    SIMILARITY_THRESHOLD = 0.22  # Configurable threshold

    _cached_metadata: Optional[List[Dict[str, Any]]] = None
    _cached_index: Optional[Any] = None
    _cached_model: Optional[Any] = None

    @classmethod
    def load_index_and_metadata(cls) -> Tuple[Any, List[Dict[str, Any]]]:
        """Loads vector index and chunk metadata from disk."""
        if cls._cached_metadata is None:
            if not APHIngestionService.METADATA_PATH.exists():
                APHIngestionService.ingest_all_pdfs()

            with open(APHIngestionService.METADATA_PATH, "r", encoding="utf-8") as f:
                cls._cached_metadata = json.load(f)

        if cls._cached_index is None:
            if not APHIngestionService.INDEX_PATH.exists():
                APHIngestionService.ingest_all_pdfs()

            if HAS_NEURAL_RAG and not str(APHIngestionService.INDEX_PATH).endswith(".json"):
                try:
                    cls._cached_index = faiss.read_index(str(APHIngestionService.INDEX_PATH))
                    cls._cached_model = SentenceTransformer(APHIngestionService.MODEL_NAME)
                except Exception:
                    with open(APHIngestionService.INDEX_PATH, "r", encoding="utf-8") as f:
                        cls._cached_index = json.load(f)
            else:
                with open(APHIngestionService.INDEX_PATH, "r", encoding="utf-8") as f:
                    cls._cached_index = json.load(f)

        return cls._cached_index, cls._cached_metadata

    @classmethod
    def retrieve_chunks(cls, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Retrieves top_k chunks matching query with similarity scores.
        """
        index, metadata = cls.load_index_and_metadata()
        clean_query = cls._sanitize_untrusted_input(query)

        if HAS_NEURAL_RAG and isinstance(index, faiss.Index):
            model = cls._cached_model or SentenceTransformer(APHIngestionService.MODEL_NAME)
            query_vec = model.encode([clean_query], convert_to_numpy=True, normalize_embeddings=True)
            scores, indices = index.search(query_vec, top_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if 0 <= idx < len(metadata):
                    results.append((metadata[idx], float(score)))
            return results

        # Fallback term-vector / cosine search
        if isinstance(index, dict) and index.get("type") == "lightweight_tfidf":
            token_pattern = re.compile(r"\b[a-zA-Z0-9_\-\.]{3,}\b")
            q_tokens = token_pattern.findall(clean_query.lower())
            if not q_tokens:
                return []

            q_tf: Dict[str, float] = {}
            for t in q_tokens:
                q_tf[t] = q_tf.get(t, 0.0) + 1.0

            doc_freqs = index["doc_freqs"]
            n_docs = index["n_docs"]

            q_vec: Dict[str, float] = {}
            norm_sq = 0.0
            for t, count in q_tf.items():
                idf = math.log((n_docs + 1) / (doc_freqs.get(t, 1) + 1)) + 1.0
                val = count * idf
                q_vec[t] = val
                norm_sq += val * val
            norm = math.sqrt(norm_sq) or 1.0
            for t in q_vec:
                q_vec[t] /= norm

            scored = []
            for chunk_dict, doc_vec in zip(metadata, index["vectors"]):
                # Cosine similarity between normalized unit vectors
                sim = sum(weight * doc_vec.get(term, 0.0) for term, weight in q_vec.items())
                scored.append((chunk_dict, sim))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

        return []

    @classmethod
    async def answer_query(
        cls,
        message: str,
        user: User,
        db: AsyncSession,
        application_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes safe APH question answering with citations and finding inquiries.
        """
        clean_message = cls._sanitize_untrusted_input(message)

        # 1. Institution scoping check
        target_app: Optional[Application] = None
        if application_id:
            if not HAS_SQLALCHEMY or select is None:
                target_app = getattr(db, "_app", None)
            else:
                stmt = (
                    select(Application)
                    .options(selectinload(Application.findings).selectinload(Finding.evidence))
                    .where(Application.id == application_id)
                )
                res = await db.execute(stmt)
                target_app = res.scalar_one_or_none()

            if not target_app:
                return {
                    "response": f"Application '{application_id}' not found.",
                    "citations": [],
                    "application_id": application_id,
                }

            if user.role == RoleEnum.INSTITUTION:
                if target_app.institution_id != user.institution_id:
                    raise PermissionError(f"Access forbidden: cannot query application '{application_id}'.")

        # 2. Check if this is a finding explanation inquiry
        if target_app and cls._is_finding_inquiry(clean_message):
            explanation_data = cls._generate_finding_explanation(clean_message, target_app, user)
            # Log audit event
            await AuditService.log_event(
                db=db,
                actor=user.email,
                role=user.role.value,
                action="CHAT_QUERY",
                target_type="APPLICATION",
                target_id=target_app.id,
                payload={
                    "query": clean_message,
                    "type": "finding_explanation",
                    "application_id": target_app.id,
                    "cited_chunk_ids": [],
                },
            )
            return explanation_data

        # 3. Retrieve handbook chunks
        retrieved = cls.retrieve_chunks(clean_message, top_k=5)

        if not retrieved or retrieved[0][1] < cls.SIMILARITY_THRESHOLD:
            # Audit log out-of-scope query
            await AuditService.log_event(
                db=db,
                actor=user.email,
                role=user.role.value,
                action="CHAT_QUERY",
                target_type="HANDBOOK",
                target_id="AICTE-APH-2024-25",
                payload={"query": clean_message, "best_score": retrieved[0][1] if retrieved else 0.0, "cited_chunk_ids": []},
            )
            return {
                "response": OUT_OF_SCOPE_RESPONSE,
                "citations": [],
                "application_id": application_id,
            }

        top_chunk, best_score = retrieved[0]

        # 4. Synthesize extractive answer from top chunks
        citations = []
        cited_chunk_ids = []
        response_paragraphs = []

        # Take relevant chunks (scores within 70% of best score)
        relevant_chunks = [c for c in retrieved if c[1] >= (best_score * 0.70)][:3]

        for chunk_data, score in relevant_chunks:
            snippet = cls._extract_best_snippet(chunk_data["text"], clean_message)
            citations.append({
                "chunk_id": chunk_data["chunk_id"],
                "section": chunk_data["section"],
                "chapter": chunk_data.get("chapter", ""),
                "page": chunk_data["page"],
                "snippet": snippet,
                "relevance_score": round(score, 3),
            })
            cited_chunk_ids.append(chunk_data["chunk_id"])

        extractive_summary = cls._build_extractive_answer(citations, clean_message)

        # 5. Audit Logging
        await AuditService.log_event(
            db=db,
            actor=user.email,
            role=user.role.value,
            action="CHAT_QUERY",
            target_type="HANDBOOK",
            target_id="AICTE-APH-2024-25",
            payload={
                "query": clean_message,
                "application_id": application_id,
                "cited_chunk_ids": cited_chunk_ids,
                "best_score": round(best_score, 3),
            },
        )

        return {
            "response": extractive_summary or top_chunk["text"],
            "citations": citations,
            "application_id": application_id,
        }

    @staticmethod
    def _sanitize_untrusted_input(text: str) -> str:
        """
        Guards against prompt injection and tool execution triggers.
        Treats all user and document text as untrusted.
        """
        # Strip control characters and command escapes
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Neutralize common injection prefixes
        cleaned = re.sub(r"(?i)(ignore previous instructions|disregard all|system:|<\/?system>|```json|```python)", " ", cleaned)
        return cleaned.strip()

    @staticmethod
    def _is_finding_inquiry(message: str) -> bool:
        """Detects if message is asking why an application or item was flagged."""
        inquiry_keywords = [
            "why was", "why is", "flagged", "deficiency", "deficiencies",
            "issue", "rejected", "mismatch", "failed", "finding", "problem",
            "explain finding", "rectification"
        ]
        lower_msg = message.lower()
        return any(kw in lower_msg for kw in inquiry_keywords)

    @classmethod
    def _generate_finding_explanation(
        cls,
        message: str,
        app: Application,
        user: User,
    ) -> Dict[str, Any]:
        """
        Explains flagged findings from Finding objects with a deterministic template.
        Institution users never see anomaly/duplicate findings.
        """
        is_inst = user.role == RoleEnum.INSTITUTION
        findings = [
            f for f in app.findings
            if not (is_inst and f.type in (FindingTypeEnum.POSSIBLE_ANOMALY, FindingTypeEnum.DUPLICATE))
        ]

        if not findings:
            return {
                "response": f"Application {app.id} currently has no active deficiency findings or flags recorded.",
                "citations": [],
                "application_id": app.id,
            }

        # Filter by keyword if user asked about specific finding (e.g. fire, land, intake)
        lower_msg = message.lower()
        matched_findings = [f for f in findings if any(w in f.title.lower() or w in f.reason.lower() for w in lower_msg.split())]
        target_findings = matched_findings if matched_findings else findings

        lines = [f"Summary of statutory observations for Application {app.id}:"]
        for idx, f in enumerate(target_findings[:3], 1):
            rule_str = f" [Rule: {', '.join(f.rule_refs)}]" if f.rule_refs else ""
            lines.append(f"{idx}. {f.title}: {f.reason}{rule_str}")
            if f.evidence:
                ev = f.evidence[0]
                lines.append(f"   - Evidence: Declared {ev.field or 'value'}: '{ev.value}'.")

        lines.append("\nNote: These observations represent decision support. Authorised council officers decide final statutory status.")
        return {
            "response": "\n".join(lines),
            "citations": [],
            "application_id": app.id,
        }

    @staticmethod
    def _extract_best_snippet(text: str, query: str) -> str:
        """Extracts the most relevant 2-sentence snippet from chunk text."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        q_words = set(query.lower().split())

        best_sent = sentences[0] if sentences else text[:150]
        max_overlap = -1

        for sent in sentences:
            overlap = len(set(sent.lower().split()).intersection(q_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_sent = sent

        return best_sent.strip()

    @staticmethod
    def _build_extractive_answer(citations: List[Dict[str, Any]], query: str) -> str:
        """Synthesizes clear extractive response referencing statutory sections."""
        if not citations:
            return OUT_OF_SCOPE_RESPONSE

        lead = citations[0]
        response_parts = [
            f"According to {lead['section']} of the AICTE Approval Process Handbook (Page {lead['page']}):",
            lead["snippet"]
        ]

        if len(citations) > 1:
            sec = citations[1]
            response_parts.append(f"Furthermore, under {sec['section']} (Page {sec['page']}), {sec['snippet']}")

        return " ".join(response_parts)
