"""
Canonical record identity, text representation, and hashing for the
VeriRAG healthcare dataset.

This module is imported by every other layer (vector DB build,
retrieval, on-chain hash registration, Merkle tree construction, and
verification). Centralizing `build_record_id` / `build_record_text` /
`hash_record_hex` here guarantees the SAME string is hashed
everywhere -- if two modules computed the record's text
representation slightly differently, every verification would fail
even on untampered data. Do not reimplement these functions elsewhere.

IMPORTANT dataset note: this CSV has no unique patient-ID column, and
inspection found ~5,500 exact duplicate rows out of 55,500 (a known
property of this dataset). Using only content fields (e.g. Name +
Date of Admission) as the record_id would collide on those duplicates
-- two DIFFERENT real records would end up sharing one Merkle leaf,
which would silently break tamper detection for one of them. To
guarantee every record gets its own leaf/hash/proof, record_id
includes the record's row position in the CSV (zero-padded), with the
patient name and admission date kept in the ID for human readability.
"""
from __future__ import annotations
import csv
import re
from typing import Dict, List
from web3 import Web3

REQUIRED_COLUMNS = [
    "Name",
    "Age",
    "Gender",
    "Blood Type",
    "Medical Condition",
    "Date of Admission",
    "Doctor",
    "Hospital",
    "Insurance Provider",
    "Billing Amount",
    "Room Number",
    "Admission Type",
    "Discharge Date",
    "Medication",
    "Test Results",
]


def _slug(value: str, max_len: int = 20) -> str:
    """Alphanumeric-only, length-capped slug for building readable IDs."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", value or "")
    return cleaned[:max_len] if cleaned else "NA"


def build_record_id(row: Dict[str, str], row_index: int) -> str:
    """
    e.g. 'BobbyJacksOn_31012024_000000'
    row_index (the record's position in the CSV, after sorting is
    applied consistently everywhere) guarantees uniqueness even
    across this dataset's known exact-duplicate rows.
    """
    name_slug = _slug(row["Name"])
    date_slug = re.sub(r"[^0-9]", "", row["Date of Admission"] or "")
    return f"{name_slug}_{date_slug}_{row_index:06d}"


def build_record_text(row: Dict[str, str]) -> str:
    """
    Deterministic, human-readable canonical text for a patient record.
    This exact string is what gets hashed, stored as the Chroma
    document, and shown to the LLM as verified context.
    """
    return (
        f"Patient: {row['Name']} | "
        f"Age: {row['Age']} | "
        f"Gender: {row['Gender']} | "
        f"Blood Type: {row['Blood Type']} | "
        f"Medical Condition: {row['Medical Condition']} | "
        f"Date of Admission: {row['Date of Admission']} | "
        f"Doctor: {row['Doctor']} | "
        f"Hospital: {row['Hospital']} | "
        f"Insurance Provider: {row['Insurance Provider']} | "
        f"Billing Amount: {row['Billing Amount']} | "
        f"Room Number: {row['Room Number']} | "
        f"Admission Type: {row['Admission Type']} | "
        f"Discharge Date: {row['Discharge Date']} | "
        f"Medication: {row['Medication']} | "
        f"Test Results: {row['Test Results']}"
    )


def hash_record_hex(record_text: str) -> str:
    """Returns keccak256(record_text) as a 0x-prefixed hex string."""
    digest: bytes = Web3.keccak(text=record_text)
    return "0x" + digest.hex()


def hex_to_bytes32(hex_str: str) -> bytes:
    """Strict hex-string -> 32 raw bytes (uses removeprefix, not lstrip,
    to avoid accidentally stripping valid leading-zero hex digits)."""
    clean = hex_str.removeprefix("0x").removeprefix("0X")
    b = bytes.fromhex(clean)
    if len(b) != 32:
        raise ValueError(f"Expected 32-byte hash, got {len(b)} bytes: {hex_str}")
    return b


def load_raw_rows(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"healthcare_dataset.csv is missing required column(s): {missing}. "
                f"Found columns: {reader.fieldnames}"
            )
        return list(reader)


def load_records_with_ids(csv_path: str) -> List[Dict[str, str]]:
    """
    Returns a list of dicts, one per CSV row (in original file order,
    which is what row_index is based on), each augmented with:
      record_id, record_text, hash_hex
    plus the original healthcare columns.
    """
    rows = load_raw_rows(csv_path)
    out = []
    for i, row in enumerate(rows):
        record_id = build_record_id(row, i)
        record_text = build_record_text(row)
        hash_hex = hash_record_hex(record_text)
        enriched = dict(row)
        enriched["record_id"] = record_id
        enriched["record_text"] = record_text
        enriched["hash_hex"] = hash_hex
        out.append(enriched)
    return out


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "dataset/healthcare/healthcare_dataset.csv"
    records = load_records_with_ids(path)
    print(f"Loaded {len(records)} records.")
    print("Example record:")
    print(f"  record_id  : {records[0]['record_id']}")
    print(f"  record_text: {records[0]['record_text']}")
    print(f"  hash_hex   : {records[0]['hash_hex']}")
