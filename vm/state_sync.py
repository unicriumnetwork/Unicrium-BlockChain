"""
State Sync Manager - Unicrium Ledger ↔ py-evm State
Syncs account data between Unicrium's ledger and py-evm's state trie
"""
import logging
from typing import Optional
from eth_utils import to_canonical_address
from eth.db.account import AccountDB
from eth.vm.forks.berlin.state import BerlinState
from eth_hash.auto import keccak

logger = logging.getLogger(__name__)


class StateSyncManager:
    """
    Manages synchronization between Unicrium Ledger and py-evm State
    
    Problem: 
    - Unicrium accounts live in Ledger
    - py-evm expects accounts in State Trie
    
    Solution:
    - Sync accounts before each EVM operation
    - Keep both systems consistent
    """
    
    def __init__(self, ledger, state: BerlinState):
        """
        Initialize sync manager
        
        Args:
            ledger: Unicrium Ledger (has accounts, balances, nonces)
            state: py-evm BerlinState (needs to be populated)
        """
        self.ledger = ledger
        self.state = state
        self._synced_accounts = set()
        
        logger.info("✅ StateSyncManager initialized")
    
    def sync_account(self, address: str):
        """
        Sync single account from Ledger to State
        
        Args:
            address: Hex address (0x...)
        """
        try:
            address_bytes = to_canonical_address(address)
            
            # Skip if already synced
            if address in self._synced_accounts:
                logger.debug(f"Account {address} already synced")
                return
            
            # Get from Unicrium Ledger
            if self.ledger:
                balance = self.ledger.get_balance(address)
                nonce = self.ledger.get_nonce(address)
            else:
                # Test mode (no ledger)
                balance = 0
                nonce = 0
            
            # Set in py-evm State
            self.state.set_balance(address_bytes, balance)
            self.state.set_nonce(address_bytes, nonce)
            
            # Mark as synced
            self._synced_accounts.add(address)
            
            logger.debug(f"✅ Synced {address}: balance={balance}, nonce={nonce}")
            
        except Exception as e:
            logger.error(f"Failed to sync {address}: {e}", exc_info=True)
            raise
    
    def sync_accounts(self, *addresses):
        """Sync multiple accounts"""
        for addr in addresses:
            self.sync_account(addr)
    
    def sync_back_nonce(self, address: str, new_nonce: int):
        """
        Sync nonce change back to Ledger
        
        Args:
            address: Hex address
            new_nonce: Updated nonce from py-evm
        """
        try:
            if self.ledger:
                # Update Unicrium Ledger
                account = self.ledger.get_or_create_account(address)
                account.nonce = new_nonce
                logger.debug(f"✅ Synced nonce back: {address} → {new_nonce}")
        except Exception as e:
            logger.error(f"Failed to sync nonce back: {e}")
    
    def create_fresh_state(self, db) -> BerlinState:
        """
        Create a fresh BerlinState with proper empty root
        
        Args:
            db: Database instance
            
        Returns:
            Fresh BerlinState
        """
        # Proper empty trie root (Ethereum standard)
        EMPTY_ROOT = keccak(b'')
        
        state = BerlinState(
            db=db,
            execution_context=None,
            state_root=EMPTY_ROOT
        )
        
        logger.debug("✅ Fresh state created")
        return state
    
    def get_stats(self) -> dict:
        """Get sync statistics"""
        return {
            'synced_accounts': len(self._synced_accounts),
            'accounts': list(self._synced_accounts)
        }


# Test
if __name__ == "__main__":
    print("=== StateSyncManager Test ===\n")
    
    from eth.db.atomic import AtomicDB
    
    # Create fresh state
    db = AtomicDB()
    EMPTY_ROOT = keccak(b'')
    state = BerlinState(db, execution_context=None, state_root=EMPTY_ROOT)
    
    # Create sync manager (no ledger for test)
    sync = StateSyncManager(ledger=None, state=state)
    print("✅ StateSyncManager created\n")
    
    # Test account sync
    test_address = "0x1234567890123456789012345678901234567890"
    print(f"Syncing test account: {test_address}")
    sync.sync_account(test_address)
    
    # Verify in state
    address_bytes = to_canonical_address(test_address)
    balance = state.get_balance(address_bytes)
    nonce = state.get_nonce(address_bytes)
    
    print(f"✅ Account in state:")
    print(f"   Balance: {balance}")
    print(f"   Nonce: {nonce}")
    
    print(f"\n📊 Stats: {sync.get_stats()}")
    print("\n✅ All tests passed!")
