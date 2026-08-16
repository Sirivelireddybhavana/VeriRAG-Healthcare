"""
Compiles and deploys HashRegistry.sol to the local Ganache chain, then
batch-registers a configurable SAMPLE of record hashes (storing all
55,500 individual hashes on-chain is impractical for a local demo
chain -- see README "Why not store every hash on-chain?"). Full-dataset
verification is handled by the Merkle layer (merkle/store_merkle_root.py),
which needs only ONE on-chain value regardless of dataset size.
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solcx import compile_source, install_solc, set_solc_version

from blockchain.web3_utils import get_web3, get_account, save_contract_artifact, send_raw
from hashing.healthcare_hashing import load_records_with_ids, hex_to_bytes32
import config


def compile_contract():
    install_solc(config.SOLC_VERSION)
    set_solc_version(config.SOLC_VERSION)
    sol_path = os.path.join(os.path.dirname(__file__), "HashRegistry.sol")
    with open(sol_path) as f:
        source = f.read()
    compiled = compile_source(source, output_values=["abi", "bin"],
                               solc_version=config.SOLC_VERSION)
    _contract_id, interface = next(iter(compiled.items()))
    return interface["abi"], interface["bin"]


def deploy(abi, bytecode):
    w3 = get_web3()
    account = get_account(w3)
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = Contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 3_000_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=account.key)
    tx_hash = send_raw(w3, signed)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[deploy_contract] HashRegistry deployed at {receipt.contractAddress}")
    save_contract_artifact(config.HASH_REGISTRY_ADDRESS_PATH, receipt.contractAddress, abi)
    return w3, account, w3.eth.contract(address=receipt.contractAddress, abi=abi)


def register_sample(w3, account, contract, sample_size: int, batch_size: int = 200):
    records = load_records_with_ids(config.DATASET_CSV_PATH)
    records.sort(key=lambda r: r["record_id"])
    sample = records if not sample_size else records[:sample_size]

    for start in range(0, len(sample), batch_size):
        batch = sample[start:start + batch_size]
        ids = [r["record_id"] for r in batch]
        hashes = [hex_to_bytes32(r["hash_hex"]) for r in batch]
        tx = contract.functions.storeHashesBatch(ids, hashes).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 6_000_000,
            "gasPrice": w3.eth.gas_price,
        })
        signed = w3.eth.account.sign_transaction(tx, private_key=account.key)
        tx_hash = send_raw(w3, signed)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"[deploy_contract] Registered {len(batch)} hashes "
              f"({start + len(batch)}/{len(sample)}). Block {receipt.blockNumber}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=config.HASH_REGISTRY_SAMPLE_SIZE,
                         help="Number of individual record hashes to register on "
                              "HashRegistry (0 = all records; NOT recommended for the "
                              "full 55,500-row dataset -- see README).")
    args = parser.parse_args()

    _abi, _bytecode = compile_contract()
    _w3, _account, _contract = deploy(_abi, _bytecode)
    register_sample(_w3, _account, _contract, args.sample_size)
