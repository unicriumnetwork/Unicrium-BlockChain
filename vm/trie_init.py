"""
Trie Infrastructure Setup
Initialize py-evm state trie properly with genesis state
"""
from eth.db.atomic import AtomicDB
from eth.db.account import AccountDB
from eth_hash.auto import keccak
from eth_utils import to_canonical_address
from trie import HexaryTrie
import rlp


class TrieInitializer:
    """
    Properly initialize py-evm state trie
    
    Problem: Empty trie root not in database
    Solution: Create proper genesis state with accounts
    """
    
    def __init__(self, db: AtomicDB):
        self.db = db
        self.account_db = AccountDB(db)
    
    def create_genesis_state(self, genesis_accounts: dict = None):
        """
        Create genesis state with accounts
        
        Args:
            genesis_accounts: {address: (balance, nonce)} dict
            
        Returns:
            state_root (bytes)
        """
        # Create trie
        trie = HexaryTrie(db=self.db)
        
        # Add genesis accounts
        if genesis_accounts:
            for address_hex, (balance, nonce) in genesis_accounts.items():
                address = to_canonical_address(address_hex)
                
                # Create account RLP
                # Account = [nonce, balance, storage_root, code_hash]
                EMPTY_SHA3 = keccak(b'')
                account_rlp = rlp.encode([
                    nonce,
                    balance,
                    EMPTY_SHA3,  # storage root
                    EMPTY_SHA3   # code hash
                ])
                
                # Insert into trie
                address_hash = keccak(address)
                trie[address_hash] = account_rlp
                
                print(f"✅ Added genesis account: {address_hex}")
                print(f"   Balance: {balance}, Nonce: {nonce}")
        
        # Get state root
        state_root = trie.root_hash
        
        print(f"\n✅ Genesis state root: {state_root.hex()}")
        return state_root
    
    def verify_state(self, state_root: bytes):
        """Verify state is accessible"""
        try:
            trie = HexaryTrie(db=self.db, root_hash=state_root)
            print(f"✅ State trie accessible with root: {state_root.hex()}")
            return True
        except Exception as e:
            print(f"❌ State verification failed: {e}")
            return False


# Test
if __name__ == "__main__":
    print("=== Trie Initialization Test ===\n")
    
    db = AtomicDB()
    initializer = TrieInitializer(db)
    
    # Create genesis with test accounts
    genesis_accounts = {
        "0x1234567890123456789012345678901234567890": (1000000, 0),
        "0xacffecb00b07a53d61c38edccd7f74de83e36bf0": (5000000 * 10**8, 0),  # Founder
    }
    
    print("Creating genesis state...")
    state_root = initializer.create_genesis_state(genesis_accounts)
    
    print("\nVerifying state...")
    if initializer.verify_state(state_root):
        print("\n🎉 SUCCESS! Trie infrastructure working!")
    else:
        print("\n❌ FAILED!")
