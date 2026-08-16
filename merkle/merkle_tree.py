"""
Custom, dependency-free Merkle Tree implementation for VeriRAG.

Design note (why not the `pymerkle` library):
pymerkle's public API has changed substantially across major versions,
which makes long-term reproducibility of a stored on-chain Merkle
root risky for a research artifact. This module re-implements the
same core idea using nothing but `web3.py`'s `Web3.keccak`, so the
leaf/parent hashing is:
  1. identical to the hash already used for HashRegistry,
  2. compatible with the "sorted-pair" hashing convention used by
     OpenZeppelin's MerkleProof.sol, in case on-chain proof
     verification is added later,
  3. free of duplicate-leaf padding (an odd node is promoted, not
     duplicated), avoiding a known Merkle-tree construction pitfall.
"""
from __future__ import annotations
import pickle
from dataclasses import dataclass, field
from typing import List, Tuple
from web3 import Web3


def _hash_pair(a: bytes, b: bytes) -> bytes:
    """Order-independent parent hash: keccak256(min(a,b) || max(a,b))."""
    first, second = (a, b) if a <= b else (b, a)
    return Web3.keccak(first + second)


@dataclass
class MerkleTree:
    leaves: List[bytes]
    levels: List[List[bytes]] = field(default_factory=list, init=False)

    def __post_init__(self):
        if not self.leaves:
            raise ValueError("Cannot build a Merkle tree with zero leaves.")
        self.levels = self._build_levels(list(self.leaves))

    @staticmethod
    def _build_levels(leaves: List[bytes]) -> List[List[bytes]]:
        levels = [leaves]
        current = leaves
        while len(current) > 1:
            next_level = []
            i = 0
            while i < len(current):
                if i + 1 < len(current):
                    next_level.append(_hash_pair(current[i], current[i + 1]))
                    i += 2
                else:
                    # Odd node out: promote unchanged (no duplication).
                    next_level.append(current[i])
                    i += 1
            levels.append(next_level)
            current = next_level
        return levels

    @property
    def root(self) -> bytes:
        return self.levels[-1][0]

    @property
    def root_hex(self) -> str:
        return "0x" + bytes(self.root).hex()

    def proof(self, index: int) -> List[Tuple[str, bytes]]:
        """
        Returns list of (position, sibling_hash) tuples. Because
        hashing is order-independent, position is informational only
        (used for human-readable evidence output), not required for
        verification.
        """
        path = []
        idx = index
        for level in self.levels[:-1]:
            if idx % 2 == 0:
                sibling_idx = idx + 1
                position = "right"
            else:
                sibling_idx = idx - 1
                position = "left"
            if sibling_idx < len(level):
                path.append((position, level[sibling_idx]))
            idx //= 2
        return path

    @staticmethod
    def verify_proof(leaf: bytes, proof: List[Tuple[str, bytes]], root: bytes) -> bool:
        computed = leaf
        for _position, sibling in proof:
            computed = _hash_pair(computed, sibling)
        return computed == root

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self.levels, f)

    @classmethod
    def load(cls, path: str) -> "MerkleTree":
        with open(path, "rb") as f:
            levels = pickle.load(f)
        obj = cls.__new__(cls)
        obj.leaves = levels[0]
        obj.levels = levels
        return obj
