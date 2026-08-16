"""
Verification for retrieved records. Two independent checks are combined:

1. Hash-recomputation check (always available, purely local): recompute
   keccak256(record_text) and confirm it equals the record's stored
   hash_hex from the vector DB metadata. Catches tampering of the
   retrieved text itself (e.g. a corrupted or maliciously edited Chroma
   entry) before it ever reaches the LLM.

2. Merkle inclusion-proof check (scales to the full 55,500-row dataset
   with a single on-chain value): generate a proof for the record's
   leaf hash and confirm it reconstructs the Merkle root currently
   published on-chain (MerkleRegistry.getMerkleRoot()).

A third, OPTIONAL signal is included when available: direct comparison
against HashRegistry.getHash(record_id), for the subset of records
individually registered on-chain. Not required for `verified=True` --
for the full dataset the Merkle check is the scalable source of truth
-- but reported separately as extra evidence when present.

Fails CLOSED: any missing artifact, undeployed contract, or
disconnected chain results in verified=False, never a crash and never
a silent pass.
"""
import sys, os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashing.healthcare_hashing import hash_record_hex
from merkle.generate_merkle_proof import generate_proof
from merkle.verify_merkle_proof import verify_merkle_proof
from blockchain.web3_utils import get_web3, load_contract
import config


@dataclass
class VerificationResult:
    record_id: str
    hash_recompute_ok: bool
    merkle_ok: bool
    hash_registry_status: Optional[bool]  # True/False/None (None = not registered)
    on_chain_root_hex: str
    local_root_hex: str
    proof_length: int
    verified: bool  # authoritative pass/fail

    def to_evidence_lines(self) -> List[str]:
        lines = [f"Record: {self.record_id}"]
        lines.append(f"  Hash Verified: {'✓' if self.hash_recompute_ok else '✗'}")
        lines.append(f"  Merkle Verified: {'✓' if self.merkle_ok else '✗'} "
                      f"(proof length {self.proof_length})")
        if self.hash_registry_status is None:
            lines.append("  HashRegistry (extra): not individually registered (skipped)")
        else:
            lines.append(f"  HashRegistry (extra): "
                          f"{'Match ✓' if self.hash_registry_status else 'Mismatch ✗'}")
        lines.append(f"  FINAL: {'VERIFIED ✓' if self.verified else 'NOT VERIFIED ✗'}")
        return lines


def _get_on_chain_merkle_root() -> str:
    w3 = get_web3()
    contract = load_contract(w3, config.MERKLE_REGISTRY_ADDRESS_PATH)
    root_bytes = contract.functions.getMerkleRoot().call()
    return "0x" + bytes(root_bytes).hex()


def _check_hash_registry(record_id: str, record_hash_hex: str) -> Optional[bool]:
    try:
        from hashing.healthcare_hashing import hex_to_bytes32
        w3 = get_web3()
        contract = load_contract(w3, config.HASH_REGISTRY_ADDRESS_PATH)
        registered = contract.functions.isRegistered(record_id).call()
        if not registered:
            return None
        return contract.functions.verifyHash(
            record_id, hex_to_bytes32(record_hash_hex)
        ).call()
    except Exception:
        return None


def verify_record_complete(retrieved_record: Dict[str, Any]) -> VerificationResult:
    record_id = retrieved_record["record_id"]
    record_text = retrieved_record["record_text"]
    stored_hash_hex = retrieved_record.get("metadata", {}).get("hash_hex", "")

    recomputed_hash_hex = hash_record_hex(record_text)
    hash_recompute_ok = bool(stored_hash_hex) and (
        recomputed_hash_hex.lower() == stored_hash_hex.lower()
    )

    merkle_ok = False
    on_chain_root_hex = ""
    local_root_hex = ""
    proof_length = 0
    hash_registry_status = None

    try:
        proof = generate_proof(record_id)
        proof_length = len(proof)

        with open(config.MERKLE_ROOT_PATH) as f:
            local_root_hex = f.read().strip()

        on_chain_root_hex = _get_on_chain_merkle_root()
        leaf_matches_root = verify_merkle_proof(recomputed_hash_hex, proof, on_chain_root_hex)
        root_matches = bool(on_chain_root_hex) and (
            on_chain_root_hex.lower() == local_root_hex.lower()
        )
        merkle_ok = leaf_matches_root and root_matches

        hash_registry_status = _check_hash_registry(record_id, recomputed_hash_hex)
    except (KeyError, FileNotFoundError, ConnectionError):
        # Missing merkle artifacts / undeployed contracts / Ganache not
        # running -- fail closed rather than crash the whole pipeline.
        pass

    verified = hash_recompute_ok and merkle_ok

    return VerificationResult(
        record_id=record_id,
        hash_recompute_ok=hash_recompute_ok,
        merkle_ok=merkle_ok,
        hash_registry_status=hash_registry_status,
        on_chain_root_hex=on_chain_root_hex,
        local_root_hex=local_root_hex,
        proof_length=proof_length,
        verified=verified,
    )


if __name__ == "__main__":
    from retrieval.retrieve_healthcare import retrieve

    query = " ".join(sys.argv[1:]) or "patients diagnosed with diabetes"
    records = retrieve(query, top_k=5)
    for r in records:
        result = verify_record_complete(r)
        print("\n".join(result.to_evidence_lines()))
        print()
