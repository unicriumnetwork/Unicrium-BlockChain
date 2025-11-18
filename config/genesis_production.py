"""Unicrium Genesis - 150 Year Mining Model"""
import sys
import os
import hashlib
import json
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from storage.storage import PersistentStorage as Storage
from blockchain.models import Block

def create_genesis():
    print("Creating Genesis - 150 Year Mining Model...")
    
    # Load wallets (DOĞRU ADRESLER)
    with open(os.path.join(os.path.dirname(__file__), "genesis_wallet.json"), 'r') as f:
        founder_wallet = json.load(f)
    
    with open(os.path.join(os.path.dirname(__file__), "faucet_wallet.json"), 'r') as f:
        faucet_wallet = json.load(f)
    
    with open(os.path.join(os.path.dirname(__file__), "validators.json"), 'r') as f:
        validators_data = json.load(f)
    
    # ADDRESSES
    FOUNDER_ADDRESS = founder_wallet['address']  # 0xacffecb00b07a53d61c38edccd7f74de83e36bf0
    FAUCET_ADDRESS = faucet_wallet['address']    # 0x8aa829da6b4a5be2789e3ddeff569d6248e3e503
    TREASURY_ADDRESS = "0xe3e92fb0a0160e41be8d80bee4b6a81b422c1d4c"  # Updated correct treasury
    
    # === SYSTEM ACCOUNTS (Phase 0 - Future Ready) ===
    BURN_ADDRESS = "0x0000000000000000000000000000000000000000"          # Fee burning
    CONTRACT_FACTORY = "0x0000000000000000000000000000000000000001"      # Deterministic contract addresses
    ORACLE_REGISTRY = "0x0000000000000000000000000000000000000002"       # Oracle registry
    BRIDGE_REGISTRY = "0x0000000000000000000000000000000000000003"       # Cross-chain bridges
    DAO_TREASURY = "0x0000000000000000000000000000000000000004"          # DAO treasury
    FEE_COLLECTOR = "0x0000000000000000000000000000000000000005"         # Fee collector
    REWARDS_POOL = "0x0000000000000000000000000000000000000006"          # Staking rewards pool
    
    # ALLOCATIONS
    TREASURY_ALLOCATION = 10_000_000 * 10**8   # 10M
    FOUNDER_ALLOCATION = 5_000_000 * 10**8     # 5M
    FAUCET_ALLOCATION = 1_000_000 * 10**8      # 1M
    VALIDATOR_STAKE = 100_000 * 10**8          # 100K each
    
    GENESIS_SUPPLY = TREASURY_ALLOCATION + FOUNDER_ALLOCATION + FAUCET_ALLOCATION + (VALIDATOR_STAKE * 3)
    MAX_SUPPLY = 100_000_000 * 10**8
    REMAINING_TO_MINE = MAX_SUPPLY - GENESIS_SUPPLY
    
    print(f"📊 Genesis Supply: {GENESIS_SUPPLY / 10**8:,.0f} UNI (16.3%)")
    print(f"⛏️  To be mined: {REMAINING_TO_MINE / 10**8:,.0f} UNI (83.7%)")
    print(f"🔒 Max Supply: {MAX_SUPPLY / 10**8:,.0f} UNI")
    print(f"⏰ Timeline: 150+ years")
    print()
    print(f"Founder: {FOUNDER_ADDRESS}")
    print(f"Faucet:  {FAUCET_ADDRESS}")
    print(f"Treasury: {TREASURY_ADDRESS}")
    print()
    print("🔧 System Accounts (Phase 0 - Future Ready):")
    print(f"   Burn:     {BURN_ADDRESS}")
    print(f"   Factory:  {CONTRACT_FACTORY}")
    print(f"   Oracle:   {ORACLE_REGISTRY}")
    print(f"   Bridge:   {BRIDGE_REGISTRY}")
    print(f"   DAO:      {DAO_TREASURY}")
    print(f"   FeeCol:   {FEE_COLLECTOR}")
    print(f"   Rewards:  {REWARDS_POOL}")
    
    # Storage
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blockchain_data")
    storage = Storage(storage_path)
    timestamp = int(time.time())
    
    # Genesis State
    genesis_state = {
        'accounts': {},
        'validators': {},
        'delegations': {},
        'unbonding': [],
        'nonces': {},
        'total_staked': 0
    }
    
    # Treasury
    genesis_state['accounts'][TREASURY_ADDRESS] = {
        'address': TREASURY_ADDRESS,
        'balance': TREASURY_ALLOCATION,
        'staked': 0,
        'nonce': 0
    }
    
    # Founder
    genesis_state['accounts'][FOUNDER_ADDRESS] = {
        'address': FOUNDER_ADDRESS,
        'balance': FOUNDER_ALLOCATION,
        'staked': 0,
        'nonce': 0
    }
    
    # Faucet
    genesis_state['accounts'][FAUCET_ADDRESS] = {
        'address': FAUCET_ADDRESS,
        'balance': FAUCET_ALLOCATION,
        'staked': 0,
        'nonce': 0
    }
    
    # Validators
    for i, val_data in enumerate(validators_data, 1):
        val_address = val_data['address']
        genesis_state['accounts'][val_address] = {
            'address': val_address,
            'balance': 0,
            'staked': VALIDATOR_STAKE,
            'nonce': 0
        }
        genesis_state['validators'][val_address] = {
            'address': val_address,
            'public_key': val_data['public_key'],
            'stake': VALIDATOR_STAKE,
            'delegated_stake': 0,
            'commission_rate': 0.1,
            'jailed': False,
            'jailed_until': 0,
            'total_blocks_proposed': 0,
            'total_blocks_missed': 0,
            'created_at': timestamp
        }
        genesis_state['total_staked'] += VALIDATOR_STAKE
        print(f"Validator-{i}: {val_address} (Staked: 100,000 UNI)")
    
    # Genesis Block (with Phase 0 contract support fields)
    genesis_block = Block(
        height=0,
        prev_hash="0" * 64,
        timestamp=timestamp,
        proposer=FOUNDER_ADDRESS,
        proposer_pubkey=founder_wallet['public_key'],
        transactions=[],
        tx_root="0" * 64,
        state_root="genesis",
        validator_set_hash="genesis",
        next_validator_set_hash="genesis",
        consensus_hash="genesis",
        app_hash="genesis",
        total_fees=0,
        block_reward=0,
        signature="genesis",
        hash="genesis",
        # Phase 0 fields (all empty/default)
        contracts_deployed=0,
        contract_calls=0,
        contract_gas_used=0,
        vm_version="none",
        protocol_version=1,
        extra_data="",
        reserved_field1=0,
        reserved_field2=0,
        reserved_field3=""
    )
    
    # Save
    storage.save_block(genesis_block)
    storage.save_state(genesis_state)
    storage.save_metadata({
        'height': 0,
        'latest_hash': 'genesis',
        'total_minted': GENESIS_SUPPLY
    })
    
    print(f"\n✅ Genesis Block Created!")
    print(f"   Height: 0")
    print(f"   Total Supply: {GENESIS_SUPPLY / 10**8:,.0f} UNI")
    print(f"   Validators: {len(validators_data)}")
    
    return True

if __name__ == "__main__":
    create_genesis()
