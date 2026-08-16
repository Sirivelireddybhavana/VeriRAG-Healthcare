// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title MerkleRegistry
/// @notice Stores a single Merkle root representing an entire dataset
///         snapshot. Scales to arbitrarily large datasets (e.g. the
///         55,500-row healthcare dataset) because only one 32-byte
///         value is written on-chain per dataset version, regardless of
///         row count. Off-chain, a Merkle inclusion proof ties any single
///         record back to this root (see merkle/verify_merkle_proof.py).
contract MerkleRegistry {
    address public owner;

    bytes32 public merkleRoot;
    uint256 public recordCount;
    uint256 public version;

    event MerkleRootUpdated(bytes32 newRoot, uint256 recordCount, uint256 version);

    modifier onlyOwner() {
        require(msg.sender == owner, "MerkleRegistry: caller is not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Publish a new Merkle root for the current dataset snapshot.
    function setMerkleRoot(bytes32 newRoot, uint256 _recordCount) public onlyOwner {
        merkleRoot = newRoot;
        recordCount = _recordCount;
        version += 1;
        emit MerkleRootUpdated(newRoot, _recordCount, version);
    }

    /// @notice Returns the currently published Merkle root.
    function getMerkleRoot() public view returns (bytes32) {
        return merkleRoot;
    }
}
