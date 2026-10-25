from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.database import get_mongo_db
from app.core.mongo_collections import (
    COLLECTION_APH_CHUNKS,
    COLLECTION_EXTRACTION_RUNS,
    COLLECTION_OCR_PAGES,
)


class MongoRepository:
    """Helper repository for MongoDB document & evidence storage."""

    @staticmethod
    async def save_ocr_page(
        document_id: str,
        page: int,
        text: str,
        words: List[Dict[str, Any]],
        engine: str = "tesseract-5.3-eng+hin",
    ) -> Dict[str, Any]:
        """
        Saves or updates OCR extracted page.
        Structure: {document_id, page, text, words[{text,bbox,conf}], engine, created_at}
        """
        db = get_mongo_db()
        col = db[COLLECTION_OCR_PAGES]
        doc = {
            "document_id": document_id,
            "page": page,
            "text": text,
            "words": words,
            "engine": engine,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await col.update_one(
            {"document_id": document_id, "page": page},
            {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        return doc

    @staticmethod
    async def get_ocr_page(document_id: str, page: int) -> Optional[Dict[str, Any]]:
        db = get_mongo_db()
        col = db[COLLECTION_OCR_PAGES]
        return await col.find_one({"document_id": document_id, "page": page}, {"_id": 0})

    @staticmethod
    async def get_document_ocr_pages(document_id: str) -> List[Dict[str, Any]]:
        db = get_mongo_db()
        col = db[COLLECTION_OCR_PAGES]
        cursor = col.find({"document_id": document_id}, {"_id": 0}).sort("page", 1)
        return await cursor.to_list(length=1000)

    @staticmethod
    async def record_extraction_run(
        run_id: str,
        document_id: str,
        application_id: str,
        model_name: str,
        model_version: str,
        status: str,
        extracted_fields_count: int,
        duration_ms: float,
        error_message: Optional[str] = None,
        raw_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Records an ML extraction pipeline run."""
        db = get_mongo_db()
        col = db[COLLECTION_EXTRACTION_RUNS]
        entry = {
            "run_id": run_id,
            "document_id": document_id,
            "application_id": application_id,
            "model_name": model_name,
            "model_version": model_version,
            "status": status,
            "extracted_fields_count": extracted_fields_count,
            "duration_ms": duration_ms,
            "error_message": error_message,
            "raw_output": raw_output or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await col.insert_one(entry)
        entry.pop("_id", None)
        return entry

    @staticmethod
    async def store_aph_chunk(
        chunk_id: str,
        section: str,
        page: int,
        text: str,
        embedding_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stores AICTE Approval Process Handbook (APH) handbook chunk with embedding index reference.
        Structure: {section, page, text, embedding_id}
        """
        db = get_mongo_db()
        col = db[COLLECTION_APH_CHUNKS]
        chunk = {
            "chunk_id": chunk_id,
            "section": section,
            "page": page,
            "text": text,
            "embedding_id": embedding_id,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await col.update_one(
            {"chunk_id": chunk_id},
            {"$set": chunk},
            upsert=True,
        )
        return chunk
