"""
Verify a Merkle inclusion proof for a leaf hash against a root.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from merkle.merkle_tree import MerkleTree
from hashing.healthcare_hashing import hex_to_bytes32
import config


def verify_merkle_proof(leaf_hash_hex: str, proof: list, root_hex: str) -> bool:
    if not leaf_hash_hex or not root_hex:
        return False
    leaf = hex_to_bytes32(leaf_hash_hex)
    root = hex_to_bytes32(root_hex)
    proof_bytes = [(pos, hex_to_bytes32(sib)) for pos, sib in proof]
    return MerkleTree.verify_proof(leaf, proof_bytes, root)


if __name__ == "__main__":
    from merkle.generate_merkle_proof import generate_proof
    from hashing.healthcare_hashing import load_records_with_ids

    rid = sys.argv[1] if len(sys.argv) > 1 else None
    if not rid:
        print("Usage: python merkle/verify_merkle_proof.py <record_id>")
        raise SystemExit(1)

    records = {r["record_id"]: r for r in load_records_with_ids(config.DATASET_CSV_PATH)}
    if rid not in records:
        print(f"record_id '{rid}' not found in dataset.")
        raise SystemExit(1)

    leaf_hex = records[rid]["hash_hex"]
    proof = generate_proof(rid)
    with open(config.MERKLE_ROOT_PATH) as f:
        root_hex = f.read().strip()

    ok = verify_merkle_proof(leaf_hex, proof, root_hex)
    print("MERKLE PROOF VERIFIED" if ok else "MERKLE PROOF FAILED")
    print("LOCAL ROOT MATCHES STORED ROOT" if ok else "ROOT MISMATCH")
