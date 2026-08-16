"""
Full VeriRAG pipeline for the healthcare domain.

Healthcare questions:
    User Query
        -> Healthcare scope check
        -> ChromaDB Retrieval
        -> Hash Verification
        -> Merkle Verification
        -> Keep Verified Records
        -> LLM using ONLY verified records

Out-of-scope questions:
    User Query
        -> Healthcare scope check
        -> LLM directly
        -> NO retrieval
        -> NO verification
        -> Trust Score = N/A
        -> Retrieved Records = 0
"""

import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from retrieval.retrieve_healthcare import retrieve
from verification.verify_retrieved_record import (
    verify_record_complete,
    VerificationResult
)
from llm.healthcare_rag_llm import generate_answer

import config


# ============================================================
# RESPONSE OBJECT
# ============================================================

@dataclass
class VeriRAGResponse:
    query: str
    retrieved_count: int
    results: List[VerificationResult]
    verified_records: List[Dict[str, Any]]

    # None means:
    # "Trust score is not applicable because this is outside
    # the verified healthcare-data scope."
    trust_score_percent: Optional[float]

    answer: str

    # True  = healthcare question
    # False = out-of-scope question
    in_scope: bool

    verification_message: str


# ============================================================
# HEALTHCARE SCOPE DETECTION
# ============================================================

HEALTHCARE_KEYWORDS = {
    # General healthcare
    "health",
    "healthcare",
    "medical",
    "medicine",
    "patient",
    "patients",
    "hospital",
    "doctor",
    "doctors",
    "diagnosis",
    "diagnosed",
    "disease",
    "diseases",
    "condition",
    "conditions",
    "treatment",
    "symptom",
    "symptoms",
    "illness",

    # Dataset fields
    "age",
    "gender",
    "blood",
    "blood type",
    "admission",
    "admitted",
    "discharge",
    "discharged",
    "medication",
    "medications",
    "insurance",
    "billing",
    "bill",
    "room",
    "test",
    "tests",
    "test results",
    "results",
    "doctor",
    "hospital",

    # Medical conditions
    "diabetes",
    "cancer",
    "obesity",
    "asthma",
    "arthritis",
    "hypertension",

    # Dataset-related queries
    "patient record",
    "patient records",
    "medical record",
    "medical records",
    "health record",
    "health records",
}


def is_healthcare_question(query: str) -> bool:
    """
    Determine whether a question belongs to the healthcare
    / patient-record domain.

    This is intentionally deterministic.

    It prevents unrelated questions from being sent to
    ChromaDB and blockchain verification.
    """

    q = query.lower().strip()

    if not q:
        return False

    # Direct keyword matching
    for keyword in HEALTHCARE_KEYWORDS:

        if keyword in q:
            return True

    return False


# ============================================================
# DIRECT LLM FOR OUT-OF-SCOPE QUESTIONS
# ============================================================

def generate_out_of_scope_answer(query: str) -> str:
    """
    Ask the local Ollama LLM to answer an unrelated question.

    IMPORTANT:
    No healthcare records are provided as context.

    Therefore the answer is NOT blockchain/Merkle verified.
    """

    from langchain_ollama import OllamaLLM

    llm = OllamaLLM(
        model=config.OLLAMA_MODEL_NAME
    )

    prompt = f"""
You are a general-purpose AI assistant.

The user's question is outside the verified healthcare
patient-record scope of VeriRAG.

Answer the user's question helpfully and clearly.

IMPORTANT:
- Do not claim that the answer came from the healthcare dataset.
- Do not claim that the answer was blockchain verified.
- Do not mention retrieved healthcare records.
- Do not fabricate healthcare records.

Question:
{query}

Answer:
"""

    return llm.invoke(prompt)


# ============================================================
# EVIDENCE REPORT
# ============================================================

