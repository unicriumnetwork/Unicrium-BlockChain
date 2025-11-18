"""
Unicrium Production Configuration
"""
import json
import os

# Cüzdan dosyalarından adresleri okuyoruz
def load_wallet_address(wallet_file):
    try:
        path = os.path.join(os.path.dirname(__file__), wallet_file)
        with open(path, "r") as f:
            return json.load(f)["address"]
    except Exception as e:
        print(f"Warning: Could not load wallet {wallet_file}. {e}")
        return f"0x{wallet_file.split('_')[0]}_default_address_{'0'*9}"

# Network
CHAIN_ID = "unicrium-mainnet-1"
NETWORK_NAME = "Unicrium Network"

# Consensus
BLOCK_TIME = 6  # seconds
MIN_STAKE = 1000 * 10**8  # 1,000 UNM
VALIDATOR_COMMISSION = 0.10  # 10%

# Finality
FINALITY_DEPTH = 10
SUPERMAJORITY_THRESHOLD = 0.67  # 67%

# Slashing
SLASHING_FRACTION = 0.05  # 5%
MAX_MISSED_BLOCKS = 100

# Gas
GAS_PRICE = 1000  # per unit
MAX_GAS = 10000000

# Token
TOKEN_SYMBOL = "UNM"
TOKEN_DECIMALS = 8
TOTAL_SUPPLY = 100_000_000 * 10**8

# Genesis Allocation
# Adresleri cüzdan dosyalarından dinamik olarak yüklüyoruz
FAUCET_ADDRESS = load_wallet_address("faucet_wallet.json")
FAUCET_ALLOCATION = 1_000_000 * 10**8

FOUNDER_ADDRESS = load_wallet_address("genesis_wallet.json")
FOUNDER_ALLOCATION = 10_000_000 * 10**8

TREASURY_ADDRESS = "0x" + "treasury" + "0" * (40 - len("treasury"))
TREASURY_ALLOCATION = 89_000_000 * 10**8

# API
API_HOST = "0.0.0.0"
API_PORT = 5000

# Faucet
FAUCET_PORT = 5001
# Faucet yapılandırmasını config'den değil, faucet_wallet.json'dan almalı
# FAUCET_AMOUNT = 1000 * 10**8 (faucet.py'da zaten yüklendi)
# FAUCET_COOLDOWN = 86400  (faucet.py'da zaten yüklendi)

# Wallet
WALLET_BACKEND_PORT = 5555

print(f"Config Loaded: Founder Address = {FOUNDER_ADDRESS}")
print(f"Config Loaded: Faucet Address  = {FAUCET_ADDRESS}")