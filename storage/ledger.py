from eth_utils import keccak
import json
"""
Ledger - Account state management with auto-creation
"""
from dataclasses import dataclass, field
from blockchain.models import ValidatorInfo
from typing import Optional, Dict
import hashlib

@dataclass
class Account:
    """
    Account with contract support
    
    Stores balance, nonce, staking info, and contract state
    """
    # === BASIC FIELDS ===
    address: str
    balance: int = 0
    nonce: int = 0
    staked: int = 0
    
    # === CONTRACT STATE (Phase 0 - Future Ready) ===
    is_contract: bool = False                    # Is this account a smart contract?
    contract_bytecode: Optional[bytes] = None    # Contract bytecode
    contract_bytecode_hash: str = ""             # Hash of bytecode (for verification)
    contract_storage: dict = field(default_factory=dict)  # Key-value storage (persistent)
    contract_vm_type: str = "none"               # VM type: "none", "evm", "uvm", "wasm"
    contract_version: int = 0                    # Contract version
    
    # === CONTRACT METADATA ===
    contract_creator: str = ""                   # Who deployed this contract
    contract_created_at: int = 0                 # Block height when deployed
    contract_upgraded_at: int = 0                # Last upgrade block height
    
    # === ADVANCED FEATURES ===
    delegate_to: str = ""                        # Delegation target (for proxy contracts)
    is_upgradeable: bool = False                 # Can this contract be upgraded?
    
    # === FUTURE-PROOF FIELDS ===
    reserved_balance: int = 0                    # Reserved funds (for special purposes)
    metadata: dict = field(default_factory=dict) # Arbitrary metadata

@dataclass  
class Validator:
    address: str
    public_key: str
    stake: int
    delegated_stake: int = 0
    commission_rate: float = 0.1
    jailed: bool = False
    jailed_until: int = 0

