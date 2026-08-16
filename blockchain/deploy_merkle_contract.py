"""
Compiles and deploys MerkleRegistry.sol to the local Ganache chain.
Run merkle/store_merkle_root.py afterwards to publish the actual root.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solcx import compile_source, install_solc, set_solc_version
from blockchain.web3_utils import get_web3, get_account, save_contract_artifact, send_raw
import config


def compile_contract():
    install_solc(config.SOLC_VERSION)
    set_solc_version(config.SOLC_VERSION)
    sol_path = os.path.join(os.path.dirname(__file__), "MerkleRegistry.sol")
    with open(sol_path) as f:
        source = f.read()
    compiled = compile_source(source, output_values=["abi", "bin"],
                               solc_version=config.SOLC_VERSION)
    _contract_id, interface = next(iter(compiled.items()))
    return interface["abi"], interface["bin"]


def deploy():
    abi, bytecode = compile_contract()
    w3 = get_web3()
    account = get_account(w3)
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = Contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 2_000_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=account.key)
    tx_hash = send_raw(w3, signed)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[deploy_merkle_contract] MerkleRegistry deployed at {receipt.contractAddress}")
    save_contract_artifact(config.MERKLE_REGISTRY_ADDRESS_PATH, receipt.contractAddress, abi)
    return receipt.contractAddress


if __name__ == "__main__":
    deploy()
