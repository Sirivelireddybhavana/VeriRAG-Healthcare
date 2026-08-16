"""
Merkle tree construction for the healthcare dataset.

Builds one leaf per patient record (using the same canonical
record_text / keccak256 hash as HashRegistry -- see
hashing/healthcare_hashing.py), constructs the tree, and writes:
  - merkle/merkle_tree.pkl   (all tree levels, used to regenerate proofs)
  - merkle/merkle_index.json (record_id -> leaf index)
  - merkle/merkle_root.txt   (hex root, to be pushed on-chain)

Leaf ordering is fixed by sorting on record_id, so the tree (and
therefore the root) is fully reproducible across runs given the same
CSV. record_id already includes the row's position in the file (see
hashing/healthcare_hashing.py) so this remains stable and unique even
though this dataset contains ~5,500 exact duplicate rows.

Run this whenever the dataset CSV changes, THEN re-run
merkle/store_merkle_root.py to publish the new root on-chain.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashing.healthcare_hashing import load_records_with_ids, hex_to_bytes32
from merkle.merkle_tree import MerkleTree
import config


def build_and_save() -> str:
    records = load_records_with_ids(config.DATASET_CSV_PATH)
    records.sort(key=lambda r: r["record_id"])

    leaves = [hex_to_bytes32(r["hash_hex"]) for r in records]
    index_map = {r["record_id"]: i for i, r in enumerate(records)}

    tree = MerkleTree(leaves)
    tree.save(config.MERKLE_TREE_PATH)

    with open(config.MERKLE_INDEX_PATH, "w") as f:
        json.dump(index_map, f)

    with open(config.MERKLE_ROOT_PATH, "w") as f:
        f.write(tree.root_hex)

    print(f"[build_merkle_tree] {len(leaves)} leaves")
    print(f"[build_merkle_tree] Merkle root: {tree.root_hex}")
    print(f"[build_merkle_tree] Wrote {config.MERKLE_TREE_PATH}")
    print(f"[build_merkle_tree] Wrote {config.MERKLE_INDEX_PATH}")
    print(f"[build_merkle_tree] Wrote {config.MERKLE_ROOT_PATH}")
    return tree.root_hex


if __name__ == "__main__":
    build_and_save()
