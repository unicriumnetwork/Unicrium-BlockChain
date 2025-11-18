"""
Unicrium Finality Manager
BFT-style finality with validator voting
"""
from typing import Dict, Set, Optional
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class FinalityVote:
    """Vote for block finality"""
    validator: str
    height: int
    block_hash: str
    timestamp: int
    signature: str = ""


class FinalityManager:
    """
    Manages block finality through validator voting
    Implements BFT-style finality
    """
    
    def __init__(self, finality_depth: int = 10, supermajority: float = 0.67):
        """
        Initialize finality manager
        
        Args:
            finality_depth: Number of blocks before finality
            supermajority: Fraction of stake needed for finality (default 67%)
        """
        self.finality_depth = finality_depth
        self.supermajority_threshold = supermajority
        
        # Votes storage: height -> validator -> vote
        self.votes: Dict[int, Dict[str, FinalityVote]] = {}
        
        # Finalized blocks: height -> block_hash
        self.finalized: Dict[int, str] = {}
        
        logger.info(f"FinalityManager initialized (depth={finality_depth}, threshold={supermajority})")
    
    def add_vote(self, vote: FinalityVote) -> bool:
        """
        Add validator vote for a block
        
        Args:
            vote: FinalityVote object
            
        Returns:
            True if vote was added
        """
        height = vote.height
        
        # Initialize height if not exists
        if height not in self.votes:
            self.votes[height] = {}
        
        # Check if already voted
        if vote.validator in self.votes[height]:
            logger.debug(f"Validator {vote.validator[:8]} already voted for height {height}")
            return False
        
        # Add vote
        self.votes[height][vote.validator] = vote
        logger.debug(f"Added vote from {vote.validator[:8]} for height {height}")
        
        return True
    
    def check_finality(self, height: int, block_hash: str, 
                      validator_stakes: Dict[str, int]) -> bool:
        """
        Check if block has reached finality
        
        Args:
            height: Block height
            block_hash: Block hash
            validator_stakes: Dict of validator -> stake amount
            
        Returns:
            True if block is finalized
        """
        # Already finalized?
        if height in self.finalized:
            return self.finalized[height] == block_hash
        
        # Not enough votes yet?
        if height not in self.votes:
            return False
        
        # Calculate voting power
        total_stake = sum(validator_stakes.values())
        if total_stake == 0:
            return False
        
        voted_stake = 0
        for validator, vote in self.votes[height].items():
            if vote.block_hash == block_hash and validator in validator_stakes:
                voted_stake += validator_stakes[validator]
        
        # Check if supermajority reached
        voting_power = voted_stake / total_stake
        
        if voting_power >= self.supermajority_threshold:
            self.finalized[height] = block_hash
            logger.info(f"✅ Block #{height} finalized with {voting_power:.1%} voting power")
            return True
        
        return False
    
    def is_finalized(self, height: int, block_hash: str) -> bool:
        """Check if specific block is finalized"""
        return self.finalized.get(height) == block_hash
    
    def get_last_finalized_height(self) -> int:
        """Get height of last finalized block"""
        if not self.finalized:
            return -1
        return max(self.finalized.keys())
    
    def cleanup_old_votes(self, current_height: int):
        """Remove votes for old blocks to save memory"""
        cutoff_height = current_height - self.finality_depth * 2
        
        old_heights = [h for h in self.votes.keys() if h < cutoff_height]
        for height in old_heights:
            del self.votes[height]
        
        if old_heights:
            logger.debug(f"Cleaned up votes for {len(old_heights)} old blocks")
    
    def get_vote_status(self, height: int, validator_stakes: Dict[str, int]) -> dict:
        """Get voting status for a height"""
        if height not in self.votes:
            return {
                'height': height,
                'votes': 0,
                'validators': 0,
                'voting_power': 0.0,
                'finalized': False
            }
        
        total_stake = sum(validator_stakes.values())
        voted_stake = sum(
            validator_stakes.get(val, 0) 
            for val in self.votes[height].keys()
        )
        
        voting_power = voted_stake / total_stake if total_stake > 0 else 0
        
        return {
            'height': height,
            'votes': len(self.votes[height]),
            'validators': len(validator_stakes),
            'voting_power': voting_power,
            'finalized': height in self.finalized
        }


if __name__ == "__main__":
    # Test finality manager
    print("=== Finality Manager Test ===\n")
    
    finality = FinalityManager(finality_depth=10, supermajority=0.67)
    
    # Mock validators
    validators = {
        "val1": 100,
        "val2": 100,
        "val3": 100,
        "val4": 50
    }
    
    # Create votes
    block_hash = "abc123"
    votes = [
        FinalityVote("val1", 1, block_hash, int(time.time())),
        FinalityVote("val2", 1, block_hash, int(time.time())),
        FinalityVote("val3", 1, block_hash, int(time.time())),
    ]
    
    # Add votes
    for vote in votes:
        finality.add_vote(vote)
    
    # Check finality
    is_final = finality.check_finality(1, block_hash, validators)
    print(f"Block finalized: {is_final}")
    
    # Get status
    status = finality.get_vote_status(1, validators)
    print(f"Vote status: {status}")
    
    print("\n✅ Finality manager tests passed!")
