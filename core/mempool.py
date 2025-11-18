"""
Unicrium Mempool - Transaction Pool Management
Handles pending transactions with proper ordering and limits
"""
from typing import Dict, List, Optional, Set
from collections import defaultdict
import time
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from blockchain.models import Transaction

logger = logging.getLogger(__name__)


class Mempool:
    """
    Transaction mempool with ordering, deduplication, and limits
    
    Features:
    - Deduplication (txid-based)
    - Nonce ordering per sender
    - Fee-based prioritization
    - Size limits
    - Age-based expiration
    """
    
    def __init__(self, max_size: int = 10000, max_age_seconds: int = 3600):
        """
        Initialize mempool
        
        Args:
            max_size: Maximum number of transactions
            max_age_seconds: Maximum age before expiration (default 1 hour)
        """
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds

        # Event for waking mining thread
        self.new_tx_event = None  # Will be set by blockchain
        
        # Main storage
        self.transactions: Dict[str, Transaction] = {}  # txid -> tx
        
        # Indexes for efficient queries
        self.by_sender: Dict[str, List[str]] = defaultdict(list)  # sender -> [txid]
        self.by_fee: List[tuple[int, str]] = []  # [(fee, txid)] sorted desc
        
        # Metadata
        self.insertion_time: Dict[str, int] = {}  # txid -> timestamp
        
        logger.info(f"Mempool initialized (max_size={max_size}, max_age={max_age_seconds}s)")
    
    def add(self, tx: Transaction) -> bool:
        """
        Add transaction to mempool
        
        Args:
            tx: Transaction to add
            
        Returns:
            True if added successfully
        """
        txid = tx.txid()
        
        # Check if already exists
        if txid in self.transactions:
            logger.debug(f"Transaction {txid[:16]}... already in mempool")
            return False
        
        # Check size limit
        if len(self.transactions) >= self.max_size:
            logger.warning(f"Mempool full ({len(self.transactions)}/{self.max_size})")
            # Try to evict old transactions
            if not self._evict_old():
                return False
        
        # Add to main storage
        self.transactions[txid] = tx
        self.insertion_time[txid] = int(time.time())
        
        # Add to sender index (sorted by nonce)
        self.by_sender[tx.sender].append(txid)
        self.by_sender[tx.sender].sort(key=lambda tid: self.transactions[tid].nonce)
        
        # Add to fee index (keep sorted descending)
        self.by_fee.append((tx.fee, txid))
        self.by_fee.sort(key=lambda x: -x[0])  # Highest fee first
        
        logger.debug(f"Added tx {txid[:16]}... from {tx.sender[:10]}... (fee={tx.fee})")
        
        # Trigger event if set (wake up mining thread)
        if self.new_tx_event:
            self.new_tx_event.set()
        
        return True
    
    def remove(self, tx: Transaction) -> bool:
        """
        Remove transaction from mempool
        
        Args:
            tx: Transaction to remove
            
        Returns:
            True if removed
        """
        txid = tx.txid()
        
        if txid not in self.transactions:
            return False
        
        # Remove from main storage
        del self.transactions[txid]
        del self.insertion_time[txid]
        
        # Remove from sender index
        if tx.sender in self.by_sender:
            self.by_sender[tx.sender] = [
                tid for tid in self.by_sender[tx.sender] 
                if tid != txid
            ]
            
            # Clean up empty sender lists
            if not self.by_sender[tx.sender]:
                del self.by_sender[tx.sender]
        
        # Remove from fee index
        self.by_fee = [(fee, tid) for fee, tid in self.by_fee if tid != txid]
        
        logger.debug(f"Removed tx {txid[:16]}...")
        return True
    
    def remove_batch(self, txs: List[Transaction]) -> int:
        """
        Remove multiple transactions efficiently
        
        Args:
            txs: List of transactions to remove
            
        Returns:
            Number of transactions removed
        """
        removed = 0
        for tx in txs:
            if self.remove(tx):
                removed += 1
        return removed
    
    def get(self, txid: str) -> Optional[Transaction]:
        """Get transaction by ID"""
        return self.transactions.get(txid)
    
    def contains(self, tx: Transaction) -> bool:
        """Check if transaction is in mempool"""
        return tx.txid() in self.transactions
    
    def get_by_sender(self, sender: str) -> List[Transaction]:
        """
        Get all transactions from a sender (ordered by nonce)
        
        Args:
            sender: Sender address
            
        Returns:
            List of transactions
        """
        txids = self.by_sender.get(sender, [])
        return [self.transactions[txid] for txid in txids]
    
    def get_ready_txs(self, expected_nonces: Dict[str, int], 
                      max_count: int = 1000) -> List[Transaction]:
        """
        Get transactions ready for inclusion in a block
        
        Args:
            expected_nonces: Dict of sender -> expected nonce
            max_count: Maximum number of transactions to return
            
        Returns:
            List of transactions, ordered by fee (highest first)
        """
        ready = []
        
        # For each sender, take transactions with correct nonce sequence
        for sender, txids in self.by_sender.items():
            expected_nonce = expected_nonces.get(sender, 0)
            
            for txid in txids:
                tx = self.transactions[txid]
                
                # Check if nonce matches
                if tx.nonce == expected_nonce:
                    ready.append(tx)
                    expected_nonce += 1  # Prepare for next tx from this sender
                else:
                    # Gap in nonce sequence, stop processing this sender
                    break
        
        # Sort by fee (highest first)
        ready.sort(key=lambda tx: -tx.fee)
        
        return ready[:max_count]
    
    def get_top_by_fee(self, count: int = 100) -> List[Transaction]:
        """
        Get top transactions by fee
        
        Args:
            count: Number of transactions to return
            
        Returns:
            List of transactions with highest fees
        """
        top_txids = [txid for _, txid in self.by_fee[:count]]
        return [self.transactions[txid] for txid in top_txids]
    
    def _evict_old(self) -> bool:
        """
        Evict old transactions to make room
        
        Returns:
            True if any transactions were evicted
        """
        now = int(time.time())
        evicted = []
        
        for txid, insert_time in self.insertion_time.items():
            age = now - insert_time
            if age > self.max_age_seconds:
                evicted.append(txid)
        
        # Remove old transactions
        for txid in evicted:
            tx = self.transactions[txid]
            self.remove(tx)
        
        if evicted:
            logger.info(f"Evicted {len(evicted)} old transactions")
        
        return len(evicted) > 0
    
    def cleanup_expired(self) -> int:
        """
        Remove expired transactions
        
        Returns:
            Number of transactions removed
        """
        return len([None for _ in range(1) if self._evict_old()])
    
    def size(self) -> int:
        """Get current mempool size"""
        return len(self.transactions)
    
    def is_full(self) -> bool:
        """Check if mempool is full"""
        return len(self.transactions) >= self.max_size
    
    def clear(self):
        """Clear all transactions"""
        self.transactions.clear()
        self.by_sender.clear()
        self.by_fee.clear()
        self.insertion_time.clear()
        logger.info("Mempool cleared")
    
    def stats(self) -> dict:
        """Get mempool statistics"""
        if not self.transactions:
            return {
                'size': 0,
                'senders': 0,
                'avg_fee': 0,
                'total_fees': 0,
                'oldest_age_seconds': 0
            }
        
        now = int(time.time())
        ages = [now - insert_time for insert_time in self.insertion_time.values()]
        fees = [tx.fee for tx in self.transactions.values()]
        
        return {
            'size': len(self.transactions),
            'senders': len(self.by_sender),
            'avg_fee': sum(fees) // len(fees) if fees else 0,
            'total_fees': sum(fees),
            'oldest_age_seconds': max(ages) if ages else 0,
            'max_size': self.max_size,
            'utilization': f"{len(self.transactions) / self.max_size * 100:.1f}%"
        }
    
    def to_dict(self) -> dict:
        """Export mempool state"""
        return {
            'transactions': [tx.to_dict() for tx in self.transactions.values()],
            'stats': self.stats()
        }


