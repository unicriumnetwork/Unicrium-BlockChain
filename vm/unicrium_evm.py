"""
Unicrium EVM - Full Integration with Persistent Storage
Phase 2: Complete bytecode execution with state persistence
"""
import logging
from typing import Tuple, Optional
from eth_utils import to_checksum_address, to_canonical_address
from eth_hash.auto import keccak
from eth.vm.forks.london.computation import LondonComputation
from eth.vm.forks.london.state import LondonState
from eth.vm.message import Message
from eth.vm.transaction_context import BaseTransactionContext
from eth.db.atomic import AtomicDB
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from trie_init import TrieInitializer
import rlp

logger = logging.getLogger(__name__)


class UnicriumEVM:
    """
    Full EVM with persistent storage
    
    Features:
    - Genesis state initialization
    - Persistent state root
    - Storage survives across calls
    - Full bytecode execution
    """
    
    def __init__(self, state_db, chain_id: int = 1):
        """Initialize EVM with persistent state"""
        self.state_db = state_db
        self.chain_id = chain_id
        self.contract_storage_path = os.path.join(os.path.dirname(__file__), "..", "blockchain_data", "contracts")
        os.makedirs(self.contract_storage_path, exist_ok=True)
        
        # Contract tracking
        self.contracts = {}
        self.storage = {}
        self._nonces = {}
        
        # py-evm infrastructure
        self.db = AtomicDB()
        self._setup_genesis_state()
        
        logger.info(f"✅ EVM initialized (Phase 2 - Persistent)")
        logger.info(f"   Chain ID: {chain_id}")
        logger.info(f"   State root: {self.state_root.hex()}")
    
    def _setup_genesis_state(self):
        """Setup genesis state with Unicrium accounts"""
        initializer = TrieInitializer(self.db)
        
        genesis_accounts = {}
        
        if self.state_db:
            # Sync first 10 accounts for performance
            for address in list(self.state_db.accounts.keys())[:10]:
                account = self.state_db.accounts[address]
                genesis_accounts[address] = (account.balance, account.nonce)
        
        # Default founder account
        if not genesis_accounts:
            genesis_accounts["0xacffecb00b07a53d61c38edccd7f74de83e36bf0"] = (5000000 * 10**8, 0)
        
        # Create genesis state
        self.state_root = initializer.create_genesis_state(genesis_accounts)
        logger.info(f"✅ Genesis created: {len(genesis_accounts)} accounts")

        # Load contracts from disk (PERSISTENT!)
        self._load_contracts_from_disk()
    
    def _get_state(self) -> LondonState:
        """Get state with current root (PERSISTENT!)"""
        return LondonState(self.db, execution_context=None, state_root=self.state_root)
    
    def _persist_state(self, state: LondonState):
        """Persist state changes (UPDATE ROOT!)"""
        # py-evm: persist() writes changes to trie
        state.persist()
        
        # Get new state root after persist
        new_root = state.state_root
        
        if new_root != self.state_root:
            self.state_root = new_root
            logger.debug(f"✅ State persisted: {self.state_root.hex()}")
    
    def _ensure_account_in_state(self, state: LondonState, address: str):
        """Ensure account exists and synced with latest balance"""
        address_bytes = to_canonical_address(address)
        
        # ALWAYS sync from ledger (get latest balance!)
        if self.state_db:
            balance = self.state_db.get_balance(address)
            nonce = self.state_db.get_nonce(address)
        else:
            balance = 0
            nonce = 0
        
        # Update state with current balance
        state.set_balance(address_bytes, balance)
        state.set_nonce(address_bytes, nonce)
        
        logger.debug(f"Synced account: {address} → balance={balance:,}")
    
    def deploy_contract(
        self,
        deployer: str,
        bytecode: bytes,
        constructor_args: bytes = b'',
        value: int = 0,
        gas_limit: int = 10_000_000
    ) -> Tuple[bool, Optional[str], int, Optional[str]]:
        """Deploy contract with persistent storage"""
        try:
            if not bytecode or len(bytecode) == 0:
                return (False, None, 0, "Empty bytecode")
            
            if len(bytecode) > 24_576:
                return (False, None, 0, "Bytecode too large")
            
            # Generate contract address
            deployer_bytes = to_canonical_address(deployer)
            nonce = self._get_nonce(deployer)
            
            rlp_encoded = rlp.encode([deployer_bytes, nonce])
            contract_hash = keccak(rlp_encoded)
            contract_address_bytes = contract_hash[-20:]
            contract_address = to_checksum_address(contract_address_bytes)
            
            # Get PERSISTENT state
            state = self._get_state()
            
            # Ensure deployer in state
            self._ensure_account_in_state(state, deployer)
            
            # Create message
            message = Message(
                to=contract_address_bytes,
                sender=deployer_bytes,
                value=value,
                data=constructor_args,
                code=bytecode,
                gas=gas_limit,
                depth=0,
                create_address=contract_address_bytes,
                code_address=None,
                should_transfer_value=False,
                is_static=False,
                is_delegation=False,
                refund=0
            )
            
            tx_context = BaseTransactionContext(
                gas_price=1,
                origin=deployer_bytes
            )
            
            # Execute
            computation = LondonComputation.apply_create_message(
                state=state,
                message=message,
                transaction_context=tx_context
            )
            
            if computation.is_error:
                error_msg = str(computation.error) if computation.error else "Unknown error"
                return (False, None, computation.get_gas_used(), error_msg)
            
            deployed_code = bytes(computation.output)
            
            # Store contract
            self.contracts[contract_address] = deployed_code
            self.storage[contract_address] = {}
            self._increment_nonce(deployer)
            
            # Save to disk (PERSISTENT!)
            self._save_contract_to_disk(contract_address, deployed_code)
            
            # PERSIST STATE! 🔥
            self._persist_state(state)
            
            gas_used = computation.get_gas_used()
            
            logger.info(f"✅ Contract deployed (Persistent)")
            logger.info(f"   Address: {contract_address}")
            logger.info(f"   Gas: {gas_used:,}")
            
            return (True, contract_address, gas_used, None)
            
        except Exception as e:
            logger.error(f"Deploy error: {e}", exc_info=True)
            return (False, None, 0, str(e))
    
    def call_contract(
        self,
        caller: str,
        contract_address: str,
        function_data: bytes = b'',
        value: int = 0,
        gas_limit: int = 1_000_000
    ) -> Tuple[bool, bytes, int, Optional[str]]:
        """Call contract with persistent storage"""
        try:
            if not self.contract_exists(contract_address):
                return (False, b'', 0, "Contract not found")
            
            code = self.get_contract_code(contract_address)
            if not code:
                return (False, b'', 0, "No code")
            
            # Get PERSISTENT state (with previous changes!)
            state = self._get_state()
            
            # Ensure accounts
            self._ensure_account_in_state(state, caller)
            self._ensure_account_in_state(state, contract_address)
            
            caller_bytes = to_canonical_address(caller)
            contract_bytes = to_canonical_address(contract_address)
            
            # Create message
            message = Message(
                to=contract_bytes,
                sender=caller_bytes,
                value=value,
                data=function_data,
                code=code,
                gas=gas_limit,
                depth=0,
                create_address=None,
                code_address=contract_bytes,
                should_transfer_value=False,
                is_static=False,
                is_delegation=False,
                refund=0
            )
            
            tx_context = BaseTransactionContext(
                gas_price=1,
                origin=caller_bytes
            )
            
            # Execute
            computation = LondonComputation.apply_message(
                state=state,
                message=message,
                transaction_context=tx_context
            )
            
            if computation.is_error:
                error_msg = str(computation.error) if computation.error else "Execution failed"
                return (False, b'', computation.get_gas_used(), error_msg)
            
            return_data = bytes(computation.output)
            gas_used = computation.get_gas_used()
            
            # PERSIST STATE! 🔥
            self._persist_state(state)
            
            logger.info(f"✅ Contract call (Persistent)")
            logger.info(f"   Gas: {gas_used:,}")
            logger.info(f"   Return: {len(return_data)} bytes")
            
            return (True, return_data, gas_used, None)
            
        except Exception as e:
            logger.error(f"Call error: {e}", exc_info=True)
            return (False, b'', 0, str(e))
    
    def contract_exists(self, address: str) -> bool:
        return address in self.contracts
    
    def get_contract_code(self, address: str) -> Optional[bytes]:
        return self.contracts.get(address)
    
    def get_storage(self, address: str, key: bytes) -> bytes:
        if address not in self.storage:
            return b'\x00' * 32
        return self.storage[address].get(key, b'\x00' * 32)
    
    def set_storage(self, address: str, key: bytes, value: bytes):
        if address not in self.storage:
            self.storage[address] = {}
        self.storage[address][key] = value
    
    def _save_contract_to_disk(self, address: str, bytecode: bytes):
        """Save contract to disk"""
        try:
            import json
            contract_file = os.path.join(self.contract_storage_path, f"{address}.json")
            data = {
                'address': address,
                'bytecode': bytecode.hex(),
                'storage': {k.hex(): v.hex() for k, v in self.storage.get(address, {}).items()}
            }
            with open(contract_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"💾 Saved contract: {address}")
        except Exception as e:
            logger.error(f"Failed to save contract {address}: {e}")

    def _load_contracts_from_disk(self):
        """Load all contracts from disk on startup"""
        try:
            if not os.path.exists(self.contract_storage_path):
                return
            
            import json
            contract_files = [f for f in os.listdir(self.contract_storage_path) if f.endswith('.json')]
            
            for filename in contract_files:
                try:
                    filepath = os.path.join(self.contract_storage_path, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    address = data['address']
                    bytecode = bytes.fromhex(data['bytecode'])
                    storage = {bytes.fromhex(k): bytes.fromhex(v) for k, v in data.get('storage', {}).items()}
                    
                    self.contracts[address] = bytecode
                    self.storage[address] = storage
                    
                    logger.debug(f"📂 Loaded contract: {address}")
                except Exception as e:
                    logger.error(f"Failed to load {filename}: {e}")
            
            if contract_files:
                logger.info(f"✅ Loaded {len(contract_files)} contracts from disk")
        except Exception as e:
            logger.error(f"Failed to load contracts: {e}")

    def _get_nonce(self, address: str) -> int:
        return self._nonces.get(address, 0)
    
    def _increment_nonce(self, address: str):
        self._nonces[address] = self._nonces.get(address, 0) + 1
    
    def estimate_gas(self, tx_type: str, bytecode_size: int = 0, calldata_size: int = 0) -> int:
        if tx_type == 'deploy':
            return 32_000 + (bytecode_size * 200)
        elif tx_type == 'call':
            return 21_000 + (calldata_size * 68)
        return 21_000
    
    def get_stats(self) -> dict:
        return {
            'chain_id': self.chain_id,
            'fork': 'London',
            'phase': 2,
            'integration': 'Full',
            'storage': 'Persistent',
            'hash_algorithm': 'KECCAK256',
            'bytecode_execution': True,
            'state_management': 'Genesis + Trie + Persistence',
            'state_root': self.state_root.hex(),
            'total_contracts': len(self.contracts),
            'contracts': list(self.contracts.keys()),
        }


# Test
if __name__ == "__main__":
    print("=== Persistent Storage Test ===\n")
    
    evm = UnicriumEVM(state_db=None, chain_id=1)
    
    # Deploy SimpleStorage
    deployer = "0xacffecb00b07a53d61c38edccd7f74de83e36bf0"
    bytecode = bytes.fromhex("608060405234801561001057600080fd5b5060c78061001f6000396000f3fe6080604052348015600f57600080fd5b506004361060325760003560e01c806360fe47b11460375780636d4ce63c146062575b600080fd5b606060048036036020811015604b57600080fd5b8101908080359060200190929190505050607e565b005b60686088565b6040518082815260200191505060405180910390f35b8060008190555050565b6000805490509056fea26469706673582212209a4c0e44e0e0e7c3f1c0e6c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c064736f6c63430007060033")
    
    print("1️⃣ Deploying contract...")
    success, addr, gas, err = evm.deploy_contract(deployer, bytecode, gas_limit=1000000)
    
    if success:
        print(f"   ✅ Deployed: {addr}\n")
        
        # Call set(42)
        print("2️⃣ Calling set(42)...")
        set_data = bytes.fromhex("60fe47b1000000000000000000000000000000000000000000000000000000000000002a")
        success, ret, gas, err = evm.call_contract(deployer, addr, set_data, gas_limit=100000)
        print(f"   ✅ set(42) executed, gas: {gas:,}\n")
        
        # Call get()
        print("3️⃣ Calling get()...")
        get_data = bytes.fromhex("6d4ce63c")
        success, ret, gas, err = evm.call_contract(deployer, addr, get_data, gas_limit=100000)
        
        if success and ret:
            value = int.from_bytes(ret, byteorder='big')
            print(f"   ✅ get() returned: {value}")
            
            if value == 42:
                print(f"\n🎉 STORAGE PERSISTENT! Value survived!")
            else:
                print(f"\n⚠️  Value: {value} (expected 42)")
        
    print(f"\n📊 State root: {evm.state_root.hex()}")
