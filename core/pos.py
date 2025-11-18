"""
Unicrium Proof-of-Stake Consensus
Enhanced with VRF and proper validator selection
"""
import hashlib
import time
import random
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class Validator:
    """Validator information"""
    address: str
    stake: int
    commission: float = 0.10
    is_active: bool = True
    total_blocks: int = 0
    last_block_time: int = 0
    
    def to_dict(self):
        return {
            'address': self.address,
            'stake': self.stake,
            'commission': self.commission,
            'is_active': self.is_active,
            'total_blocks': self.total_blocks,
            'last_block_time': self.last_block_time
        }


class ProofOfStake:
    """PoS Consensus Engine"""
    
    def __init__(self, min_stake: int = 1000 * 10**8):  # 1,000 UNM:  # 1,000 UNM
        self.min_stake = min_stake
        self.validators: Dict[str, Validator] = {}
        self.validator_rotation = []
    
    def add_validator(self, address: str, stake: int, commission: float = 0.10):
        """Add new or update existing validator"""
        if stake >= self.min_stake:
            if address in self.validators:
                # Update stake
                self.validators[address].stake = stake
            else:
                # Add new
                self.validators[address] = Validator(
                    address=address,
                    stake=stake,
                    commission=commission
                )
            self._update_rotation()
            print(f"PoS: Validator added/updated: {address[:10]}... (Stake: {stake})")
            return True
        
        # Eğer stake minimumun altındaysa ve validatörse, kaldır
        elif address in self.validators:
            return self.remove_validator(address)
            
        return False

    def remove_validator(self, address: str) -> bool:
        """Remove validator"""
        if address in self.validators:
            del self.validators[address]
            self._update_rotation()
            print(f"PoS: Validator removed: {address[:10]}...")
            return True
        return False
    
    def _update_rotation(self):
        """Update validator rotation based on stake"""
        self.validator_rotation = []
        if not self.validators:
            return

        active_validators = self.get_active_validators()
        if not active_validators:
            return

        # En düşük stake'i bul (ağırlıklandırma için)
        min_stake_unit = min(v.stake for v in active_validators)
        if min_stake_unit == 0:
            min_stake_unit = self.min_stake # Güvenlik önlemi

        for validator in active_validators:
            # Ağırlık = stake / en_düşük_stake (veya min_stake)
            weight = max(1, int(validator.stake // min_stake_unit))
            self.validator_rotation.extend([validator.address] * weight)
        
        print(f"PoS: Rotation updated. Total weight: {len(self.validator_rotation)}")
    
    def select_proposer(self, height: int, seed: str = "") -> Optional[str]:
        """Select block proposer using VRF-like mechanism"""
        if not self.validator_rotation:
            print("PoS Error: No validators in rotation!")
            # Acil durum: Validatör listesinden rastgele seç
            if self.validators:
                return random.choice(list(self.validators.keys()))
            return None
        
        # Combine height and seed for deterministic selection
        hash_input = f"{height}{seed}".encode()
        hash_output = hashlib.sha256(hash_input).hexdigest()
        index = int(hash_output, 16) % len(self.validator_rotation)
        
        return self.validator_rotation[index]
    
    def get_active_validators(self) -> List[Validator]:
        """Get all active validators"""
        return [v for v in self.validators.values() if v.is_active and v.stake >= self.min_stake]
    
    def get_validator(self, address: str) -> Optional[Validator]:
        """Get specific validator"""
        return self.validators.get(address)
    
    def record_block(self, validator_address: str):
        """Record that validator produced a block"""
        if validator_address in self.validators:
            self.validators[validator_address].total_blocks += 1
            self.validators[validator_address].last_block_time = int(time.time())