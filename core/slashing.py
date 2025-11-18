"""
Unicrium Slashing System
Detects and penalizes malicious validator behavior
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """Evidence of validator misbehavior"""
    validator: str
    evidence_type: str
    block_height: int
    timestamp: int
    data: dict
    
    def __hash__(self):
        return hash((self.validator, self.evidence_type, self.block_height))


@dataclass
class SlashingEvent:
    """Record of a slashing event"""
    validator: str
    reason: str
    amount_slashed: int
    height: int
    timestamp: int
    evidence: Evidence


class SlashingDetector:
    """Detects validator misbehavior"""
    
    def __init__(self):
        self.seen_votes: Dict[int, Dict[str, Set[str]]] = {}
        self.validator_last_seen: Dict[str, int] = {}
        self.evidence_pool: List[Evidence] = []
        logger.info("SlashingDetector initialized")
    
    def detect_double_sign(self, block_height: int, validator: str, 
                          block_hash: str) -> Optional[Evidence]:
        """Detect double signing"""
        if block_height not in self.seen_votes:
            self.seen_votes[block_height] = {}
        
        if validator not in self.seen_votes[block_height]:
            self.seen_votes[block_height][validator] = set()
        
        previous_votes = self.seen_votes[block_height][validator]
        
        if previous_votes and block_hash not in previous_votes:
            logger.warning(f"🚨 DOUBLE SIGN: {validator[:8]}")
            
            evidence = Evidence(
                validator=validator,
                evidence_type="double_sign",
                block_height=block_height,
                timestamp=int(time.time()),
                data={'block_hashes': list(previous_votes) + [block_hash]}
            )
            
            self.evidence_pool.append(evidence)
            return evidence
        
        self.seen_votes[block_height][validator].add(block_hash)
        return None


class SlashingExecutor:
    """Executes slashing penalties"""
    
    def __init__(self, slashing_fraction: float = 0.05):
        self.slashing_fraction = slashing_fraction
        self.slashing_history: List[SlashingEvent] = []
        self.slashed_validators: Set[str] = set()
    
    def slash_validator(self, validator: str, stake: int, 
                       evidence: Evidence) -> int:
        """Slash validator stake"""
        slash_amount = int(stake * self.slashing_fraction)
        
        event = SlashingEvent(
            validator=validator,
            reason=evidence.evidence_type,
            amount_slashed=slash_amount,
            height=evidence.block_height,
            timestamp=int(time.time()),
            evidence=evidence
        )
        
        self.slashing_history.append(event)
        self.slashed_validators.add(validator)
        
        logger.warning(f"⚔️ SLASHED: {validator[:8]} amount={slash_amount}")
        
        return slash_amount


class SlashingManager:
    """Manages complete slashing system"""
    
    def __init__(self, slashing_fraction: float = 0.05):
        self.detector = SlashingDetector()
        self.executor = SlashingExecutor(slashing_fraction)
    
    def process_block(self, block_height: int, proposer: str,
                     block_hash: str, validators: Dict[str, int]) -> List[SlashingEvent]:
        """Process block for slashing"""
        events = []
        
        double_sign = self.detector.detect_double_sign(block_height, proposer, block_hash)
        if double_sign:
            stake = validators.get(proposer, 0)
            self.executor.slash_validator(proposer, stake, double_sign)
            events.append(self.executor.slashing_history[-1])
        
        return events