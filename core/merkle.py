"""
Unicrium MerkleTree Implementation
Production-ready Merkle tree for transaction verification
Supports SPV (Simplified Payment Verification)
"""
from typing import List, Optional, Tuple
import hashlib
import json

# crypto.py'dan standartlaştırılmış hash fonksiyonumuzu import ediyoruz
from core.crypto import hash_object


class MerkleTree:
    """
    Merkle Tree for transaction verification
    Enables SPV clients and efficient block validation
    """
    
    def __init__(self, data_list: List[str]):
        """
        Initialize Merkle tree from list of data (transaction hashes)
        
        Args:
            data_list: List of transaction hashes
        """
        self.data_list = data_list
        self.tree = []
        self.root = self._build_tree()
    
    def _build_tree(self) -> str:
        """Build the Merkle tree and return root hash"""
        if not self.data_list:
            # crypto.py'dan gelen hash_object'i kullanıyoruz
            return hash_object("EMPTY_TREE")
        
        # Start with leaf nodes (transaction hashes)
        current_level = self.data_list.copy()
        
        # Build tree level by level
        while len(current_level) > 1:
            self.tree.append(current_level.copy())
            
            # If odd number of nodes, duplicate last one
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])
            
            # Compute parent level
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1]
                # crypto.py'dan gelen hash_object'i kullanıyoruz
                parent = hash_object(left + right)
                next_level.append(parent)
            
            current_level = next_level
        
        # Root is the single remaining node
        return current_level[0]
    
    @staticmethod
    def compute_root(tx_hashes: List[str]) -> str:
        """
        Compute Merkle root from transaction hashes
        Static method for quick root calculation
        
        Args:
            tx_hashes: List of transaction hashes
            
        Returns:
            Merkle root hash
        """
        if not tx_hashes:
            # crypto.py'dan gelen hash_object'i kullanıyoruz
            return hash_object("EMPTY_TREE")
        
        if len(tx_hashes) == 1:
            return tx_hashes[0]
        
        # Duplicate last hash if odd number
        if len(tx_hashes) % 2 == 1:
            tx_hashes.append(tx_hashes[-1])
        
        # Compute parent hashes
        new_hashes = []
        for i in range(0, len(tx_hashes), 2):
            combined = tx_hashes[i] + tx_hashes[i + 1]
            # crypto.py'dan gelen hash_object'i kullanıyoruz
            new_hashes.append(hash_object(combined))
        
        # Recursively compute root
        return MerkleTree.compute_root(new_hashes)
    
    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Get Merkle proof for transaction at index
        Used for SPV verification
        
        Args:
            index: Index of transaction in original list
            
        Returns:
            List of (hash, position) tuples for proof path
            position is 'left' or 'right'
        """
        if index < 0 or index >= len(self.data_list):
            raise ValueError(f"Index {index} out of range")
        
        proof = []
        current_index = index
        
        # Traverse tree from leaf to root
        for level in self.tree:
            # Determine sibling index
            if current_index % 2 == 0:
                # Current is left child
                sibling_index = current_index + 1
                position = 'right'
            else:
                # Current is right child
                sibling_index = current_index - 1
                position = 'left'
            
            # Add sibling to proof if it exists
            if sibling_index < len(level):
                proof.append((level[sibling_index], position))
            
            # Move to parent level
            current_index = current_index // 2
        
        return proof
    
    @staticmethod
    def verify_proof(tx_hash: str, proof: List[Tuple[str, str]], root: str) -> bool:
        """
        Verify Merkle proof
        Used by SPV clients to verify transaction inclusion
        
        Args:
            tx_hash: Transaction hash to verify
            proof: Merkle proof path
            root: Expected Merkle root
            
        Returns:
            True if proof is valid
        """
        current_hash = tx_hash
        
        # Traverse proof path
        for sibling_hash, position in proof:
            if position == 'left':
                # Sibling is on left
                current_hash = hash_object(sibling_hash + current_hash)
            else:
                # Sibling is on right
                current_hash = hash_object(current_hash + sibling_hash)
        
        # Check if computed root matches expected root
        return current_hash == root
    
    def to_dict(self) -> dict:
        """Export tree as dictionary"""
        return {
            'root': self.root,
            'leaves': self.data_list,
            'levels': len(self.tree)
        }
    
    @classmethod
    def from_transactions(cls, transactions: list) -> 'MerkleTree':
        """
        Create Merkle tree from transaction objects
        
        Args:
            transactions: List of Transaction objects
            
        Returns:
            MerkleTree instance
        """
        # .txid() zaten crypto.py'daki hash_object'i kullanacak
        tx_hashes = [tx.txid() for tx in transactions]
        return cls(tx_hashes)


# Utility functions for block integration
def compute_tx_root(transactions: list) -> str:
    """
    Compute transaction Merkle root for a block
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        Merkle root hash
    """
    if not transactions:
        # crypto.py'dan gelen hash_object'i kullanıyoruz
        return hash_object("EMPTY_BLOCK")
    
    tx_hashes = [tx.txid() for tx in transactions]
    return MerkleTree.compute_root(tx_hashes)


def verify_tx_inclusion(tx_hash: str, proof: List[Tuple[str, str]], 
                       block_tx_root: str) -> bool:
    """
    Verify transaction is included in block
    SPV clients use this to verify transactions without full blockchain
    
    Args:
        tx_hash: Transaction hash
        proof: Merkle proof
        block_tx_root: Transaction root from block header
        
    Returns:
        True if transaction is in block
    """
    return MerkleTree.verify_proof(tx_hash, proof, block_tx_root)


if __name__ == "__main__":
    # Test MerkleTree
    print("Testing MerkleTree...")
    
    # Create tree from transaction hashes
    tx_hashes = [
        hash_object("tx1"),
        hash_object("tx2"),
        hash_object("tx3"),
        hash_object("tx4")
    ]
    
    tree = MerkleTree(tx_hashes)
    print(f"✓ Root: {tree.root[:16]}...")
    
    # Get proof for tx2
    proof = tree.get_proof(1)
    print(f"✓ Proof for tx2: {len(proof)} nodes")
    
    # Verify proof
    valid = MerkleTree.verify_proof(tx_hashes[1], proof, tree.root)
    print(f"✓ Proof valid: {valid}")
    
    # Test with odd number of transactions
    tx_hashes_odd = [
        hash_object("tx1"),
        hash_object("tx2"),
        hash_object("tx3")
    ]
    
    root_odd = MerkleTree.compute_root(tx_hashes_odd)
    print(f"✓ Odd root: {root_odd[:16]}...")
    
    print("\n✅ MerkleTree tests passed!")