"""
Publishes the locally-built Merkle root (merkle/merkle_root.txt) to the
deployed MerkleRegistry contract on the local Ganache chain.

Run order: build_merkle_tree.py -> deploy_merkle_contract.py -> this script.
Re-run this (no redeploy needed) any time build_merkle_tree.py produces
a new root, e.g. after the dataset changes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.web3_utils import get_web3, get_account, load_contract, send_raw
from hashing.healthcare_hashing import hex_to_bytes32
import config


def store_merkle_root():
    if not os.path.exists(config.MERKLE_ROOT_PATH):
        raise FileNotFoundError(
            "merkle_root.txt not found -- run merkle/build_merkle_tree.py first."
        )
    with open(config.MERKLE_ROOT_PATH) as f:
        root_hex = f.read().strip()

    with open(config.DATASET_CSV_PATH) as f:
        record_count = sum(1 for _ in f) - 1  # minus header row

    w3 = get_web3()
    account = get_account(w3)
    contract = load_contract(w3, config.MERKLE_REGISTRY_ADDRESS_PATH)

    tx = contract.functions.setMerkleRoot(
        hex_to_bytes32(root_hex), record_count
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=account.key)
    tx_hash = send_raw(w3, signed)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[store_merkle_root] Root {root_hex} stored for {record_count} records.")
    print(f"[store_merkle_root] Tx: {tx_hash.hex()}  Block: {receipt.blockNumber}")


if __name__ == "__main__":
    store_merkle_root()
