"""
Core data models for the blockchain
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Adım 1'de güncellenen crypto modülünü import ediyoruz
from core.crypto import hash_object, verify_dict_signature, is_valid_address, KeyPair


class TxType(Enum):
    """Transaction types"""
    # === BASIC TYPES ===
    TRANSFER = "transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    DELEGATE = "delegate"
    UNDELEGATE = "undelegate"
    VOTE = "vote"
    CREATE_VALIDATOR = "create_validator"
    EDIT_VALIDATOR = "edit_validator"
    
    # === CONTRACT TYPES (Phase 0 - Future Ready) ===
    CONTRACT_DEPLOY = "contract_deploy"    # Deploy new smart contract
    CONTRACT_CALL = "contract_call"        # Call contract function
    
    # === ADVANCED TYPES (Phase 0 - Future Ready) ===
    BATCH_TRANSFER = "batch_transfer"      # Batch transfers (gas efficient)


class TxStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    INCLUDED = "included"
    FAILED = "failed"


@dataclass(frozen=True)
class Transaction:
    """Blockchain transaction with contract support"""
    # === BASIC FIELDS ===
    sender: str  # Address (0x... 42 hex chars)
    sender_pubkey: Optional[str] = None  # Public key hex (for verification)
    nonce: int = 0
    tx_type: str = ""  # TxType value
    amount: int = 0
    recipient: Optional[str] = None
    fee: int = 0
    gas_limit: int = 100_000
    gas_price: int = 1  # Gas price (user can set higher for priority)
    data: Dict[str, Any] = field(default_factory=dict)
    signature: str = ""
    timestamp: int = field(default_factory=lambda: int(time.time()))
    
    # === CONTRACT FIELDS (Phase 0 - Future Ready) ===
    contract_address: Optional[str] = None       # Target contract address (for CONTRACT_CALL)
    contract_bytecode: Optional[bytes] = None    # Contract bytecode (for CONTRACT_DEPLOY)
    contract_input: Optional[bytes] = None       # Function call data / constructor args
    contract_value: int = 0                      # UNI value sent to contract (payable functions)
    
    # === BATCH FIELDS (Phase 0 - Future Ready) ===
    batch_recipients: List[str] = field(default_factory=list)  # For BATCH_TRANSFER
    batch_amounts: List[int] = field(default_factory=list)     # For BATCH_TRANSFER
    
    # === FUTURE-PROOF FIELDS ===
    version: int = 1                             # TX version (for future upgrades)
    extra_data: bytes = b''                      # Additional data (max 1KB)
    
    def __post_init__(self):
        """Validate transaction"""
        # Adım 1'de güncellenen is_valid_address (0x... destekli)
        if not is_valid_address(self.sender):
            raise ValueError(f"Invalid sender address: {self.sender}")
        
        if self.recipient and not is_valid_address(self.recipient):
            raise ValueError(f"Invalid recipient address: {self.recipient}")
        
        if self.amount < 0 or self.fee < 0:
            raise ValueError("Amount and fee must be non-negative")
        
        if self.nonce < 0:
            raise ValueError("Nonce must be non-negative")
    
    def payload(self) -> dict:
        """Get signable payload (excludes signature)"""
        return {
            "sender": self.sender,
            "sender_pubkey": self.sender_pubkey,
            "nonce": self.nonce,
            "tx_type": self.tx_type,
            "amount": self.amount,
            "recipient": self.recipient,
            "fee": self.fee,
            "gas_limit": self.gas_limit,
            "data": self.data,
            "timestamp": self.timestamp,
        }
    
    def txid(self) -> str:
        """Get transaction ID (hash of payload)"""
        # Adım 1'de güncellenen hash_object (sha256)
        return hash_object(self.payload())
    
    def sign(self, keypair: KeyPair) -> Transaction:
        """Sign transaction with keypair"""
        # Create payload WITH sender_pubkey before signing
        payload_with_pubkey = {
            **self.payload(),
            "sender_pubkey": keypair.public_key_hex()
        }
        # Adım 1'de güncellenen sign_dict (ecdsa)
        signature = keypair.sign_dict(payload_with_pubkey)
        
        # frozen=True olduğu için object.__setattr__ kullanıyoruz
        object.__setattr__(self, 'signature', signature)
        object.__setattr__(self, 'sender_pubkey', keypair.public_key_hex())
        return self
    
    def verify_signature(self) -> bool:
        """Verify transaction signature"""
        if not self.signature or not self.sender_pubkey:
            return False
        try:
            public_key = bytes.fromhex(self.sender_pubkey)
            # Adım 1'de güncellenen verify_dict_signature (ecdsa)
            return verify_dict_signature(public_key, self.payload(), self.signature)
        except (ValueError, TypeError):
            return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary - ALL bytes to hex/string"""
        d = asdict(self)
        
        # CRITICAL: Convert ALL bytes fields to JSON-safe types
        # contract_bytecode
        if isinstance(d.get('contract_bytecode'), bytes):
            d['contract_bytecode'] = d['contract_bytecode'].hex() if d['contract_bytecode'] else None
        
        # contract_input  
        if isinstance(d.get('contract_input'), bytes):
            d['contract_input'] = d['contract_input'].hex() if d['contract_input'] else None
        
        # extra_data - ALWAYS convert even if empty!
        if isinstance(d.get('extra_data'), bytes):
            d['extra_data'] = d['extra_data'].hex()  # b'' becomes ''
        
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Transaction:
        """Create from dictionary with backward compatibility"""
        # Convert hex strings back to bytes
        if 'contract_bytecode' in data and isinstance(data.get('contract_bytecode'), str):
            data['contract_bytecode'] = bytes.fromhex(data['contract_bytecode']) if data['contract_bytecode'] else None
        if 'contract_input' in data and isinstance(data.get('contract_input'), str):
            data['contract_input'] = bytes.fromhex(data['contract_input']) if data['contract_input'] else None
        if 'extra_data' in data and isinstance(data.get('extra_data'), str):
            data['extra_data'] = bytes.fromhex(data['extra_data']) if data['extra_data'] else b''
        
        # Backward compatibility: set defaults for new fields
        data.setdefault('contract_address', None)
        data.setdefault('contract_bytecode', None)
        data.setdefault('contract_input', None)
        data.setdefault('contract_value', 0)
        data.setdefault('batch_recipients', [])
        data.setdefault('batch_amounts', [])
        data.setdefault('version', 1)
        data.setdefault('gas_price', 1)
        data.setdefault('extra_data', b'')
        data.setdefault('gas_price', 1)  # CRITICAL: Backward compatibility
        
        return cls(**data)


