// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title HashRegistry
/// @notice Stores keccak256 hashes of individual VeriRAG records, keyed by
///         record_id, so a retrieved record's integrity can be checked
///         directly against an on-chain value. See MerkleRegistry for the
///         scalable, whole-dataset alternative (one root covers every
///         record without one on-chain entry per row).
contract HashRegistry {
    address public owner;

    mapping(string => bytes32) private recordHashes;
    mapping(string => bool) private recordExists;

    event RecordHashStored(string recordId, bytes32 recordHash);

    modifier onlyOwner() {
        require(msg.sender == owner, "HashRegistry: caller is not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Store the hash for a single record.
    function storeHash(string memory recordId, bytes32 recordHash) public onlyOwner {
        recordHashes[recordId] = recordHash;
        recordExists[recordId] = true;
        emit RecordHashStored(recordId, recordHash);
    }

    /// @notice Store hashes for many records in one transaction, to reduce
    ///         the number of transactions needed for bulk registration.
    function storeHashesBatch(string[] memory recordIds, bytes32[] memory hashes)
        public
        onlyOwner
    {
        require(recordIds.length == hashes.length, "HashRegistry: length mismatch");
        for (uint256 i = 0; i < recordIds.length; i++) {
            recordHashes[recordIds[i]] = hashes[i];
            recordExists[recordIds[i]] = true;
            emit RecordHashStored(recordIds[i], hashes[i]);
        }
    }

    /// @notice Returns the stored hash for a record (bytes32(0) if unset).
    function getHash(string memory recordId) public view returns (bytes32) {
        return recordHashes[recordId];
    }

    /// @notice Returns true if `recordId` has ever been registered.
    function isRegistered(string memory recordId) public view returns (bool) {
        return recordExists[recordId];
    }

    /// @notice Convenience view: true iff `recordHash` matches the stored
    ///         hash for `recordId`.
    function verifyHash(string memory recordId, bytes32 recordHash)
        public
        view
        returns (bool)
    {
        return recordExists[recordId] && recordHashes[recordId] == recordHash;
    }
}
