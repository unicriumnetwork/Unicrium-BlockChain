"""
Production-Grade Persistent Storage
Using RocksDict (RocksDB wrapper)
"""
import json
import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List
from rocksdict import Rdict, Options, AccessType

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from blockchain.models import Block, Transaction
# storage.ledger'a bağımlılık kaldırıldı (Account ve Ledger artık blockchain.models veya storage.ledger'da değil)

logger = logging.getLogger(__name__)


class PersistentStorage:
    """
    Production-grade persistent storage with RocksDB
    Handles blocks, state, and indexes
    """
    
    def __init__(self, data_dir: str = "./data/blockchain"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Database options
        opts = Options(raw_mode=True)
        opts.create_if_missing(True)
        
        # Open databases
        db_path = str(self.data_dir)
        # DB'leri aynı dizine (farklı prefix'lerle) değil, alt dizinlere açıyoruz
        self.block_db = Rdict(os.path.join(db_path, "blocks"), options=opts)
        self.state_db = Rdict(os.path.join(db_path, "state"), options=opts)
        self.index_db = Rdict(os.path.join(db_path, "indexes"), options=opts)
        
        logger.info(f"Storage initialized: {self.data_dir}")
    
    # Block operations
    def save_block(self, block: Block) -> None:
        """Save block to storage"""
        try:
            key = f"block:{block.height}".encode()
            value = json.dumps(block.to_dict()).encode()
            self.block_db[key] = value
            
            # Index by hash
            hash_key = f"hash:{block.hash}".encode()
            self.index_db[hash_key] = str(block.height).encode()
            
            logger.debug(f"Saved block {block.height}")
        except Exception as e:
            logger.error(f"Failed to save block {block.height}: {e}")
            raise
    
    def load_block(self, height: int) -> Optional[Block]:
        """Load block by height"""
        try:
            key = f"block:{height}".encode()
            value = self.block_db.get(key)
            
            if value:
                data = json.loads(value.decode())
                return Block.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Failed to load block {height}: {e}")
            return None
    
    def load_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Load block by hash"""
        try:
            hash_key = f"hash:{block_hash}".encode()
            height_bytes = self.index_db.get(hash_key)
            
            if height_bytes:
                height = int(height_bytes.decode())
                return self.load_block(height)
            return None
        except Exception as e:
            logger.error(f"Failed to load block by hash {block_hash}: {e}")
            return None
    
    def get_latest_block_height(self) -> int:
        """Get latest block height"""
        meta = self.get_metadata()
        return meta.get('height', -1)
    
    def load_blocks_range(self, start: int, end: int) -> List[Block]:
        """Load blocks in range"""
        blocks = []
        for height in range(start, end + 1):
            block = self.load_block(height)
            if block:
                blocks.append(block)
        return blocks
    
    # State operations
    def save_state(self, ledger_snapshot: dict) -> None:
        """Save ledger state snapshot"""
        try:
            key = b"state:current"
            value = json.dumps(ledger_snapshot).encode()
            self.state_db[key] = value
            logger.debug("Saved state")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise
    
    def load_state(self) -> Optional[dict]:
        """Load current ledger state snapshot"""
        try:
            print("🔍 PersistentStorage.load_state: Checking for data...")
            
            # Sadece 'state:current' anahtarını oku
            value = self.state_db.get(b"state:current")
            
            if value:
                print(f"✅ Found b'state:current' key: {len(value)} bytes")
                data = json.loads(value.decode())
                print(f"   Accounts in data: {len(data.get('accounts', {}))}")
                return data
            
            print("❌ No current state data found (key: b'state:current')!")
            return None
        except Exception as e:
            print(f"💥 Exception in load_state: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to load state: {e}")
            return None

    # Metadata operations
    def save_metadata(self, metadata: dict) -> None:
        """Save blockchain metadata (blocks DB'sine kaydediyoruz)"""
        try:
            key = b"meta:blockchain"
            value = json.dumps(metadata).encode()
            self.block_db[key] = value # state_db yerine block_db
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise
    
    def get_metadata(self) -> dict:
        """Get blockchain metadata (blocks DB'sinden okuyoruz)"""
        try:
            key = b"meta:blockchain"
            value = self.block_db.get(key)
            
            if value:
                return json.loads(value.decode())
            return {}
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return {}
    
    # Checkpoint operations
    def create_checkpoint(self, name: str, height: int) -> None:
        """Create state checkpoint"""
        try:
            # Checkpoint'i state_db'ye kaydediyoruz
            checkpoint_key = f"checkpoint:{name}".encode()
            checkpoint_data = {
                'name': name,
                'height': height,
                'state_key': 'state:current' # Hangi state'in kopyası olduğu
            }
            self.state_db[checkpoint_key] = json.dumps(checkpoint_data).encode()
            logger.info(f"Created checkpoint '{name}' at height {height}")
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
    
    def close(self) -> None:
        """Close all database connections"""
        try:
            self.block_db.close()
            self.state_db.close()
            self.index_db.close()
            logger.info("Storage closed")
        except Exception as e:
            logger.error(f"Error closing storage: {e}")


if __name__ == "__main__":
    # Test storage
    import tempfile
    
    # Geçici bir dizin kullan
    test_dir = tempfile.mkdtemp()
    print(f"Using test directory: {test_dir}")
    storage = PersistentStorage(test_dir)
    
    # Create test block (Adım 3'teki models.Block)
    genesis = Block(
        height=0,
        prev_hash="0"*64,
        timestamp=0,
        proposer="GENESIS",
        transactions=[],
        tx_root="test_root",
        state_root="test_root",
        validator_set_hash="test_val",
        next_validator_set_hash="test_val"
    )
    genesis.hash = genesis.compute_hash()
    
    # Save and load
    storage.save_block(genesis)
    loaded = storage.load_block(0)
    
    print(f"Saved: {genesis.height}")
    print(f"Loaded: {loaded.height if loaded else 'None'}")
    print(f"Match: {genesis.height == loaded.height if loaded else False}")
    
    # Test state
    test_state = {"accounts": {"0x123": {"balance": 100, "nonce": 0, "staked": 0}}}
    storage.save_state(test_state)
    loaded_state = storage.load_state()
    print(f"State saved.")
    print(f"State loaded: {loaded_state.get('accounts', {}).get('0x123', {})}")
    
    storage.close()
    
    # Clean up (isteğe bağlı)
    # import shutil
    # shutil.rmtree(test_dir)
    # print(f"Cleaned up test directory: {test_dir}")