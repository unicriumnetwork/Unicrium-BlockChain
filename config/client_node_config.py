"""
Client Node Configuration
Bu config ile yeni node'lar ana node'a bağlanabilir
"""

# Bootstrap node (ana node)
BOOTSTRAP_NODES = [
    "YOUR_SERVER_IP:26656"  # Ana node IP'nizi buraya yazın
]

# Genesis bilgileri (ana node ile AYNI)
GENESIS_TIMESTAMP = 1761931343
GENESIS_CHAIN_ID = "unicrium-mainnet-1"

# P2P ayarları
P2P_HOST = "0.0.0.0"
P2P_PORT = 26656  # Client node farklı port kullanabilir: 26657, 26658

# API ayarları
API_HOST = "0.0.0.0"
API_PORT = 5001  # Ana node 5000 kullanıyor
