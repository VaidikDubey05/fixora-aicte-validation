"""
Fixora Handbook Assistant RAG Retrieval Benchmark
Evaluates 20 statutory test questions against APH vector index.
Measures Top-1, Top-3, Top-5 retrieval hit rates and Mean Reciprocal Rank (MRR).
"""

from pathlib import Path
import sys
from typing import Any, Dict, List

backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.rag.rag_service import RAGService

# 20 Statutory Evaluation Benchmark Questions with Ground Truth Expected Sections
BENCHMARK_QUESTIONS: List[Dict[str, str]] = [
    {
        "id": "Q-01",
        "question": "What is the minimum land requirement for an engineering college in urban areas?",
        "expected_section": "Section 3.1",
        "topic": "Land Norms (Urban)",
    },
    {
        "id": "Q-02",
        "question": "What are the norms for minimum land required for technical institutions in rural areas?",
        "expected_section": "Section 3.1",
        "topic": "Land Norms (Rural)",
    },
    {
        "id": "Q-03",
        "question": "What built-up carpet area is required if the applied intake exceeds 120 students?",
        "expected_section": "Section 3.2",
        "topic": "Carpet Area (>120)",
    },
    {
        "id": "Q-04",
        "question": "What is the built-up space norm for institutions with applied intake of 120 or fewer students?",
        "expected_section": "Section 3.2",
        "topic": "Carpet Area (<=120)",
    },
    {
        "id": "Q-05",
        "question": "How many laboratories or practical workshops are required per technical intake?",
        "expected_section": "Section 3.3",
        "topic": "Laboratory Norm Ratio",
    },
    {
        "id": "Q-06",
        "question": "What is the minimum baseline number of laboratories an institution must possess?",
        "expected_section": "Section 3.3",
        "topic": "Minimum Baseline Laboratories",
    },
    {
        "id": "Q-07",
        "question": "What is the prescribed student to computer terminal ratio in the computer centre?",
        "expected_section": "Section 3.4",
        "topic": "Computer Centre Terminal Ratio",
    },
    {
        "id": "Q-08",
        "question": "What accessibility norms and barrier-free infrastructure are mandatory for differently-abled persons?",
        "expected_section": "Section 3.5",
        "topic": "Accessibility & Barrier-free Norms",
    },
    {
        "id": "Q-09",
        "question": "What is the faculty to student cadre ratio for undergraduate engineering courses?",
        "expected_section": "Section 4.1",
        "topic": "Faculty Cadre Ratio (1:20)",
    },
    {
        "id": "Q-10",
        "question": "What is the cadre distribution ratio of Professors to Associate Professors and Assistant Professors?",
        "expected_section": "Section 4.1",
        "topic": "Cadre Distribution Ratio",
    },
    {
        "id": "Q-11",
        "question": "What constitutes an unapproved intake increase requiring statutory deficiency rectification?",
        "expected_section": "Section 4.2",
        "topic": "Intake Ceilings & Discrepancies",
    },
    {
        "id": "Q-12",
        "question": "What minimum academic qualifications and experience are mandatory for a Principal or Director?",
        "expected_section": "Section 4.3",
        "topic": "Principal / Director Qualifications",
    },
    {
        "id": "Q-13",
        "question": "What is the non-refundable Technical Education Regulatory TER processing fee structure?",
        "expected_section": "Section 5.1",
        "topic": "TER Processing Fee Schedule",
    },
    {
        "id": "Q-14",
        "question": "How must TER fees be paid and what payment confirmation status is mandatory?",
        "expected_section": "Section 5.2",
        "topic": "TER Fee Remittance & Verification",
    },
    {
        "id": "Q-15",
        "question": "What are the statutory requirements for executing a sworn affidavit on stamp paper?",
        "expected_section": "Section 2.1",
        "topic": "Sworn Affidavit Requirements",
    },
    {
        "id": "Q-16",
        "question": "What are the rules regarding valid fire safety certificate and department NOC?",
        "expected_section": "Section 2.2",
        "topic": "Fire Safety Certificate & NOC",
    },
    {
        "id": "Q-17",
        "question": "Who must issue the structural stability and building occupancy completion certificate?",
        "expected_section": "Section 2.3",
        "topic": "Building Occupancy Certificate",
    },
    {
        "id": "Q-18",
        "question": "What digital requirements and QR codes apply to National Board of Accreditation NBA certificates?",
        "expected_section": "Section 2.4",
        "topic": "Accreditation Certificate & QR",
    },
    {
        "id": "Q-19",
        "question": "How must land ownership be registered in the name of the Trust or Society?",
        "expected_section": "Section 2.5",
        "topic": "Registered Land Title Deed",
    },
    {
        "id": "Q-20",
        "question": "What is the statutory rectification window granted to cure minor certificate deficiencies?",
        "expected_section": "Section 7.1",
        "topic": "Rectification Window to Cure",
    },
]