def evidence_report(response: VeriRAGResponse) -> str:

    lines = [
        f"Query: {response.query}",
        ""
    ]

    # --------------------------------------------------------
    # OUT-OF-SCOPE
    # --------------------------------------------------------

    if not response.in_scope:

        lines.append("Scope: OUTSIDE HEALTHCARE DATA SCOPE")
        lines.append("Retrieved Records: 0")
        lines.append(
            "Verification: Not performed "
            "(outside the scope to perform verification)"
        )
        lines.append("Trust Score: N/A")
        lines.append("")
        lines.append("Final Answer:")
        lines.append(response.answer)

        return "\n".join(lines)

    # --------------------------------------------------------
    # HEALTHCARE
    # --------------------------------------------------------

    lines.append(
        f"Retrieved Records: {response.retrieved_count}"
    )

    lines.append("")

    for i, res in enumerate(response.results, start=1):

        lines.append(f"Record {i}:")

        for line in res.to_evidence_lines()[1:]:
            lines.append(f"  {line.strip()}")

        lines.append("")

    lines.append(
        f"Trust Score: {response.trust_score_percent:.0f}%"
    )

    lines.append("")

    lines.append("Final Answer:")
    lines.append(response.answer)

    return "\n".join(lines)


# ============================================================
# MAIN VERIRAG PIPELINE
# ============================================================

def run_query(
    query: str,
    top_k: int = None
) -> VeriRAGResponse:

    top_k = top_k or config.DEFAULT_TOP_K

    query = query.strip()

    # ========================================================
    # STEP 1: CHECK SCOPE
    # ========================================================

    in_scope = is_healthcare_question(query)

    # ========================================================
    # OUT-OF-SCOPE PATH
    # ========================================================

    if not in_scope:

        print(
            "[VeriRAG] Question is outside healthcare scope."
        )

        print(
            "[VeriRAG] Skipping ChromaDB retrieval."
        )

        print(
            "[VeriRAG] Skipping blockchain/Merkle verification."
        )

        # Let LLM answer normally
        answer = generate_out_of_scope_answer(query)

        return VeriRAGResponse(
            query=query,

            retrieved_count=0,

            results=[],

            verified_records=[],

            trust_score_percent=None,

            answer=answer,

            in_scope=False,

            verification_message=(
                "Not performed "
                "(outside the scope to perform verification)"
            ),
        )

    # ========================================================
    # HEALTHCARE PATH
    # ========================================================

    print(
        "[VeriRAG] Healthcare question detected."
    )

    # --------------------------------------------------------
    # STEP 2: RETRIEVE
    # --------------------------------------------------------

    retrieved = retrieve(
        query,
        top_k=top_k
    )

    print(
        f"[VeriRAG] Retrieved {len(retrieved)} records."
    )

    # --------------------------------------------------------
    # STEP 3: VERIFY
    # --------------------------------------------------------

    results: List[VerificationResult] = []

    verified_records: List[Dict[str, Any]] = []

    for record in retrieved:

        result = verify_record_complete(record)

        results.append(result)

        if result.verified:

            verified_records.append(record)

    # --------------------------------------------------------
    # STEP 4: TRUST SCORE
    # --------------------------------------------------------

    if retrieved:

        trust_score = (
            len(verified_records)
            / len(retrieved)
            * 100.0
        )

    else:

        trust_score = 0.0

    # --------------------------------------------------------
    # STEP 5: LLM ONLY GETS VERIFIED RECORDS
    # --------------------------------------------------------

    if verified_records:

        answer = generate_answer(
            query,
            verified_records
        )

    else:

        answer = (
            "No retrieved records passed verification, so "
            "no answer can be generated from trusted data. "
            "This may indicate tampering, or that the Merkle "
            "tree / on-chain root is out of date."
        )

    # --------------------------------------------------------
    # STEP 6: RETURN
    # --------------------------------------------------------

    return VeriRAGResponse(
        query=query,

        retrieved_count=len(retrieved),

        results=results,

        verified_records=verified_records,

        trust_score_percent=trust_score,

        answer=answer,

        in_scope=True,

        verification_message="Verification performed",
    )


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    q = (
        " ".join(sys.argv[1:])
        or "Which patients were diagnosed with diabetes?"
    )

    response = run_query(q)

    print(
        evidence_report(response)
    )