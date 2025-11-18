class Mempool:
    def __init__(self):
        self.transactions = {}
        self.retry_count = {}
        self.MAX_SIZE = 100
        self.MAX_RETRIES = 3
        
    def add_transaction(self, tx):
        """Safely add transaction with validation"""
        try:
            if not hasattr(tx, 'txid'):
                return False
                
            if len(self.transactions) >= self.MAX_SIZE:
                oldest = next(iter(self.transactions))
                del self.transactions[oldest]
                if oldest in self.retry_count:
                    del self.retry_count[oldest]
                    
            tx_hash = tx.txid()
            self.transactions[tx_hash] = tx
            self.retry_count[tx_hash] = 0
            return True
        except Exception as e:
            print(f"Mempool add error: {e}")
            return False
            
    def get_transactions_for_block(self, chain, max_count=50):
        """Get only valid transactions for block creation"""
        valid_txs = []
        to_remove = []
        
        for tx_hash, tx in list(self.transactions.items()):
            if len(valid_txs) >= max_count:
                break
                
            try:
                # Validate TX
                if chain.validate_transaction(tx):
                    valid_txs.append(tx)
                else:
                    self.retry_count[tx_hash] = self.retry_count.get(tx_hash, 0) + 1
                    if self.retry_count[tx_hash] > self.MAX_RETRIES:
                        to_remove.append(tx_hash)
            except Exception:
                # Problemli TX'i direkt sil
                to_remove.append(tx_hash)
                
        # Başarısız TX'leri temizle
        for tx_hash in to_remove:
            if tx_hash in self.transactions:
                del self.transactions[tx_hash]
            if tx_hash in self.retry_count:
                del self.retry_count[tx_hash]
                
        return valid_txs
        
    def remove_transactions(self, tx_list):
        """Remove processed transactions"""
        for tx in tx_list:
            tx_hash = tx.txid()
            if tx_hash in self.transactions:
                del self.transactions[tx_hash]
            if tx_hash in self.retry_count:
                del self.retry_count[tx_hash]
                
    def clear(self):
        self.transactions.clear()
        self.retry_count.clear()
        
    def size(self):
        return len(self.transactions)