def run_rag_retrieval_evaluation() -> Dict[str, Any]:
    """
    Evaluates retrieval accuracy across the 20 benchmark questions.
    """
    total = len(BENCHMARK_QUESTIONS)
    top_1_hits = 0
    top_3_hits = 0
    top_5_hits = 0
    reciprocal_ranks = []

    print("\n" + "=" * 90)
    print(" FIXORA APPROVAL PROCESS HANDBOOK (APH) - RAG RETRIEVAL BENCHMARK REPORT")
    print(" Total Benchmark Questions: 20 | Target: Official Statutory Handbook Sections")
    print("=" * 90)
    print(f"{'ID':<6} | {'Topic':<32} | {'Expected':<12} | {'Rank':<6} | {'Status':<10} | {'Score'}")
    print("-" * 90)

    for q in BENCHMARK_QUESTIONS:
        retrieved = RAGService.retrieve_chunks(q["question"], top_k=5)
        expected = q["expected_section"].lower()

        rank = -1
        score_val = 0.0
        for idx, (chunk_data, score) in enumerate(retrieved, start=1):
            sec = chunk_data.get("section", "").lower()
            text = chunk_data.get("text", "").lower()
            if expected in sec or expected in text:
                rank = idx
                score_val = score
                break

        if rank == 1:
            top_1_hits += 1
            top_3_hits += 1
            top_5_hits += 1
            reciprocal_ranks.append(1.0)
            status_str = "HIT (Top-1)"
        elif 1 < rank <= 3:
            top_3_hits += 1
            top_5_hits += 1
            reciprocal_ranks.append(1.0 / rank)
            status_str = f"HIT (Top-{rank})"
        elif 3 < rank <= 5:
            top_5_hits += 1
            reciprocal_ranks.append(1.0 / rank)
            status_str = f"HIT (Top-{rank})"
        else:
            reciprocal_ranks.append(0.0)
            status_str = "MISS"

        rank_str = str(rank) if rank > 0 else "-"
        print(f"{q['id']:<6} | {q['topic']:<32} | {q['expected_section']:<12} | {rank_str:<6} | {status_str:<10} | {score_val:.3f}")

    top_1_rate = (top_1_hits / total) * 100.0
    top_3_rate = (top_3_hits / total) * 100.0
    top_5_rate = (top_5_hits / total) * 100.0
    mrr = sum(reciprocal_ranks) / total

    print("=" * 90)
    print(f"Top-1 Retrieval Hit Rate : {top_1_hits}/{total} ({top_1_rate:.1f}%)")
    print(f"Top-3 Retrieval Hit Rate : {top_3_hits}/{total} ({top_3_rate:.1f}%)")
    print(f"Top-5 Retrieval Hit Rate : {top_5_hits}/{total} ({top_5_rate:.1f}%)")
    print(f"Mean Reciprocal Rank (MRR): {mrr:.3f}")
    print("=" * 90 + "\n")

    return {
        "total_questions": total,
        "top_1_rate": top_1_rate,
        "top_3_rate": top_3_rate,
        "top_5_rate": top_5_rate,
        "mrr": mrr,
    }


if __name__ == "__main__":
    run_rag_retrieval_evaluation()