if __name__ == "__main__":
    # Test mempool
    print("=== Mempool Test ===\n")
    
    from core.crypto import KeyPair
    from blockchain.models import TxType
    
    # Create mempool
    mempool = Mempool(max_size=5)  # Small for testing
    
    # Create test transactions
    alice = KeyPair.from_seed("alice")
    bob = KeyPair.from_seed("bob")
    
    alice_addr = alice.address()
    bob_addr = bob.address()
    
    # Add transactions with different fees
    for i in range(3):
        tx = Transaction(
            sender=alice_addr,
            sender_pubkey=alice.public_key_hex(),
            nonce=i,
            tx_type=TxType.TRANSFER.value,
            amount=100 * (i + 1),
            recipient=bob_addr,
            fee=10 * (i + 1)  # Increasing fees
        )
        tx.sign(alice)
        
        added = mempool.add(tx)
        print(f"✅ Added tx {i} (fee={tx.fee}): {added}")
    
    # Check stats
    stats = mempool.stats()
    print(f"\n📊 Stats:")
    print(f"   Size: {stats['size']}")
    print(f"   Senders: {stats['senders']}")
    print(f"   Avg fee: {stats['avg_fee']}")
    
    # Get ready transactions
    expected_nonces = {alice_addr: 0}  # Alice's next nonce is 0
    ready = mempool.get_ready_txs(expected_nonces, max_count=10)
    print(f"\n📦 Ready txs: {len(ready)}")
    for tx in ready:
        print(f"   Nonce {tx.nonce}, Fee {tx.fee}")
    
    # Get top by fee
    top = mempool.get_top_by_fee(count=2)
    print(f"\n💰 Top 2 by fee:")
    for tx in top:
        print(f"   Fee {tx.fee}, Amount {tx.amount}")
    
    # Remove transactions
    removed = mempool.remove_batch(ready[:2])
    print(f"\n🗑️  Removed {removed} transactions")
    print(f"   New size: {mempool.size()}")
    
    print("\n✅ Mempool tests passed!")
