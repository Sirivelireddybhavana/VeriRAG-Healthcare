"""
LLM wrapper for the healthcare domain: builds a context-grounded prompt
from ONLY verified records and calls a local Ollama model.
"""
import sys, os
from typing import List, Dict, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_ollama import OllamaLLM
import config

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = OllamaLLM(model=config.OLLAMA_MODEL_NAME)
    return _llm


PROMPT_TEMPLATE = """You are a clinical-records assistant. Answer the question
using ONLY the verified patient records below. Every record shown here has
passed cryptographic hash and Merkle-proof verification against a
blockchain-anchored record of the original dataset -- you may treat them as
authentic. Do not use any other knowledge, and do not offer medical advice or
diagnosis beyond what is explicitly stated in the records. If the verified
records do not contain enough information to answer, say so explicitly.

Verified Records:
{context}

Question: {question}

Answer:"""


def build_context(verified_records: List[Dict[str, Any]]) -> str:
    lines = []
    for i, r in enumerate(verified_records, start=1):
        lines.append(f"{i}. [{r['record_id']}] {r['record_text']}")
    return "\n".join(lines) if lines else "(no verified records available)"


def generate_answer(question: str, verified_records: List[Dict[str, Any]]) -> str:
    context = build_context(verified_records)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    llm = _get_llm()
    return llm.invoke(prompt)


if __name__ == "__main__":
    demo_records = [{
        "record_id": "BobbyJacksOn_31012024_000000",
        "record_text": "Patient: Bobby JacksOn | Age: 30 | Gender: Male | "
                        "Blood Type: B- | Medical Condition: Cancer | "
                        "Date of Admission: 31-01-2024 | Doctor: Matthew Smith | "
                        "Hospital: Sons and Miller | Insurance Provider: Blue Cross | "
                        "Billing Amount: 18856.28 | Room Number: 328 | "
                        "Admission Type: Urgent | Discharge Date: 02-02-2024 | "
                        "Medication: Paracetamol | Test Results: Normal",
    }]
    print(generate_answer("What medication was Bobby JacksOn prescribed?", demo_records))
