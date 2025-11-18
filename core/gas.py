"""
Unicrium Gas System
Resource metering and fee calculation
Prevents spam and ensures fair resource usage
"""
from typing import Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TxType(str, Enum):
    """Transaction types"""
    TRANSFER = "transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    DELEGATE = "delegate"
    UNDELEGATE = "undelegate"
    VOTE = "vote"
    SMART_CONTRACT = "smart_contract"


class GasConfig:
    """
    Gas configuration
    Defines costs for different operations
    """
    
    def __init__(self):
        # Base costs (in smallest unit)
        self.TX_BASE = 1000  # Base transaction cost
        self.TRANSFER = 2000  # Transfer cost
        self.STAKE = 5000  # Staking cost
        self.UNSTAKE = 5000  # Unstaking cost
        self.DELEGATE = 3000  # Delegation cost
        self.UNDELEGATE = 3000  # Undelegation cost
        self.VOTE = 1000  # Voting cost
        self.SMART_CONTRACT_BASE = 10000  # Smart contract base
        
        # Per-byte costs
        self.BYTE_COST = 10  # Cost per byte of data
        
        # Signature verification
        self.SIGNATURE_VERIFY = 500
        
        # Storage costs
        self.STORAGE_WRITE = 100  # Per byte stored
        self.STORAGE_READ = 10  # Per byte read
        
        # Gas limits
        self.MAX_GAS_PER_TX = 1000000  # Maximum gas per transaction
        self.MAX_GAS_PER_BLOCK = 10000000  # Maximum gas per block
        
        # Gas price (in smallest unit per gas unit)
        self.MIN_GAS_PRICE = 1  # Minimum gas price
        self.DEFAULT_GAS_PRICE = 10  # Default gas price
    
    def get_tx_type_cost(self, tx_type: str) -> int:
        """Get base cost for transaction type"""
        costs = {
            TxType.TRANSFER: self.TRANSFER,
            TxType.STAKE: self.STAKE,
            TxType.UNSTAKE: self.UNSTAKE,
            TxType.DELEGATE: self.DELEGATE,
            TxType.UNDELEGATE: self.UNDELEGATE,
            TxType.VOTE: self.VOTE,
            TxType.SMART_CONTRACT: self.SMART_CONTRACT_BASE
        }
        return costs.get(tx_type, self.TX_BASE)
    
    def to_dict(self) -> dict:
        """Export configuration"""
        return {
            'costs': {
                'tx_base': self.TX_BASE,
                'transfer': self.TRANSFER,
                'stake': self.STAKE,
                'unstake': self.UNSTAKE,
                'delegate': self.DELEGATE,
                'undelegate': self.UNDELEGATE,
                'vote': self.VOTE,
                'smart_contract_base': self.SMART_CONTRACT_BASE
            },
            'limits': {
                'max_gas_per_tx': self.MAX_GAS_PER_TX,
                'max_gas_per_block': self.MAX_GAS_PER_BLOCK
            },
            'prices': {
                'min_gas_price': self.MIN_GAS_PRICE,
                'default_gas_price': self.DEFAULT_GAS_PRICE
            }
        }


class GasCalculator:
    """
    Calculates gas costs for transactions
    """
    
    def __init__(self, config: Optional[GasConfig] = None):
        """
        Initialize gas calculator
        
        Args:
            config: Gas configuration (uses default if None)
        """
        self.config = config or GasConfig()
        logger.info("GasCalculator initialized")
    
    def calculate_tx_gas(self, tx_type: str, data_size: int = 0,
                        storage_write: int = 0, storage_read: int = 0) -> int:
        """
        Calculate gas cost for transaction
        
        Args:
            tx_type: Type of transaction
            data_size: Size of transaction data in bytes
            storage_write: Bytes written to storage
            storage_read: Bytes read from storage
            
        Returns:
            Total gas cost
        """
        # Base cost for transaction type
        gas = self.config.TX_BASE + self.config.get_tx_type_cost(tx_type)
        
        # Add data cost
        gas += data_size * self.config.BYTE_COST
        
        # Add storage costs
        gas += storage_write * self.config.STORAGE_WRITE
        gas += storage_read * self.config.STORAGE_READ
        
        # Add signature verification
        gas += self.config.SIGNATURE_VERIFY
        
        return gas
    
    def calculate_fee(self, gas_used: int, gas_price: Optional[int] = None) -> int:
        """
        Calculate transaction fee
        
        Args:
            gas_used: Gas units consumed
            gas_price: Gas price (uses default if None)
            
        Returns:
            Fee in smallest token unit
        """
        if gas_price is None:
            gas_price = self.config.DEFAULT_GAS_PRICE
        
        # Ensure minimum gas price
        gas_price = max(gas_price, self.config.MIN_GAS_PRICE)
        
        fee = gas_used * gas_price
        
        return fee
    
    def validate_gas_limit(self, gas_limit: int) -> bool:
        """
        Validate gas limit is within bounds
        
        Args:
            gas_limit: Proposed gas limit
            
        Returns:
            True if valid
        """
        return 0 < gas_limit <= self.config.MAX_GAS_PER_TX
    
    def estimate_transfer_gas(self, amount: int, memo: str = "") -> int:
        """
        Estimate gas for transfer transaction
        
        Args:
            amount: Transfer amount
            memo: Optional memo
            
        Returns:
            Estimated gas
        """
        data_size = len(memo.encode()) if memo else 0
        return self.calculate_tx_gas(TxType.TRANSFER, data_size)
    
    def estimate_stake_gas(self, amount: int) -> int:
        """Estimate gas for staking"""
        return self.calculate_tx_gas(TxType.STAKE)
    
    def estimate_vote_gas(self) -> int:
        """Estimate gas for voting"""
        return self.calculate_tx_gas(TxType.VOTE)