@dataclass
class ValidatorInfo:
    """Validator information"""
    address: str
    public_key: str
    stake: int
    delegated_stake: int
    commission_rate: float  # 0.0 to 1.0
    jailed: bool = False
    jailed_until: int = 0
    total_blocks_proposed: int = 0
    total_blocks_missed: int = 0
    created_at: int = field(default_factory=lambda: int(time.time()))
    
    def total_stake(self) -> int:
        """Total voting power"""
        return self.stake + self.delegated_stake
    
    def is_active(self, current_height: int, min_stake: int) -> bool:
        """Check if validator is active"""
        if self.jailed and current_height < self.jailed_until:
            return False
        return self.total_stake() >= min_stake
    
    def to_dict(self) -> dict:
        """Convert Block to dictionary with Transaction serialization"""
        d = asdict(self)
        
        # Convert transactions to dict (they have their own to_dict)
        d['transactions'] = [tx.to_dict() for tx in self.transactions]
        
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ValidatorInfo:
        return cls(**data)


@dataclass
class Delegation:
    """Delegation record"""
    delegator: str
    validator: str
    amount: int
    created_at: int = field(default_factory=lambda: int(time.time()))
    
    def to_dict(self) -> dict:
        """Convert Block to dictionary with Transaction serialization"""
        d = asdict(self)
        
        # Convert transactions to dict (they have their own to_dict)
        d['transactions'] = [tx.to_dict() for tx in self.transactions]
        
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Delegation:
        return cls(**data)


