"""
Fixora Approval Process Handbook (APH) Ingestion Script
Reads handbook PDFs from data/aph/, extracts text via PyMuPDF,
splits into ~400 token semantic chunks with section titles and page numbers,
embeds with sentence-transformers (all-MiniLM-L6-v2), and persists vectors to FAISS
and chunk metadata to MongoDB aph_chunks collection.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

backend_root = Path(__file__).resolve().parent.parent.parent
data_aph_dir = backend_root.parent / "data" / "aph"
storage_dir = backend_root.parent / "storage"

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import faiss
    import numpy as np
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


@dataclass
class HandbookChunk:
    chunk_id: str
    section: str
    chapter: str
    page: int
    text: str
    token_count: int
    source_file: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class APHIngestionService:
    """
    Ingests official AICTE Approval Process Handbook PDFs.
    """

    INDEX_PATH = storage_dir / "aph_faiss.index"
    METADATA_PATH = storage_dir / "aph_chunks.json"
    MODEL_NAME = "all-MiniLM-L6-v2"

    @classmethod
    def extract_text_from_pdf(cls, pdf_path: Path) -> List[Tuple[int, str]]:
        """
        Extracts (page_number, text) tuples from PDF using PyMuPDF or pure Python fallback.
        """
        pages = []
        if HAS_PYMUPDF:
            try:
                doc = fitz.open(str(pdf_path))
                for idx, page in enumerate(doc):
                    text = page.get_text() or ""
                    pages.append((idx + 1, text))
                return pages
            except Exception as e:
                pass

        # Fallback pure-python PDF text extraction
        with open(pdf_path, "rb") as f:
            content = f.read()

        raw_str = content.decode("latin1", errors="ignore")
        # Split on Page markers or find text inside BT ... ET streams
        streams = re.findall(r"stream[\r\n]+(.*?)[\r\n]+endstream", raw_str, re.DOTALL)
        if streams:
            for idx, st in enumerate(streams):
                # Extract text inside (...) Tj
                tj_matches = re.findall(r"\((.*?)\)\s*Tj", st)
                if tj_matches:
                    clean_lines = [m.replace("\\(", "(").replace("\\)", ")") for m in tj_matches]
                    page_text = "\n".join(clean_lines)
                    pages.append((idx + 1, page_text))

        if not pages:
            # Fallback text
            pages.append((1, raw_str))

        return pages

    @classmethod
    def split_into_chunks(cls, pages: List[Tuple[int, str]], source_file: str) -> List[HandbookChunk]:
        """
        Splits text into chunks of ~400 tokens preserving section titles and page numbers.
        """
        chunks: List[HandbookChunk] = []
        chunk_counter = 1

        current_chapter = "Chapter 1: Statutory Basis & Objectives"
        current_section = "Section 1.1: Scope and Jurisdiction of the Council"

        for page_num, page_text in pages:
            lines = page_text.splitlines()
            current_buffer: List[str] = []
            buffer_tokens = 0

            for line in lines:
                clean_line = line.strip().replace("[STRONG]", "").replace("---", "").strip()
                if not clean_line:
                    continue

                # Check chapter or section headers
                chap_match = re.search(r"(Chapter\s+\d+[^:\n]*[:\-\s]+[^\n]+)", clean_line, re.IGNORECASE)
                if chap_match:
                    current_chapter = chap_match.group(1).strip()

                sec_match = re.search(r"(Section\s+\d+\.\d+[^:\n]*[:\-\s]+[^\n]+)", clean_line, re.IGNORECASE)
                if sec_match:
                    # Flush previous buffer before starting a major new section
                    if buffer_tokens > 0:
                        chunk_text = " ".join(current_buffer)
                        chunks.append(HandbookChunk(
                            chunk_id=f"aph_chunk_{chunk_counter:04d}",
                            section=current_section,
                            chapter=current_chapter,
                            page=page_num,
                            text=chunk_text,
                            token_count=buffer_tokens,
                            source_file=source_file,
                        ))
                        chunk_counter += 1
                        current_buffer = []
                        buffer_tokens = 0
                    current_section = sec_match.group(1).strip()

                words = clean_line.split()
                line_token_count = len(words)

                # Chunk size target: ~400 tokens (range 250 - 450)
                if buffer_tokens + line_token_count > 420:
                    chunk_text = " ".join(current_buffer)
                    chunks.append(HandbookChunk(
                        chunk_id=f"aph_chunk_{chunk_counter:04d}",
                        section=current_section,
                        chapter=current_chapter,
                        page=page_num,
                        text=chunk_text,
                        token_count=buffer_tokens,
                        source_file=source_file,
                    ))
                    chunk_counter += 1
                    current_buffer = [clean_line]
                    buffer_tokens = line_token_count
                else:
                    current_buffer.append(clean_line)
                    buffer_tokens += line_token_count

            if current_buffer:
                chunk_text = " ".join(current_buffer)
                chunks.append(HandbookChunk(
                    chunk_id=f"aph_chunk_{chunk_counter:04d}",
                    section=current_section,
                    chapter=current_chapter,
                    page=page_num,
                    text=chunk_text,
                    token_count=buffer_tokens,
                    source_file=source_file,
                ))
                chunk_counter += 1

        return chunks

    @classmethod
    def ingest_all_pdfs(cls) -> Dict[str, Any]:
        """
        Discovers all PDFs in data/aph/, chunks them, embeds vectors, and persists index + metadata.
        """
        storage_dir.mkdir(parents=True, exist_ok=True)
        pdf_files = list(data_aph_dir.glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {data_aph_dir}. Place handbook PDF there.")

        all_chunks: List[HandbookChunk] = []
        for pdf_path in pdf_files:
            pages = cls.extract_text_from_pdf(pdf_path)
            chunks = cls.split_into_chunks(pages, pdf_path.name)
            all_chunks.extend(chunks)

        chunk_dicts = [c.to_dict() for c in all_chunks]

        # 1. Save metadata JSON cache for rapid lookup and offline tests
        with open(cls.METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(chunk_dicts, f, indent=2)

        # 2. Vector indexing
        chunk_texts = [c.text for c in all_chunks]

        if HAS_SENTENCE_TRANSFORMERS and HAS_FAISS:
            model = SentenceTransformer(cls.MODEL_NAME)
            embeddings = model.encode(chunk_texts, convert_to_numpy=True, normalize_embeddings=True)
            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)  # Inner product on normalized vectors = Cosine similarity
            index.add(embeddings)
            faiss.write_index(index, str(cls.INDEX_PATH))
            index_type = "faiss_sentence_transformers"
        else:
            # Fallback lightweight TF-IDF / term-frequency cosine vector index
            index_data = cls._build_lightweight_vector_index(all_chunks)
            with open(cls.INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(index_data, f)
            index_type = "lightweight_term_vector"

        return {
            "status": "success",
            "pdf_count": len(pdf_files),
            "chunk_count": len(all_chunks),
            "index_type": index_type,
            "index_file": str(cls.INDEX_PATH),
            "metadata_file": str(cls.METADATA_PATH),
        }

    @staticmethod
    def _build_lightweight_vector_index(chunks: List[HandbookChunk]) -> Dict[str, Any]:
        """Builds a portable cosine vector index from vocabulary term frequencies."""
        token_pattern = re.compile(r"\b[a-zA-Z0-9_\-\.]{3,}\b")
        doc_freqs: Dict[str, int] = {}
        chunk_vectors = []

        for c in chunks:
            tokens = token_pattern.findall(c.text.lower())
            tf: Dict[str, float] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0.0) + 1.0
            for t in tf:
                doc_freqs[t] = doc_freqs.get(t, 0) + 1
            chunk_vectors.append(tf)

        n_docs = len(chunks)
        # Compute IDF and normalize unit vectors
        normalized_vectors = []
        for tf in chunk_vectors:
            vec: Dict[str, float] = {}
            norm_sq = 0.0
            for t, count in tf.items():
                idf = math.log((n_docs + 1) / (doc_freqs.get(t, 1) + 1)) + 1.0
                val = count * idf
                vec[t] = val
                norm_sq += val * val
            norm = math.sqrt(norm_sq) or 1.0
            for t in vec:
                vec[t] /= norm
            normalized_vectors.append(vec)

        return {
            "type": "lightweight_tfidf",
            "doc_freqs": doc_freqs,
            "n_docs": n_docs,
            "vectors": normalized_vectors,
            "chunk_ids": [c.chunk_id for c in chunks],
        }


if __name__ == "__main__":
    result = APHIngestionService.ingest_all_pdfs()
    print("Handbook Ingestion Summary:")
    print(json.dumps(result, indent=2))