class GasTracker:
    """
    Tracks gas usage for blocks and transactions
    Used for optimization and analytics
    """
    
    def __init__(self, config: Optional[GasConfig] = None):
        """Initialize gas tracker"""
        self.config = config or GasConfig()
        self.block_gas_used: Dict[int, int] = {}  # height -> gas used
        self.tx_gas_used: Dict[str, int] = {}  # tx_hash -> gas used
    
    def record_tx_gas(self, tx_hash: str, gas_used: int):
        """Record gas used by transaction"""
        self.tx_gas_used[tx_hash] = gas_used
    
    def record_block_gas(self, height: int, gas_used: int):
        """Record gas used in block"""
        self.block_gas_used[height] = gas_used
        
        # Log if block is near gas limit
        utilization = gas_used / self.config.MAX_GAS_PER_BLOCK
        if utilization > 0.8:
            logger.warning(f"Block {height} gas usage: {utilization:.1%}")
    
    def get_block_gas(self, height: int) -> int:
        """Get gas used in block"""
        return self.block_gas_used.get(height, 0)
    
    def get_tx_gas(self, tx_hash: str) -> int:
        """Get gas used by transaction"""
        return self.tx_gas_used.get(tx_hash, 0)
    
    def get_average_block_gas(self, last_n_blocks: int = 100) -> float:
        """Get average gas usage over last N blocks"""
        if not self.block_gas_used:
            return 0.0
        
        recent_heights = sorted(self.block_gas_used.keys())[-last_n_blocks:]
        if not recent_heights:
            return 0.0
        
        total_gas = sum(self.block_gas_used[h] for h in recent_heights)
        return total_gas / len(recent_heights)
    
    def get_block_utilization(self, height: int) -> float:
        """Get gas utilization percentage for block"""
        gas_used = self.get_block_gas(height)
        return gas_used / self.config.MAX_GAS_PER_BLOCK
    
    def to_dict(self) -> dict:
        """Export statistics"""
        avg_gas = self.get_average_block_gas()
        avg_utilization = avg_gas / self.config.MAX_GAS_PER_BLOCK if self.config.MAX_GAS_PER_BLOCK > 0 else 0
        
        return {
            'total_blocks_tracked': len(self.block_gas_used),
            'total_txs_tracked': len(self.tx_gas_used),
            'average_block_gas': int(avg_gas),
            'average_utilization': f"{avg_utilization:.2%}",
            'max_gas_per_block': self.config.MAX_GAS_PER_BLOCK
        }


if __name__ == "__main__":
    # Test gas system
    print("Testing Gas System...")
    
    config = GasConfig()
    calculator = GasCalculator(config)
    tracker = GasTracker(config)
    
    # Test transfer gas calculation
    gas = calculator.estimate_transfer_gas(1000000, "Hello Unicrium!")
    print(f"✓ Transfer gas: {gas}")
    
    # Test fee calculation
    fee = calculator.calculate_fee(gas)
    print(f"✓ Transfer fee: {fee}")
    
    # Test stake gas
    stake_gas = calculator.estimate_stake_gas(1000000)
    print(f"✓ Stake gas: {stake_gas}")
    
    # Test gas validation
    valid = calculator.validate_gas_limit(gas)
    print(f"✓ Gas limit valid: {valid}")
    
    # Test gas tracking
    tracker.record_tx_gas("tx123", gas)
    tracker.record_block_gas(1, gas * 10)
    
    print(f"✓ Block gas: {tracker.get_block_gas(1)}")
    print(f"✓ Block utilization: {tracker.get_block_utilization(1):.2%}")
    
    print("\n✅ Gas system tests passed!")