@dataclass
class UnbondingEntry:
    """Unbonding/undelegation entry"""
    address: str
    validator: Optional[str]  # None for unstaking, address for undelegation
    amount: int
    completion_height: int
    created_at: int = field(default_factory=lambda: int(time.time()))
    
    def is_mature(self, current_height: int) -> bool:
        """Check if unbonding is complete"""
        return current_height >= self.completion_height
    
    def to_dict(self) -> dict:
        """Convert Block to dictionary with Transaction serialization"""
        d = asdict(self)
        
        # Convert transactions to dict (they have their own to_dict)
        d['transactions'] = [tx.to_dict() for tx in self.transactions]
        
        return d

    @classmethod
    def from_dict(cls, data: dict) -> UnbondingEntry:
        return cls(**data)


@dataclass
class Block:
    """
    Blockchain block with future-proof contract support
    
    Core fields for transactions, PoS consensus, and mining rewards
    Extended with contract execution tracking and protocol versioning
    """
    # === CORE FIELDS ===
    height: int
    prev_hash: str
    timestamp: int
    proposer: str  # Validator address
    proposer_pubkey: str = ""  # Public key for signature verification
    
    # === TRANSACTIONS ===
    transactions: List[Transaction] = field(default_factory=list)
    
    # === MERKLE ROOTS ===
    tx_root: str = ""           # Merkle root of transactions
    state_root: str = ""        # State merkle root
    
    # === VALIDATOR SET ===
    validator_set_hash: str = ""
    next_validator_set_hash: str = ""
    
    # === CONSENSUS ===
    consensus_hash: str = ""    # Hash of consensus parameters
    app_hash: str = ""          # Application state hash
    signature: str = ""         # Block signature
    hash: str = ""              # Block hash
    
    # === ECONOMICS ===
    total_fees: int = 0         # Total fees from transactions
    block_reward: int = 0       # Mining reward for this block
    
    # === CONTRACT SUPPORT (Phase 0 - Future Ready) ===
    contracts_deployed: int = 0      # Number of contracts deployed in this block
    contract_calls: int = 0          # Number of contract calls in this block
    contract_gas_used: int = 0       # Total gas used by contract operations
    
    # === VM VERSIONING ===
    vm_version: str = "none"         # VM version: "none", "evm-0.1", "uvm-0.1", "wasm-0.1"
    
    # === PROTOCOL UPGRADES ===
    protocol_version: int = 1        # Protocol version (for hard forks)
    
    # === FUTURE-PROOF FIELDS ===
    extra_data: str = ""             # Max 256 bytes for future protocol extensions
    reserved_field1: int = 0         # Reserved for future integer data
    reserved_field2: int = 0         # Reserved for future integer data
    reserved_field3: str = ""        # Reserved for future string data
    next_validator_set_hash: str = ""
    consensus_hash: str = ""  # Hash of consensus parameters
    app_hash: str = ""  # Application state hash
    total_fees: int = 0
    block_reward: int = 0
    signature: str = ""
    hash: str = ""
    
    def header(self) -> dict:
        """Get block header"""
        return {
            "height": self.height,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "proposer": self.proposer,
            "proposer_pubkey": self.proposer_pubkey,
            "state_root": self.state_root,
            "validator_set_hash": self.validator_set_hash,
            "next_validator_set_hash": self.next_validator_set_hash,
            "consensus_hash": self.consensus_hash,
            "app_hash": self.app_hash,
            "tx_count": len(self.transactions),
            "tx_merkle_root": self.tx_root,
            "total_fees": self.total_fees,
            "block_reward": self.block_reward,
            # NEW: Contract fields
            "contracts_deployed": self.contracts_deployed,
            "contract_calls": self.contract_calls,
            "contract_gas_used": self.contract_gas_used,
            "vm_version": self.vm_version,
            "protocol_version": self.protocol_version,
        }
    
    # _compute_tx_root fonksiyonu kaldırıldı, artık tx_root dışarıdan set ediliyor.
    # (bkz: blockchain.py -> create_block)
    
    def compute_hash(self) -> str:
        """Compute block hash"""
        header_data = self.header()
        header_data["signature"] = self.signature
        # Adım 1'de güncellenen hash_object (sha256)
        return hash_object(header_data)
    
    def sign(self, keypair: KeyPair) -> Block:
        """Sign block with proposer's key"""
        # Create header WITH proposer_pubkey before signing
        header_with_pubkey = {
            **self.header(),
            "proposer_pubkey": keypair.public_key_hex()
        }
        # Adım 1'de güncellenen sign_dict (ecdsa)
        signature = keypair.sign_dict(header_with_pubkey)
        
        # frozen=True olmadığı için normal atama
        self.signature = signature
        self.proposer_pubkey = keypair.public_key_hex()
        self.hash = self.compute_hash()
        return self
    
    def verify_signature(self) -> bool:
        """Verify block signature"""
        if not self.signature or not self.proposer_pubkey:
            return False
        try:
            public_key = bytes.fromhex(self.proposer_pubkey)
            # Adım 1'de güncellenen verify_dict_signature (ecdsa)
            return verify_dict_signature(public_key, self.header(), self.signature)
        except (ValueError, TypeError):
            return False
    
    def to_dict(self) -> dict:
        """Convert Block to dictionary with Transaction serialization"""
        d = asdict(self)
        
        # Convert transactions to dict (they have their own to_dict)
        d['transactions'] = [tx.to_dict() for tx in self.transactions]
        
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Block:
        """Create from dictionary with backward compatibility"""
        txs = [Transaction.from_dict(tx) for tx in data.pop("transactions", [])]
        
        # Backward compatibility: set defaults for new fields if not present
        data.setdefault('contracts_deployed', 0)
        data.setdefault('contract_calls', 0)
        data.setdefault('contract_gas_used', 0)
        data.setdefault('vm_version', 'none')
        data.setdefault('protocol_version', 1)
        data.setdefault('extra_data', '')
        data.setdefault('reserved_field1', 0)
        data.setdefault('reserved_field2', 0)
        data.setdefault('reserved_field3', '')
        
        return cls(transactions=txs, **data)


