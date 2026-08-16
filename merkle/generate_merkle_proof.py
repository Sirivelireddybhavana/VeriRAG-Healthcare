"""
Generate a Merkle inclusion proof for a single record_id.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from merkle.merkle_tree import MerkleTree
import config


def generate_proof(record_id: str):
    if not os.path.exists(config.MERKLE_INDEX_PATH):
        raise FileNotFoundError(
            "merkle_index.json not found -- run merkle/build_merkle_tree.py first."
        )
    with open(config.MERKLE_INDEX_PATH) as f:
        index_map = json.load(f)
    if record_id not in index_map:
        raise KeyError(
            f"record_id '{record_id}' not found in Merkle index. "
            f"Did you run merkle/build_merkle_tree.py after the dataset last changed?"
        )
    tree = MerkleTree.load(config.MERKLE_TREE_PATH)
    idx = index_map[record_id]
    raw_proof = tree.proof(idx)
    return [(pos, "0x" + bytes(sib).hex()) for pos, sib in raw_proof]


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else None
    if not rid:
        print("Usage: python merkle/generate_merkle_proof.py <record_id>")
        raise SystemExit(1)
    proof = generate_proof(rid)
    print(json.dumps(proof, indent=2))
