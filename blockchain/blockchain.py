"""
Unicrium Blockchain - 150 Year Mining Model
1 UNM/block with 10-year halving
Total Supply: ~79.5M UNM (Genesis: 16.4M + Mining: 63.1M)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.pos import ProofOfStake
from core.mempool import Mempool
from core.gas import GasCalculator, GasTracker
from core.slashing import SlashingManager
from core.merkle import compute_tx_root
from storage.storage import PersistentStorage
from storage.ledger import Ledger
from vm.unicrium_evm import UnicriumEVM
from blockchain.models import Block, Transaction
import time
import logging
import threading
import json

logger = logging.getLogger(__name__)


class BlockchainConfig:
    """Blockchain configuration - 150 year model with flexible feature activation"""
    # === TOKENOMICS ===
    MAX_SUPPLY = 100_000_000 * 10**8  # 100M UNM
    GENESIS_SUPPLY = 16_400_000 * 10**8  # 16.4M UNM

    # Mining (150-year model: 1 UNM/block, 10yr halving)
    INITIAL_BLOCK_REWARD = 1 * 10**8  # 1 UNM
    HALVING_INTERVAL = 31_536_000  # blocks (~10 years at 10 sec/block)

    # === STAKING ===
    MIN_VALIDATOR_STAKE = 1000 * 10**8  # 1,000 UNM
    UNBONDING_PERIOD = 1_814_400

    # === GAS SYSTEM ===
    GAS_PRICE = 1
    MIN_GAS_LIMIT = 21_000
    MAX_GAS_LIMIT = 10_000_000

    # === BLOCK LIMITS ===
    MAX_TXS_PER_BLOCK = 1000
    MAX_BLOCK_SIZE = 2_000_000
    MAX_TIMESTAMP_DRIFT = 60  # 60 seconds future tolerance
    
    # === FEATURE FLAGS (Phase 0 - Flexible Activation) ===
    FEATURES = {
        # Core features (always enabled from genesis)
        'transfers': {
            'enabled': True,
            'min_height': 0,
            'activated_at': 0,
            'can_deactivate': False,
            'description': 'Basic transfers',
        },
        'staking': {
            'enabled': True,
            'min_height': 0,
            'activated_at': 0,
            'can_deactivate': False,
            'description': 'PoS staking',
        },
        
        # Smart contracts (manual activation after min_height)
        'contracts': {
            'enabled': False,
            'min_height': 5_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'Smart contract support',
        },
        'evm': {
            'enabled': False,
            'min_height': 5_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'Ethereum Virtual Machine',
        },
        'uvm': {
            'enabled': False,
            'min_height': 10_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'Unicrium VM (native, 10x cheaper gas)',
        },
        'wasm': {
            'enabled': False,
            'min_height': 20_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'WebAssembly VM',
        },
        
        # Advanced features
        'batch_transfers': {
            'enabled': False,
            'min_height': 1_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'Batch transfer operations (gas efficient)',
        },
        'oracles': {
            'enabled': False,
            'min_height': 10_000,
            'activated_at': None,
            'can_deactivate': True,
            'description': 'Native oracle support',
        },
        'cross_chain': {
            'enabled': False,
            'min_height': 50_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'Cross-chain bridges',
        },
        'zk_proofs': {
            'enabled': False,
            'min_height': 100_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'Zero-knowledge proof support',
        },
        
        # Governance
        'governance': {
            'enabled': False,
            'min_height': 50_000,
            'activated_at': None,
            'can_deactivate': False,
            'description': 'On-chain governance (DAO)',
        },
    }
    
    # === CONTRACT CONFIGURATION ===
    MAX_CONTRACT_SIZE = 24_576           # 24KB (Ethereum limit)
    MAX_CONTRACT_STORAGE_KEYS = 2**20    # 1M keys max per contract
    MAX_CONTRACTS_PER_BLOCK = 100        # Max deployments per block
    
    # Contract gas costs
    CONTRACT_DEPLOY_BASE_GAS = 32_000
    CONTRACT_DEPLOY_PER_BYTE = 200
    CONTRACT_CALL_BASE_GAS = 21_000
    CONTRACT_STORAGE_SET_GAS = 20_000
    CONTRACT_STORAGE_RESET_GAS = 5_000
    CONTRACT_STORAGE_CLEAR_GAS = 5_000
    
    # VM-specific gas multipliers
    VM_GAS_MULTIPLIERS = {
        'evm': 1.0,        # Standard (same as Ethereum)
        'uvm': 0.1,        # 10x cheaper (register-based)
        'wasm': 0.3,       # 3x cheaper (optimized)
    }
    
    # === PROTOCOL VERSIONING ===
    PROTOCOL_VERSION = 1             # Current protocol version
    MIN_SUPPORTED_VERSION = 1        # Minimum backward compatible version


class Blockchain:
    """150-year deflationary blockchain"""

    def __init__(self, chain_id: str = "unicrium-mainnet-1"):
        self.chain_id = chain_id
        self.config = BlockchainConfig()

        # Storage
        storage_path = os.path.join(os.path.dirname(__file__), "..", "blockchain_data")
        self.storage = PersistentStorage(storage_path)

        # State
        self.ledger = Ledger()

        # Consensus & Security
        self.consensus = ProofOfStake(min_stake=self.config.MIN_VALIDATOR_STAKE)
        self.slashing = SlashingManager()

        # Transaction Management
        self.mempool = Mempool(max_size=10000, max_age_seconds=3600)

        # Event for fast mining when TX arrives
        self.mining_event = threading.Event()
        self.mempool.new_tx_event = self.mining_event

        # Gas System
        self.gas_calculator = GasCalculator()
        self.gas_tracker = GasTracker()

        # EVM (Ethereum Virtual Machine)
        self.evm = UnicriumEVM(state_db=self.ledger, chain_id=1)

        # Block storage
        self.blocks = []

        # Track total minted coins
        self.total_minted = 0

        # Auto block production
        self.auto_producing = False
        self.producer_thread = None

        self._load_state()
        logger.info(f"✅ Blockchain initialized: Height {self.get_height()}")

    def _create_genesis_block(self) -> Block:
        """Create genesis block with 16.4M UNM allocation"""
        print("\n" + "="*70)
        print("🌟 CREATING GENESIS BLOCK - UNMCRIUM MAINNET")
        print("="*70)
        print("📊 TOKENOMICS: 1 UNM/block, 10-year halving, 150-year model")
        print("💰 Max Supply: 100M UNM | Genesis: 16.4M UNM | Mineable: 83.6M UNM")
        print("="*70)

        # Genesis allocations with REAL wallet addresses
        allocations = {
            # Founder: 5M UNM
            "0xacffecb00b07a53d61c38edccd7f74de83e36bf0": 5_000_000 * 10**8,
            
            # Faucet: 1M UNM
            "0x8aa829da6b4a5be2789e3ddeff569d6248e3e503": 1_000_000 * 10**8,
            
            # Treasury: 10M UNM
            "0xe3e92fb0a0160e41be8d80bee4b6a81b422c1d4c": 10_000_000 * 10**8,
            
            # Validator 1: 100K UNM
            "0x8231d09a6766dc1d75a8261e2a64d31cf6c35a8c": 100_000 * 10**8,
            
            # Validator 2: 100K UNM
            "0xf31d79f0fb66c3767da9285ddefee3a72ee267c6": 100_000 * 10**8,
            
            # Validator 3: 100K UNM
            "0x0f9f8535e53944956b60127003e396c834b1f36d": 100_000 * 10**8,
        }

        # Create genesis accounts
        print("\n💰 GENESIS ALLOCATIONS:")
        total_allocated = 0
        for address, balance in allocations.items():
            self.ledger.get_or_create_account(address)
            self.ledger.accounts[address].balance = balance
            total_allocated += balance
            
            # Identify account type
            if address == "0xacffecb00b07a53d61c38edccd7f74de83e36bf0":
                acc_type = "FOUNDER"
            elif address == "0x8aa829da6b4a5be2789e3ddeff569d6248e3e503":
                acc_type = "FAUCET"
            elif address == "0xe3e92fb0a0160e41be8d80bee4b6a81b422c1d4c":
                acc_type = "TREASURY"
            else:
                acc_type = "VALIDATOR"
            
            print(f"   {acc_type:10s} {address[:10]}... → {balance / 10**8:>12,.0f} UNM")

        # Create genesis block
        genesis = Block(
            height=0,
            prev_hash="0" * 64,
            timestamp=int(time.time()),  # Current time
            proposer="0xacffecb00b07a53d61c38edccd7f74de83e36bf0",
            transactions=[],
            total_fees=0,
            block_reward=0
        )

        genesis.proposer_pubkey = "cdaab1107e6f2031cae2d966b500a391c65e6e88ebe365d825509397b067bedff5c87e497a729aaf79329706ba5a0d599bd2288f5020746a1df4dd3b37ca8c4f"
        genesis.tx_root = "0" * 64
        genesis.state_root = "genesis"
        genesis.validator_set_hash = "genesis"
        genesis.next_validator_set_hash = "genesis"
        genesis.consensus_hash = "genesis"
        genesis.app_hash = "genesis"
        genesis.signature = "genesis"
        genesis.hash = "genesis"

        # Set total minted
        self.total_minted = self.config.GENESIS_SUPPLY

        print(f"\n✅ Genesis Supply: {self.config.GENESIS_SUPPLY / 10**8:,.0f} UNM")
        print(f"✅ Accounts Created: {len(allocations)}")
        print(f"✅ Max Supply: {self.config.MAX_SUPPLY / 10**8:,.0f} UNM")
        print(f"✅ Mineable Supply: {(self.config.MAX_SUPPLY - self.config.GENESIS_SUPPLY) / 10**8:,.0f} UNM")
        print(f"✅ Mining Rate: 1 UNM/block (halves every 10 years)")
        print("="*70 + "\n")

        return genesis

    def _load_state(self):
        """Load blockchain state or create genesis"""
        print("📁 Loading blockchain state...")

        meta = self.storage.get_metadata()
        if not meta:
            print("   ⚠️  No metadata found - creating genesis block...")
            genesis = self._create_genesis_block()
            
            self.blocks.append(genesis)
            self.storage.save_block(genesis)
            self.storage.save_state(self.ledger.get_state())
            self.storage.save_metadata({
                'height': 0,
                'latest_hash': genesis.hash,
                'total_minted': self.total_minted
            })
            
            print("   ✅ Genesis block created and saved!")
            return

        height = int(meta.get('height', -1))
        if height == -1:
            print("   ⚠️  Invalid height - creating genesis block...")
            genesis = self._create_genesis_block()
            
            self.blocks.append(genesis)
            self.storage.save_block(genesis)
            self.storage.save_state(self.ledger.get_state())
            self.storage.save_metadata({
                'height': 0,
                'latest_hash': genesis.hash,
                'total_minted': self.total_minted
            })
            
            print("   ✅ Genesis block created and saved!")
            return

        print(f"   Last block height: {height}")

        # Load blocks
        start_height = max(0, height - 100)
        for h in range(start_height, height + 1):
            block = self.storage.load_block(h)
            if block:
                self.blocks.append(block)
        print(f"   ✅ Loaded {len(self.blocks)} blocks to memory")

        # Load ledger state
        state = self.storage.load_state()
        if state:
            self.ledger.load_state(state)
            print(f"   ✅ Loaded ledger: {len(self.ledger.accounts)} accounts")
            
            # CRITICAL: Load validators
            if 'validators' in state and state['validators']:
                print(f"   ✅ Loaded validators: {len(self.ledger.validators)} validators")
                
                # Add to consensus
                for addr, validator in self.ledger.validators.items():
                    stake = getattr(validator, 'stake', 0)
                    commission = getattr(validator, 'commission_rate', 0.1)
                    if stake >= self.config.MIN_VALIDATOR_STAKE:
                        self.consensus.add_validator(addr, stake, commission)
                print(f"   ✅ Added {len(self.consensus.validators)} validators to consensus")
            else:
                print("   ⚠️ No validators found in state")

        # Load total minted
        self.total_minted = meta.get('total_minted', self.config.GENESIS_SUPPLY)
        print(f"   💰 Total supply: {self.total_minted / 10**8:,.0f} UNM")

    def get_height(self):
        """Get current height"""
        return self.storage.get_metadata().get('height', -1)

    def get_block_reward(self, height: int) -> int:
        """Calculate block reward with 10-year halving"""
        era = height // self.config.HALVING_INTERVAL
        reward = self.config.INITIAL_BLOCK_REWARD // (2 ** era)
        if reward < 1:
            reward = 1
        if self.total_minted + reward > self.config.MAX_SUPPLY:
            remaining = self.config.MAX_SUPPLY - self.total_minted
            return max(0, remaining)
        return reward

    def get_current_era(self) -> dict:
        """Get current mining era info"""
        height = self.get_height() + 1
        era = height // self.config.HALVING_INTERVAL
        blocks_in_era = height % self.config.HALVING_INTERVAL
        blocks_until_halving = self.config.HALVING_INTERVAL - blocks_in_era
        current_reward = self.get_block_reward(height)
        next_reward = current_reward // 2 if current_reward > 1 else 1
        years_in_era = blocks_in_era / 3_153_600
        years_until_halving = blocks_until_halving / 3_153_600
        return {
            'era': era,
            'blocks_in_era': blocks_in_era,
            'blocks_until_halving': blocks_until_halving,
            'years_in_era': round(years_in_era, 2),
            'years_until_halving': round(years_until_halving, 2),
            'current_reward': current_reward,
            'next_reward': next_reward
        }

    
    def validate_transaction(self, tx) -> bool:
        """Validate transaction"""
        try:
            if not tx.verify_signature():
                return False
            expected_nonce = self.ledger.get_nonce(tx.sender)
            if tx.nonce != expected_nonce:
                return False
            total_cost = tx.amount + tx.fee
            if self.ledger.get_balance(tx.sender) < total_cost:
                return False
            return True
        except:
            return False
    
    def add_transaction(self, tx: Transaction) -> bool:
        print(f"🚨 ADD_TRANSACTION CALLED! TX: {tx.txid()[:16]}... Type: {tx.tx_type}")
        """Add transaction to mempool"""
        try:
            if not tx.verify_signature():
                logger.warning(f"Invalid signature: {tx.txid()[:16]}...")
                return False
            expected_nonce = self.ledger.get_nonce(tx.sender)
            if tx.nonce != expected_nonce:
                logger.warning(f"Nonce mismatch: expected={expected_nonce}, got={tx.nonce}")
                return False
            required_gas = self.gas_calculator.calculate_tx_gas(tx.tx_type, data_size=len(json.dumps(tx.data).encode()))
            if tx.gas_limit < required_gas:
                logger.warning(f"Gas limit too low: {tx.gas_limit} < {required_gas}")
                return False
            gas_fee = self.gas_calculator.calculate_fee(required_gas)
            total_cost = tx.amount + tx.fee + gas_fee
            if not self.ledger.has_sufficient_balance(tx.sender, total_cost):
                logger.warning(f"Insufficient balance: {tx.sender[:10]}...")
                return False
            result = self.mempool.add(tx)
            logger.info(f"Mempool add result: {result}, mempool size now: {self.mempool.size()}")
            return result
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            return False

    def create_block(self, proposer):
        """Create block with all required parameters"""
        try:
            from blockchain.models import Block
            import time
            
            # Get transactions from mempool
            transactions = []
            if hasattr(self.mempool, 'transactions'):
                for tx_hash, tx in list(self.mempool.transactions.items())[:50]:
                    try:
                        if self.validate_transaction(tx):
                            transactions.append(tx)
                    except:
                        continue
            
            # Calculate tx_root
            if transactions:
                tx_hashes = [tx.txid() for tx in transactions]
                tx_root = self.calculate_merkle_root(tx_hashes) if hasattr(self, 'calculate_merkle_root') else "0" * 64
            else:
                tx_root = "0" * 64
            
            # Get previous block hash
            prev_hash = self.get_latest_block().hash if self.get_height() >= 0 else "0" * 64
            
            # Calculate fees
            total_fees = sum(tx.fee for tx in transactions)
            
            # Get block reward
            era_info = self.get_current_era()
            block_reward = era_info['current_reward']
            
            # Create block with ALL required parameters
            block = Block(
                height=self.get_height() + 1,
                prev_hash=prev_hash,
                timestamp=int(time.time()),
                proposer=proposer,
                proposer_pubkey="",  # Will be set by proposer
                transactions=transactions,
                tx_root=tx_root,
                state_root="",  # Will be calculated
                validator_set_hash="",
                next_validator_set_hash="",
                consensus_hash="",
                app_hash="",
                signature="",  # Will be signed
                hash="",  # Will be calculated
                total_fees=total_fees,
                block_reward=block_reward,
                contracts_deployed=0,
                contract_calls=0,
                contract_gas_used=0,
                vm_version="evm",
                protocol_version=1,
                extra_data={},
                reserved_field1=None,
                reserved_field2=None,
                reserved_field3=None
            )
            
            # Process transactions
            for tx in transactions:
                try:
                    self.process_transaction(tx, is_mining=True)
                    if tx.tx_type == 'contract_deploy':
                        block.contracts_deployed += 1
                    elif tx.tx_type == 'contract_call':
                        block.contract_calls += 1
                except Exception as e:
                    print(f"TX processing error: {e}")
            
            # Remove from mempool
            for tx in transactions:
                tx_hash = tx.txid()
                if tx_hash in self.mempool.transactions:
                    del self.mempool.transactions[tx_hash]
            
            return block
            
        except Exception as e:
            print(f"Block creation error: {e}")
            import traceback
            traceback.print_exc()
            # Return empty block with all parameters
            from blockchain.models import Block
            import time
            return Block(
                height=self.get_height() + 1,
                prev_hash=self.get_latest_block().hash if self.get_height() >= 0 else "0" * 64,
                timestamp=int(time.time()),
                proposer=proposer,
                proposer_pubkey="",
                transactions=[],
                tx_root="0" * 64,
                state_root="",
                validator_set_hash="",
                next_validator_set_hash="",
                consensus_hash="",
                app_hash="",
                signature="",
                hash="",
                total_fees=0,
                block_reward=self.get_current_era()['current_reward'],
                contracts_deployed=0,
                contract_calls=0,
                contract_gas_used=0,
                vm_version="evm",
                protocol_version=1,
                extra_data={},
                reserved_field1=None,
                reserved_field2=None,
                reserved_field3=None
            )


    def _validate_block(self, block: Block) -> bool:
        """Validate block"""
        expected_height = self.get_height() + 1
        if block.height != expected_height:
            return False
        prev_block = self.storage.load_block(block.height - 1)
        expected_prev_hash = prev_block.hash if prev_block else "0" * 64
        if block.prev_hash != expected_prev_hash:
            return False
        return True

    def stake(self, address: str, amount: int) -> bool:
        """Stake tokens"""
        try:
            account = self.ledger.accounts[address]
            if account.balance < amount:
                return False
            account.balance -= amount
            account.staked += amount
            if account.staked >= self.config.MIN_VALIDATOR_STAKE:
                self.consensus.add_validator(address, account.staked)
            self.storage.save_state(self.ledger.get_state())
            return True
        except:
            return False

    def unstake(self, address: str, amount: int) -> bool:
        """Unstake tokens"""
        try:
            account = self.ledger.accounts[address]
            if account.staked < amount:
                return False
            account.staked -= amount
            account.balance += amount
            if account.staked < self.config.MIN_VALIDATOR_STAKE:
                self.consensus.remove_validator(address)
            self.storage.save_state(self.ledger.get_state())
            return True
        except:
            return False

    def get_staking_info(self, address: str) -> dict:
        """Get staking info"""
        account = self.ledger.accounts[address]
        return {
            'address': address,
            'balance': account.balance,
            'staked': account.staked,
            'total': account.balance + account.staked,
            'is_validator': address in self.consensus.validators,
            'min_stake': self.config.MIN_VALIDATOR_STAKE,
            'rewards': 0
        }

    def get_balance(self, address: str) -> int:
        """Get balance"""
        return self.ledger.get_balance(address)

    def get_latest_block(self):
        """Get latest block"""
        return self.blocks[-1] if self.blocks else None
    
    def calculate_merkle_root(self, tx_hashes):
        """Calculate merkle root from transaction hashes"""
        if not tx_hashes:
            return "0" * 64
        
        import hashlib
        
        def hash_pair(a, b):
            combined = a + b
            return hashlib.sha256(combined.encode()).hexdigest()
        
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])
            
            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                new_hashes.append(hash_pair(tx_hashes[i], tx_hashes[i+1]))
            tx_hashes = new_hashes
        
        return tx_hashes[0]
    
    
    def add_block(self, block):
        """Add block to blockchain"""
        try:
            # Validate block
            if not self._validate_block(block):
                return False
            
            # Process transactions
            for tx in block.transactions:
                try:
                    if hasattr(tx, 'tx_type') and tx.tx_type == 'contract_deploy':
                        # Contract deployment
                        if hasattr(tx, 'contract_bytecode') and tx.contract_bytecode:
                            success, address, gas_used, error = self.evm.deploy_contract(
                                deployer=tx.sender,
                                bytecode=tx.contract_bytecode,
                                constructor_args=getattr(tx, 'contract_input', b''),
                                gas_limit=tx.gas_limit
                            )
                            if success:
                                print(f"✅ Contract deployed at: {address}")
                    
                    # Update ledger
                    self.ledger.increment_nonce(tx.sender)
                    if tx.fee > 0:
                        self.ledger.deduct_balance(tx.sender, tx.fee)
                        
                except Exception as e:
                    print(f"TX processing error: {e}")
            
            # Add mining reward
            if block.block_reward > 0:
                self.ledger.get_or_create_account(block.proposer)
                self.ledger.accounts[block.proposer].balance += block.block_reward
                self.total_minted += block.block_reward
            
            # Save block
            self.blocks.append(block)
            if len(self.blocks) > 101:
                self.blocks.pop(0)
            
            # Save to storage
            self.storage.save_block(block)
            self.storage.save_state(self.ledger.get_state())
            self.storage.save_metadata({
                'height': block.height,
                'latest_hash': block.hash,
                'total_minted': self.total_minted
            })
            
            # Remove transactions from mempool
            for tx in block.transactions:
                tx_hash = tx.txid()
                if hasattr(self.mempool, 'transactions') and tx_hash in self.mempool.transactions:
                    del self.mempool.transactions[tx_hash]
            
            print(f"✅ Block #{block.height} added")
            return True
            
        except Exception as e:
            print(f"❌ add_block error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_auto_producer(self, interval: int = 5):
        """Start automatic block production with smart strategy"""
        def produce_blocks():
            print(f"🔨 Auto block producer started")
            print("📋 Mining Strategy:")
            print(f"   • Transactions available → Block every {interval}s")
            print(f"   • No transactions → Empty block every 900s (15 min)")
            print("✅ Validators will rotate based on stake weight")
            
            while self.auto_producing:
                try:
                    # Check mempool size BEFORE creating block
                    pending_txs = self.mempool.size()
                    
                    # Select validator based on stake (PoS)
                    proposer = self.consensus.select_proposer(self.get_height() + 1)
                    
                    if not proposer:
                        # Fallback to first account
                        if self.ledger.accounts:
                            proposer = list(self.ledger.accounts.keys())[0]
                        else:
                            print("⚠️  No proposer available")
                            time.sleep(interval)
                            continue
                    
                    # Create and add block
                    block = self.create_block(proposer)
                    
                    if self.add_block(block):
                        tx_count = len(block.transactions)
                        reward = block.block_reward / 10**8
                        
                        if tx_count > 0:
                            print(f"⛏️  Block #{block.height} | Proposer: {proposer[:10]}... | TXs: {tx_count} | Reward: {reward} UNM")
                        else:
                            print(f"⛏️  Block #{block.height} | EMPTY | Reward: {reward} UNM")
                    else:
                        print(f"❌ Block #{block.height} validation failed")
                    
                    # Dynamic interval: fast if TXs, slow if empty
                    if pending_txs > 0:
                        # Wait for interval or new TX event
                        self.mining_event.wait(timeout=interval)
                        self.mining_event.clear()
                    else:
                        print(f"💤 No transactions. Next empty block in 15 minutes (or when TX arrives)...")
                        # Wait for 15 min or new TX event
                        self.mining_event.wait(timeout=900)
                        self.mining_event.clear()
                    
                except Exception as e:
                    print(f"❌ Block production error: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(interval)
        
        self.auto_producing = True
        self.producer_thread = threading.Thread(target=produce_blocks, daemon=True)
        self.producer_thread.start()
        print("✅ Auto block producer thread started")
    
    def stop_auto_producer(self):
        """Stop automatic block production"""
        if self.auto_producing:
            self.auto_producing = False
            if self.producer_thread:
                self.producer_thread.join(timeout=2)
            print("⛔ Auto block producer stopped")


    # ===== EVM CONTRACT PROCESSING =====
    
    def _process_contract_deploy(self, tx: Transaction, ledger) -> bool:
        """Process contract deployment transaction"""
        logger.info(f"📜 Processing contract deploy from {tx.sender}")
        
        # Check bytecode exists
        if not tx.contract_bytecode:
            logger.error("No bytecode provided")
            return False
        
        # Deploy contract
        success, address, gas_used, error = self.evm.deploy_contract(
            deployer=tx.sender,
            bytecode=tx.contract_bytecode,
            constructor_args=tx.contract_input or b'',
            value=tx.contract_value,
            gas_limit=tx.gas_limit
        )
        
        if not success:
            logger.error(f"Deploy failed: {error}")
            return False
        
        # Calculate gas fee
        gas_fee = gas_used * tx.gas_price
        
        # Charge gas fee (burn it)
        burn_address = "0x0000000000000000000000000000000000000000"
        if not ledger.transfer(tx.sender, burn_address, gas_fee):
            logger.error(f"Insufficient balance for gas: {gas_fee}")
            return False
        
        
        logger.info(f"✅ Contract deployed at {address}, gas: {gas_used:,}")
        return True
    
    def _process_contract_call(self, tx: Transaction, ledger) -> bool:
        """Process contract call transaction"""
        logger.info(f"📞 Processing contract call from {tx.sender}")
        
        # Check contract address
        if not tx.contract_address:
            logger.error("No contract address provided")
            return False
        
        # Check contract exists
        if not self.evm.contract_exists(tx.contract_address):
            logger.error(f"Contract {tx.contract_address} not found")
            return False
        
        # Call contract
        success, return_data, gas_used, error = self.evm.call_contract(
            caller=tx.sender,
            contract_address=tx.contract_address,
            function_data=tx.contract_input or b'',
            value=tx.contract_value,
            gas_limit=tx.gas_limit
        )
        
        if not success:
            logger.error(f"Contract call failed: {error}")
            return False
        
        # Calculate gas fee
        gas_fee = gas_used * tx.gas_price
        
        # Charge gas fee
        burn_address = "0x0000000000000000000000000000000000000000"
        if not ledger.transfer(tx.sender, burn_address, gas_fee):
            logger.error(f"Insufficient balance for gas: {gas_fee}")
            return False
        
        # Increment nonce (CRITICAL FIX!)
        ledger.increment_nonce(tx.sender)
        
        logger.info(f"✅ Contract call successful, gas: {gas_used:,}")
        return True