@dataclass
class Vote:
    """Validator vote on a block"""
    validator: str
    height: int
    block_hash: str
    timestamp: int
    signature: str = ""
    
    def payload(self) -> dict:
        return {
            "validator": self.validator,
            "height": self.height,
            "block_hash": self.block_hash,
            "timestamp": self.timestamp,
        }
    
    def sign(self, keypair: KeyPair) -> Vote:
        signature = keypair.sign_dict(self.payload())
        return Vote(**{**self.__dict__, "signature": signature})
    
    def verify_signature(self, public_key_hex: str) -> bool:
        if not self.signature:
            return False
        try:
            public_key = bytes.fromhex(public_key_hex)
            return verify_dict_signature(public_key, self.payload(), self.signature)
        except (ValueError, TypeError):
            return False


@dataclass
class Evidence:
    """Evidence of misbehavior"""
    evidence_type: str  # "double_sign", "missed_blocks"
    validator: str
    height: int
    timestamp: int
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert Block to dictionary with Transaction serialization"""
        d = asdict(self)
        
        # Convert transactions to dict (they have their own to_dict)
        d['transactions'] = [tx.to_dict() for tx in self.transactions]
        
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Evidence:
        return cls(**data)


if __name__ == "__main__":
    # Test models
    print("=== Data Models Test ===\n")
    
    # Test transaction
    tx = Transaction(
        sender="0x" + "a" * 40,
        nonce=0,
        tx_type=TxType.TRANSFER.value,
        amount=1000,
        recipient="0x" + "b" * 40,
        fee=10
    )
    print(f"Transaction ID: {tx.txid()}")
    print(f"Valid sender: {is_valid_address(tx.sender)}")
    
    # Test validator
    val = ValidatorInfo(
        address="0x" + "v" * 40,
        public_key="pk" * 32,
        stake=10_000,
        delegated_stake=5_000,
        commission_rate=0.1
    )
    print(f"\nValidator total stake: {val.total_stake()}")
    print(f"Active: {val.is_active(0, 1000)}")