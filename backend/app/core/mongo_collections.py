from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
try:
    from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel
    HAS_PYMONGO = True
except ImportError:
    ASCENDING = 1
    DESCENDING = -1
    TEXT = "text"
    IndexModel = Any
    HAS_PYMONGO = False
from app.core.database import get_mongo_db
from app.core.logging import logger

COLLECTION_OCR_PAGES = "ocr_pages"
COLLECTION_EXTRACTION_RUNS = "extraction_runs"
COLLECTION_APH_CHUNKS = "aph_chunks"


async def init_mongo_indexes() -> Dict[str, List[str]]:
    """
    Initializes required MongoDB collections and creates optimized indexes for:
    - ocr_pages: {document_id, page, text, words[{text,bbox,conf}], engine}
    - extraction_runs: {run_id, document_id, model_name, model_version, status, ...}
    - aph_chunks: {section, page, text, embedding_id, ...}
    """
    db = get_mongo_db()
    created_indexes: Dict[str, List[str]] = {}

    try:
        # 1. ocr_pages collection
        ocr_col = db[COLLECTION_OCR_PAGES]
        ocr_indexes = [
            IndexModel(
                [("document_id", ASCENDING), ("page", ASCENDING)],
                unique=True,
                name="uq_doc_page",
            ),
            IndexModel([("document_id", ASCENDING)], name="idx_ocr_doc_id"),
            IndexModel([("text", TEXT)], name="idx_ocr_text_search"),
        ]
        res_ocr = await ocr_col.create_indexes(ocr_indexes)
        created_indexes[COLLECTION_OCR_PAGES] = res_ocr

        # 2. extraction_runs collection
        ext_col = db[COLLECTION_EXTRACTION_RUNS]
        ext_indexes = [
            IndexModel([("run_id", ASCENDING)], unique=True, name="uq_run_id"),
            IndexModel(
                [("document_id", ASCENDING), ("created_at", DESCENDING)],
                name="idx_ext_doc_created",
            ),
            IndexModel([("application_id", ASCENDING)], name="idx_ext_app_id"),
        ]
        res_ext = await ext_col.create_indexes(ext_indexes)
        created_indexes[COLLECTION_EXTRACTION_RUNS] = res_ext

        # 3. aph_chunks collection
        aph_col = db[COLLECTION_APH_CHUNKS]
        aph_indexes = [
            IndexModel(
                [("section", ASCENDING), ("page", ASCENDING)],
                name="idx_aph_section_page",
            ),
            IndexModel([("embedding_id", ASCENDING)], name="idx_aph_embedding_id"),
            IndexModel([("text", TEXT)], name="idx_aph_text_search"),
        ]
        res_aph = await aph_col.create_indexes(aph_indexes)
        created_indexes[COLLECTION_APH_CHUNKS] = res_aph

        logger.info("MongoDB collections and indexes initialized successfully", extra={"indexes": created_indexes})
        return created_indexes

    except Exception as exc:
        logger.error("Failed to initialize MongoDB indexes", exc_info=exc)
        raise exc