class Ledger:
    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.validators: Dict[str, Validator] = {}
        self.delegations = []
        self.unbonding = []
    
    def get_or_create_account(self, address: str) -> Account:
        """Get account or create if doesn't exist"""
        if address not in self.accounts:
            self.accounts[address] = Account(address=address)
        return self.accounts[address]
    
    def get_balance(self, address: str) -> int:
        return self.get_or_create_account(address).balance
    
    def get_stake(self, address: str) -> int:
        return self.get_or_create_account(address).staked
    
    def get_nonce(self, address: str) -> int:
        return self.get_or_create_account(address).nonce
    
    def has_sufficient_balance(self, address: str, amount: int) -> bool:
        return self.get_balance(address) >= amount
    
    def apply_transaction(self, tx, current_height: int):
        """Apply transaction to ledger"""
        sender = self.get_or_create_account(tx.sender)
        
        # STAKING TRANSACTION
        if hasattr(tx, 'tx_type') and tx.tx_type == 'stake':
            stake_amount = tx.data.get('stake_amount', 0)
            total_cost = stake_amount + tx.fee
            
            if sender.balance < total_cost:
                raise ValueError(f"Insufficient balance for staking")
            
            sender.balance -= total_cost
            sender.staked += stake_amount
            sender.nonce += 1
            
            # Create or update validator
            if tx.sender not in self.validators:
                public_key = tx.data.get('public_key', getattr(tx, 'sender_pubkey', ''))
                self.validators[tx.sender] = ValidatorInfo(
                    address=tx.sender,
                    public_key=public_key,
                    stake=stake_amount,
                    delegated_stake=0,
                    commission_rate=0.1,
                    jailed=False,
                    jailed_until=0,
                    total_blocks_proposed=0,
                    total_blocks_missed=0,
                    created_at=current_height
                )
            else:
                self.validators[tx.sender].stake += stake_amount
            
            print(f"🔒 Staked {stake_amount / 10**8:,.0f} UNI")
            return

        # UNSTAKING TRANSACTION
        if hasattr(tx, 'tx_type') and tx.tx_type == 'unstake':
            unstake_amount = tx.data.get('unstake_amount', 0)
            
            if sender.staked < unstake_amount:
                raise ValueError(f"Insufficient staked balance: {sender.staked} < {unstake_amount}")
            
            if sender.balance < tx.fee:
                raise ValueError(f"Insufficient balance for fee: {sender.balance} < {tx.fee}")
            
            sender.balance -= tx.fee  # Sadece fee öde
            sender.staked -= unstake_amount
            sender.balance += unstake_amount  # Unstake edilen geri döner
            sender.nonce += 1
            
            # Validator stake güncelle
            if tx.sender in self.validators:
                self.validators[tx.sender].stake -= unstake_amount
                # Min stake altına düştüyse validator'dan çıkar
                if self.validators[tx.sender].stake < 1000 * 10**8:
                    del self.validators[tx.sender]
                    print(f"🔓 Unstaked {unstake_amount / 10**8:,.0f} UNM - No longer validator")
                else:
                    print(f"🔓 Unstaked {unstake_amount / 10**8:,.0f} UNM - Still validator")
            else:
                print(f"🔓 Unstaked {unstake_amount / 10**8:,.0f} UNM")
            return
        
        # TRANSFER TRANSACTION (default)
        recipient = self.get_or_create_account(tx.recipient)
        total_cost = tx.amount + tx.fee
        
        if sender.balance < total_cost:
            raise ValueError(f"Insufficient balance: {sender.balance} < {total_cost}")
        
        sender.balance -= total_cost
        sender.nonce += 1
        recipient.balance += tx.amount

    def transfer(self, from_addr: str, to_addr: str, amount: int) -> bool:
        """
        Safe transfer between accounts
        
        Args:
            from_addr: Sender address
            to_addr: Recipient address
            amount: Amount to transfer
        
        Returns:
            True if successful, False if insufficient balance
        """
        if amount <= 0:
            return False
        
        sender = self.get_or_create_account(from_addr)
        
        # Check balance
        if sender.balance < amount:
            return False
        
        recipient = self.get_or_create_account(to_addr)
        
        # Atomic transfer
        sender.balance -= amount
        recipient.balance += amount
        
        return True

    def increment_nonce(self, address: str):
        """
        Increment account nonce
        
        Args:
            address: Account address
        """
        account = self.get_or_create_account(address)
        account.nonce += 1

    def total_supply(self) -> int:
        """Calculate total supply"""
        return sum(acc.balance + acc.staked for acc in self.accounts.values())
    
    def total_staked(self) -> int:
        """Calculate total staked"""
        return sum(acc.staked for acc in self.accounts.values())
    
    def staking_ratio(self) -> float:
        """Calculate staking ratio"""
        supply = self.total_supply()
        if supply == 0:
            return 0.0
        return self.total_staked() / supply
    
    def state_root(self) -> str:
        """Compute deterministic state root (EVM-compatible)"""
        
        # EVM gibi state tree oluştur
        state_data = {}
        for addr in sorted(self.accounts.keys()):
            acc = self.accounts[addr]
            state_data[addr] = {
                'balance': str(acc.balance),  # String for JSON consistency
                'nonce': acc.nonce,
                'staked': str(acc.staked),
                'code_hash': ''  # EVM contract code hash placeholder
            }
        
        # Canonical JSON (Ethereum gibi)
        canonical = json.dumps(state_data, sort_keys=True, separators=(',', ':'))
        
        # Keccak256 for Ethereum compatibility
        return keccak(canonical.encode()).hex()
    def get_state(self) -> dict:
        """Export ledger state"""
        return {
            'accounts': {
                addr: {
                    'balance': acc.balance,
                    'nonce': acc.nonce,
                    'staked': acc.staked
                }
                for addr, acc in self.accounts.items()
            },
            'validators': {
                addr: {
                    'address': val.address,
                    'public_key': val.public_key,
                    'stake': val.stake,
                    'delegated_stake': val.delegated_stake,
                    'commission_rate': val.commission_rate,
                    'jailed': val.jailed,
                    'jailed_until': val.jailed_until
                }
                for addr, val in self.validators.items()
            },
            'delegations': self.delegations,
            'unbonding': self.unbonding
        }
    
    def load_state(self, state: dict):
        """Load ledger state"""
        # Load accounts
        for addr, acc_data in state.get('accounts', {}).items():
            self.accounts[addr] = Account(
                address=addr,
                balance=acc_data.get('balance', 0),
                nonce=acc_data.get('nonce', 0),
                staked=acc_data.get('staked', 0)
            )
        
        # Load validators
        for addr, val_data in state.get('validators', {}).items():
            self.validators[addr] = Validator(
                address=val_data['address'],
                public_key=val_data['public_key'],
                stake=val_data['stake'],
                delegated_stake=val_data.get('delegated_stake', 0),
                commission_rate=val_data.get('commission_rate', 0.1),
                jailed=val_data.get('jailed', False),
                jailed_until=val_data.get('jailed_until', 0)
            )
        
        self.delegations = state.get('delegations', [])
        self.unbonding = state.get('unbonding', [])
    
    def clone(self):
        """Create a deep copy"""
        new_ledger = Ledger()
        new_ledger.load_state(self.get_state())
        return new_ledger
    
    def process_mature_unbonding(self, current_height: int) -> int:
        """Process completed unbonding entries"""
        completed = 0
        remaining = []
        
        for entry in self.unbonding:
            if entry['completion_height'] <= current_height:
                # Return tokens
                acc = self.get_or_create_account(entry['delegator'])
                acc.balance += entry['amount']
                completed += 1
            else:
                remaining.append(entry)
        
        self.unbonding = remaining
        return completed
    
    def slash_validator(self, validator_addr: str, fraction: float, reason: str) -> int:
        """Slash validator stake"""
        if validator_addr in self.validators:
            val = self.validators[validator_addr]
            slash_amount = int(val.stake * fraction)
            val.stake -= slash_amount
            return slash_amount
        return 0
    
    def jail_validator(self, validator_addr: str, until_height: int):
        """Jail validator"""
        if validator_addr in self.validators:
            self.validators[validator_addr].jailed = True
            self.validators[validator_addr].jailed_until = until_height
