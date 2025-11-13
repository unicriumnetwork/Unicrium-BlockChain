# Unicrium Network

**A Trust-First, Transparent Proof-of-Stake Blockchain with EVM Compatibility**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Network Status](https://img.shields.io/badge/network-mainnet-green.svg)](https://www.unicrium.network)
[![Audit Status](https://img.shields.io/badge/security-audited-brightgreen.svg)](https://github.com/UnicriumNetwork/audits)

---

## 🌟 Overview

Unicrium is a **trust-indexed**, transparent blockchain network built with integrity at its core:

- 🛡️ **Zero-Tolerance for Fraud**: Built-in mechanisms prevent rug pulls and scams
- 🔍 **Full Transparency**: Every transaction, block, and validator action is publicly verifiable
- ⚡ **Pure Proof-of-Stake (PoS)** consensus mechanism
- 🔗 **EVM Compatibility** for Ethereum smart contracts
- 🌐 **Decentralized P2P Network** with automatic peer discovery
- 💰 **Fair Tokenomics** with predictable halving schedule
- 🔐 **Enterprise-grade Security** with ECDSA cryptography
- 📊 **Real-time Monitoring** with built-in block explorer

**Live Network:** [https://www.unicrium.network](https://www.unicrium.network)  
**RPC Endpoint:** [https://rpc.unicrium.network](https://rpc.unicrium.network)

### 🛡️ Trust & Security First

**We are committed to building a fraud-resistant ecosystem:**

- ✅ **No Hidden Allocations**: All token minting is transparent and on-chain
- ✅ **Immutable Smart Contracts**: No upgradeable proxies that can rug pull
- ✅ **Public Validator Set**: All validators are publicly listed and monitored
- ✅ **Open Source**: 100% of our code is open for audit
- ✅ **Community Governance**: Major decisions require community consensus
- ✅ **Real-time Auditing**: Every transaction is traceable and verifiable

---

## 📋 Table of Contents

- [Features](#-features)
- [Network Statistics](#-network-statistics)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Running a Node](#-running-a-node)
- [MetaMask Setup](#-metamask-setup)
- [API Documentation](#-api-documentation)
- [Tokenomics](#-tokenomics)
- [Architecture](#-architecture)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Trust & Security
- **Fraud-Resistant Design**: Built from ground-up to prevent scams and rug pulls
- **100% Transparent**: All code, transactions, and governance decisions are public
- **Immutable Rules**: Protocol rules cannot be changed without community consensus
- **Real-time Auditing**: Every transaction is verifiable on the blockchain
- **No Hidden Backdoors**: Open source code audited by the community

### Core Blockchain
- **Pure PoS Consensus**: Energy-efficient block production with validator rotation
- **Fast Block Times**: ~5 second block intervals
- **High Throughput**: Optimized for scalability
- **Deterministic Finality**: No chain reorganizations after confirmation
- **Fair Launch**: No pre-mine, no insider allocations

### Smart Contracts
- **EVM Compatible**: Deploy Solidity contracts without modifications
- **Gas-efficient**: Optimized execution environment
- **py-evm Integration**: Battle-tested Ethereum Virtual Machine
- **Contract Verification**: Public source code verification system

### Network
- **P2P Protocol**: Libp2p-based decentralized networking
- **Automatic Discovery**: Bootstrap nodes for easy network joining
- **Multi-platform**: Linux, Windows, and macOS support
- **DDoS Protection**: Built-in rate limiting and peer reputation

### Developer Tools
- **JSON-RPC API**: Full Web3 compatibility
- **MetaMask Integration**: Seamless wallet connection
- **Block Explorer**: Real-time network monitoring
- **RESTful API**: Easy blockchain data access
- **Open Documentation**: Comprehensive guides and tutorials

---

## 📊 Network Statistics

| Metric | Value |
|--------|-------|
| **Chain ID** | 1001 (0x3e9) |
| **Block Time** | ~5 seconds |
| **Max Supply** | 100,000,000 UNM |
| **Current Era** | Era 1 (0.5 UNM/block) |
| **Consensus** | Proof of Stake |
| **Network** | Mainnet (Production) |
| **Fraud Protection** | ✅ Enabled |
| **Transparency Level** | 100% Open Source |

**Current Height:** 1,500+ blocks  
**Total Supply:** ~750 UNM minted  
**Active Validators:** 21+  
**Trust Score:** AAA (Fully Auditable)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- 4GB RAM minimum
- 10GB free disk space

### One-Command Installation

```bash
# Clone the repository
git clone https://github.com/UnicriumNetwork/unicrium-blockchain.git
cd unicrium-blockchain

# Install dependencies
pip install -r requirements.txt

# Run a full node
python3 run_node.py
```

Your node will start syncing with the network automatically! 🎉

---

## 📦 Installation

### From Source

```bash
# 1. Clone repository
git clone https://github.com/UnicriumNetwork/unicrium-blockchain.git
cd unicrium-blockchain

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python3 -c "from blockchain.blockchain import Blockchain; print('✅ Installation successful!')"
```

### Using Docker (Coming Soon)

```bash
docker pull unicrium/node:latest
docker run -d -p 5000:5000 -p 26656:26656 unicrium/node:latest
```

---

## 🖥️ Running a Node

### Full Node

Run a complete node that validates and relays blocks:

```bash
python3 run_node.py
```

Your node will:
- ✅ Connect to the P2P network
- ✅ Sync the blockchain
- ✅ Validate transactions and blocks
- ✅ Participate in consensus (if staking)

### API Server

Start the JSON-RPC API server:

```bash
cd /path/to/unicrium-blockchain
uvicorn blockchain.api_server:app --host 0.0.0.0 --port 5000
```

API will be available at `http://localhost:5000`

### Validator Node

To become a validator:

1. Stake minimum 1,000,000 UNM (10,000 UNM)
2. Run a full node with 99.9% uptime
3. Register your validator public key

```python
from blockchain.blockchain import Blockchain
from core.crypto import KeyPair

chain = Blockchain()
validator_key = KeyPair()

# Stake UNM
chain.stake(
    address=validator_key.address,
    amount=1000000 * 10**8,  # 1M UNM
    public_key=validator_key.public_key
)
```

---

## 🦊 MetaMask Setup

### Add Unicrium Network

1. Open MetaMask
2. Click **Networks** → **Add Network**
3. Enter the following details:

| Field | Value |
|-------|-------|
| **Network Name** | Unicrium Mainnet |
| **RPC URL** | `https://rpc.unicrium.network` |
| **Chain ID** | `1001` |
| **Currency Symbol** | `UNM` |
| **Block Explorer** | `https://www.unicrium.network` |

4. Click **Save** and switch to Unicrium Network

### Get Test UNM

Visit the faucet at [https://www.unicrium.network/faucet.html](https://www.unicrium.network/faucet.html)

---

## 📚 API Documentation

### JSON-RPC Endpoints

Full Web3 compatibility for MetaMask and web3.js:

```javascript
// Connect to Unicrium
const Web3 = require('web3');
const web3 = new Web3('https://rpc.unicrium.network');

// Get balance
const balance = await web3.eth.getBalance('0x...');

// Send transaction
await web3.eth.sendTransaction({
  from: '0x...',
  to: '0x...',
  value: web3.utils.toWei('1', 'ether')
});
```

### RESTful API

```bash
# Get blockchain info
curl https://rpc.unicrium.network/info

# Get latest block
curl https://rpc.unicrium.network/block/latest

# Check balance
curl https://rpc.unicrium.network/balance/0x...

# List validators
curl https://rpc.unicrium.network/validators
```

**Full API Documentation:** [API.md](./docs/API.md)

---

## 💰 Tokenomics

### UNM Token

- **Name:** Unicrium
- **Symbol:** UNM
- **Decimals:** 8
- **Max Supply:** 100,000,000 UNM (Fixed & Immutable)
- **Initial Block Reward:** 0.5 UNM
- **Transparency:** 100% on-chain, no pre-mine, no hidden allocations

### Halving Schedule

| Era | Blocks | Reward | Total Minted | Timeframe |
|-----|--------|--------|--------------|-----------|
| 1 | 0 - 210,000 | 0.5 UNM | 105,000 UNM | ~12 days |
| 2 | 210,001 - 420,000 | 0.25 UNM | 52,500 UNM | ~12 days |
| 3 | 420,001 - 630,000 | 0.125 UNM | 26,250 UNM | ~12 days |
| 4 | 630,001 - 840,000 | 0.0625 UNM | 13,125 UNM | ~12 days |
| ... | ... | ... | ... | ... |
| Final | ~400,000,000 blocks | <0.00000001 UNM | 100,000,000 UNM | ~63 years |

Halvings occur every 210,000 blocks (~12 days at 5s block time).

### Distribution Model

**100% Fair Launch - No Pre-mine, No ICO, No Insider Allocation**

- **85%** Block Rewards (Validators & Stakers)
- **10%** Community Treasury (Governed by DAO)
- **5%** Development Fund (Multi-sig controlled, transparent)

### Anti-Fraud Mechanisms

1. **Transparent Minting**: Every UNM token is minted through block rewards only
2. **No Admin Keys**: No one can mint tokens arbitrarily
3. **Immutable Supply Cap**: 100M hard cap enforced at protocol level
4. **Public Validator List**: All validators are publicly auditable
5. **Slashing Protection**: Malicious validators lose their stake
6. **On-chain Governance**: No centralized control

---

## 🏗️ Architecture

### Project Structure

```
unicrium-blockchain/
├── blockchain/          # Core blockchain logic
│   ├── blockchain.py    # Main blockchain class
│   ├── models.py        # Block, Transaction models
│   └── api_server.py    # FastAPI JSON-RPC server
├── consensus/           # PoS consensus mechanism
│   └── pos.py          # Validator selection & rewards
├── core/               # Cryptography & utilities
│   ├── crypto.py       # ECDSA key pairs
│   └── p2p.py          # Libp2p networking
├── storage/            # Data persistence
│   ├── ledger.py       # Account balances & state
│   └── store.py        # Block storage
├── evm/                # Ethereum Virtual Machine
│   └── evm_integration.py
└── static/             # Web interface
    └── index.html      # Block explorer
```

### Key Components

**Blockchain Core**
- Block validation and consensus
- Transaction pool (mempool)
- State management

**Consensus (PoS)**
- Weighted validator selection
- Stake-based block rewards
- Slashing for malicious behavior

**P2P Network**
- Peer discovery via bootstrap nodes
- Block and transaction propagation
- Network synchronization

**EVM**
- Full Ethereum smart contract support
- Solidity compatibility
- Gas metering

---

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_blockchain.py

# Run with coverage
pytest --cov=blockchain tests/
```

### Development Mode

```bash
# Enable debug logging
export UNICRIUM_DEBUG=1

# Run with auto-reload
uvicorn blockchain.api_server:app --reload --log-level debug
```

### Building from Source

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linter
flake8 blockchain/ core/ consensus/

# Format code
black blockchain/ core/ consensus/
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Keep
