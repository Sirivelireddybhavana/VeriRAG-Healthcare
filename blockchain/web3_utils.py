"""
Shared Web3 connection / contract-loading helpers for VeriRAG.

Centralizing this avoids each script re-implementing connection,
account loading, and web3.py v6-vs-v7 raw-transaction attribute
naming differences (`rawTransaction` -> `raw_transaction`).
"""
import json
from web3 import Web3
from eth_account import Account
import config


def get_web3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(config.GANACHE_RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(
            f"Could not connect to Ganache at {config.GANACHE_RPC_URL}. "
            f"Make sure Ganache is running."
        )
    return w3


def get_account(w3: Web3):
    if not config.PRIVATE_KEY:
        raise EnvironmentError(
            "PRIVATE_KEY is not set. Copy .env.example to .env and set "
            "PRIVATE_KEY to one of the private keys shown in the Ganache UI/CLI."
        )
    return Account.from_key(config.PRIVATE_KEY)


def send_raw(w3: Web3, signed_tx):
    """web3.py v7 renamed `.rawTransaction` to `.raw_transaction`."""
    raw = getattr(signed_tx, "raw_transaction", None)
    if raw is None:
        raw = signed_tx.rawTransaction
    return w3.eth.send_raw_transaction(raw)


def save_contract_artifact(path: str, address: str, abi: list) -> None:
    with open(path, "w") as f:
        json.dump({"address": address, "abi": abi}, f, indent=2)


def load_contract(w3: Web3, artifact_path: str):
    if not __import__("os").path.exists(artifact_path):
        raise FileNotFoundError(
            f"Contract artifact not found at {artifact_path}. "
            f"Did you run the matching deploy script first?"
        )
    with open(artifact_path) as f:
        artifact = json.load(f)
    return w3.eth.contract(address=artifact["address"], abi=artifact["abi"])
