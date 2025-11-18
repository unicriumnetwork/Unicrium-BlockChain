import importlib
import sys
if "blockchain.blockchain" in sys.modules: importlib.reload(sys.modules["blockchain.blockchain"])
"""
Unicrium API Server - Production Ready with P2P and MetaMask Support
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import traceback
import sys
import os
import threading
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from blockchain.blockchain import Blockchain
from blockchain.models import Transaction
from core.p2p import P2PNode

# Create FastAPI app
app = FastAPI(title="Unicrium API", version="2.0.0")

# CORS for MetaMask
#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=["*"],
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
#)

print("🚀 Starting Unicrium API Server...")

# Create blockchain instance
chain = Blockchain()

# Load validators if empty
if not chain.ledger.validators:
    state = chain.storage.load_state()
    if state and 'validators' in state:
        from storage.ledger import Validator
        for addr, val_data in state['validators'].items():
            chain.ledger.validators[addr] = Validator(
                address=val_data['address'],
                public_key=val_data['public_key'],
                stake=val_data['stake'],
                delegated_stake=val_data.get('delegated_stake', 0),
                commission_rate=val_data.get('commission_rate', 0.1),
                jailed=val_data.get('jailed', False),
                jailed_until=val_data.get('jailed_until', 0)
            )
        print(f"✅ Loaded {len(chain.ledger.validators)} validators")


print("✅ Blockchain loaded")
print(f"📊 Height: {chain.get_height()}")
print(f"💰 Supply: {chain.total_minted / 10**8:,.0f} UNM")

# Initialize P2P (but don't start yet - causes issues with uvicorn)
p2p_node = None
try:
    p2p_node = P2PNode(host="0.0.0.0", port=26656, blockchain=chain)
    print("✅ P2P Node initialized")
    print(f"📌 Node ID: {p2p_node.node_id}")
except Exception as e:
    print(f"⚠️  P2P initialization failed: {e}")

# Start auto block production (only if genesis exists)
if chain.get_height() >= 0:
    print("=" * 60)
    print("🔨 Starting Auto Block Production (Real PoS)")
    print("=" * 60)
    chain.start_auto_producer(interval=5)
    print("=" * 60)
else:
    print("=" * 60)
    print("⚠️  No genesis block - auto mining disabled")
    print("📥 This node will sync from network")
    print("=" * 60)

# Start P2P Network
if p2p_node:
    def run_p2p():
        """Run P2P in background thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print("🌐 Starting P2P network...")
            loop.run_until_complete(p2p_node.start())
        except Exception as e:
            print(f"⚠️  P2P error: {e}")
            import traceback
            traceback.print_exc()
    
    p2p_thread = threading.Thread(target=run_p2p, daemon=True)
    p2p_thread.start()
    print("✅ P2P network thread started")
    print("=" * 60)

# ==================== ENDPOINTS ====================


# Serve static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass  # Static directory might not exist

@app.get("/network-dashboard")
def network_dashboard():
    """Network dashboard page"""
    return FileResponse("static/network.html")

@app.get("/")
def root():
    return {"message": "Unicrium Blockchain API", "version": "2.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "node": "unicrium-mainnet", "version": "2.0.0"}

@app.get("/info")
def chain_info():
    try:
        total_supply = chain.total_minted
        max_supply = chain.config.MAX_SUPPLY
        active_validators = [v for v in chain.consensus.validators.values() if v.is_active]
        total_staked = chain.ledger.total_staked()

        return {
            "chain_id": chain.chain_id,
            "height": chain.get_height(),
            "total_supply": total_supply,
            "total_supply_formatted": f"{total_supply / 10**8:,.0f} UNM",
            "max_supply": max_supply,
            "max_supply_formatted": f"{max_supply / 10**8:,.0f} UNM",
            "supply_percentage": f"{(total_supply / max_supply * 100):.4f}%",
            "total_staked": total_staked,
            "total_staked_formatted": f"{total_staked / 10**8:,.0f} UNM",
            "staking_ratio": f"{chain.ledger.staking_ratio():.2%}",
            "validators": {"active": len(active_validators), "total": len(chain.consensus.validators)},
            "mempool_size": chain.mempool.size()
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mining_info")
def get_mining_info():
    try:
        height = chain.get_height()
        era_info = chain.get_current_era()

        return {
            "current_height": height,
            "pending_transactions": chain.mempool.size(),
            "block_reward": era_info['current_reward'],
            "block_reward_formatted": f"{era_info['current_reward'] / 10**8} UNM",
            "era": era_info['era'],
            "blocks_until_halving": era_info['blocks_until_halving']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/producer/start")
def start_producer():
    try:
        if chain.auto_producing:
            return {"status": "already_producing", "message": "Block producer already running"}
        
        chain.start_auto_producer(interval=10)
        return {"status": "started", "message": "Block producer started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/producer/stop")
def stop_producer():
    try:
        if not chain.auto_producing:
            return {"status": "not_producing", "message": "Block producer not running"}
        
        chain.stop_auto_producer()
        return {"status": "stopped", "message": "Block producer stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/balance/{address}")
def get_balance(address: str):
    try:
        balance = chain.ledger.get_balance(address)
        staked = chain.ledger.get_stake(address)
        nonce = chain.ledger.get_nonce(address)

        return {
            "address": address,
            "balance": balance,
            "staked": staked,
            "nonce": nonce,
            "total": balance + staked
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/validators")
def get_validators():
    try:
        # Doğrudan storage'dan oku
        state = chain.storage.load_state()
        validators_list = []
        
        if state and 'validators' in state:
            for addr, val in state['validators'].items():
                validators_list.append({
                    "address": addr,
                    "stake": val.get('stake', 0),
                    "stake_formatted": f"{val.get('stake', 0) / 10**8:,.0f} UNM",
                    "commission_rate": val.get('commission_rate', 0.1),
                    "jailed": val.get('jailed', False)
                })
        
        return {"total": len(validators_list), "validators": validators_list}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"total": 0, "validators": [], "error": str(e)}

@app.post("/transaction")
def submit_transaction(tx_data: dict):
    try:
        tx = Transaction.from_dict(tx_data)
        if chain.add_transaction(tx):
            return {"success": True, "tx_hash": tx.txid()}
        else:
            raise HTTPException(status_code=400, detail="Invalid transaction")
    except Exception as e:
        print(f"❌ Transaction error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mine")
def mine_block():
    try:
        proposer = chain.consensus.select_proposer(chain.get_height() + 1)

        if not proposer:
            accounts = list(chain.ledger.balances.keys())
            proposer = accounts[0] if accounts else None

        if not proposer:
            raise HTTPException(status_code=500, detail="No proposer available")

        block = chain.create_block(proposer)

        if chain.add_block(block):
            return {
                "success": True,
                "block_height": block.height,
                "block_hash": block.hash,
                "transactions": len(block.transactions),
                "proposer": proposer,
                "reward": block.block_reward,
                "reward_formatted": f"{block.block_reward / 10**8} UNM"
            }
        else:
            raise HTTPException(status_code=400, detail="Block validation failed")
    except Exception as e:
        print(f"❌ Mining error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/block/{height}")
def get_block(height: int):
    try:
        block = chain.storage.load_block(height)
        if block:
            return block.to_dict()
        else:
            raise HTTPException(status_code=404, detail="Block not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== P2P ENDPOINTS ====================

@app.get("/network")
def get_network_info():
    """Get P2P network information"""
    try:
        if not p2p_node:
            return {
                "status": "disabled",
                "message": "P2P network not initialized"
            }
        
        return {
            "status": "active",
            "node_id": p2p_node.node_id,
            "listening": f"{p2p_node.host}:{p2p_node.port}",
            "peers": {
                "connected": len(p2p_node.connections),
                "known": len(p2p_node.peers),
                "max": p2p_node.max_peers
            },
            "bootstrap_nodes": p2p_node.bootstrap_peers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/peers")
def get_peers():
    """Get connected peers list"""
    try:
        if not p2p_node:
            return {"peers": [], "message": "P2P not initialized"}
        
        peers = p2p_node.get_peers_info()
        return {
            "node_id": p2p_node.node_id,
            "connected_peers": len(p2p_node.connections),
            "known_peers": len(peers),
            "max_peers": p2p_node.max_peers,
            "peers": peers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DOWNLOAD ENDPOINTS ====================

@app.get("/download/node-package")
def download_node_package(platform: str = "linux"):
    try:
        if platform == "linux":
            files = [f for f in os.listdir("/tmp") if f.startswith("unicrium-node-package") and f.endswith(".tar.gz")]
            if not files:
                raise HTTPException(status_code=404, detail="Package not found")
            latest = sorted(files)[-1]
            return FileResponse(f"/tmp/{latest}", media_type="application/gzip", filename=latest)
        elif platform == "windows":
            files = [f for f in os.listdir("/tmp") if f.startswith("unicrium-node-windows") and f.endswith(".zip")]
            if not files:
                raise HTTPException(status_code=404, detail="Package not found")
            latest = sorted(files)[-1]
            return FileResponse(f"/tmp/{latest}", media_type="application/zip", filename=latest)
        else:
            raise HTTPException(status_code=400, detail="Invalid platform")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/available-packages")
def available_packages():
    try:
        linux = [f for f in os.listdir("/tmp") if f.startswith("unicrium-node-package") and f.endswith(".tar.gz")]
        windows = [f for f in os.listdir("/tmp") if f.startswith("unicrium-node-windows") and f.endswith(".zip")]
        return {"linux": linux, "windows": windows}
    except:
        return {"linux": [], "windows": []}


@app.get("/evm/stats")
async def get_evm_stats():
    """Get EVM statistics"""
    try:
        stats = chain.evm.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contract/{address}")
async def get_contract(address: str):
    """Get contract information"""
    try:
        exists = chain.evm.contract_exists(address)
        
        if not exists:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        code = chain.evm.get_contract_code(address)
        
        return {
            "success": True,
            "contract": {
                "address": address,
                "exists": exists,
                "code_size": len(code) if code else 0,
                "code_hex": code.hex() if code else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/deploy_contract")
async def deploy_contract(data: dict):
    """
    Deploy smart contract
    
    Body:
    {
        "deployer": "0x...",
        "bytecode": "0x6080604052...",
        "constructor_args": "0x..." (optional),
        "gas_limit": 10000000 (optional)
    }
    """
    try:
        deployer = data.get("deployer")
        bytecode_hex = data.get("bytecode")
        constructor_args_hex = data.get("constructor_args", "")
        gas_limit = data.get("gas_limit", 10_000_000)
        
        if not deployer or not bytecode_hex:
            raise HTTPException(status_code=400, detail="Missing deployer or bytecode")
        
        # Convert hex to bytes
        if bytecode_hex.startswith("0x"):
            bytecode_hex = bytecode_hex[2:]
        
        bytecode = bytes.fromhex(bytecode_hex)
        
        constructor_args = b''
        if constructor_args_hex:
            if constructor_args_hex.startswith("0x"):
                constructor_args_hex = constructor_args_hex[2:]
            constructor_args = bytes.fromhex(constructor_args_hex)
        
        # Deploy contract
        success, address, gas_used, error = chain.evm.deploy_contract(
            deployer=deployer,
            bytecode=bytecode,
            constructor_args=constructor_args,
            gas_limit=gas_limit
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=error)
        
        return {
            "success": True,
            "contract_address": address,
            "gas_used": gas_used,
            "deployer": deployer
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/call_contract")
async def call_contract(data: dict):
    """
    Call contract function
    
    Body:
    {
        "caller": "0x...",
        "contract_address": "0x...",
        "function_data": "0x..." (optional),
        "value": 0 (optional),
        "gas_limit": 1000000 (optional)
    }
    """
    try:
        caller = data.get("caller")
        contract_address = data.get("contract_address")
        function_data_hex = data.get("function_data", "")
        value = data.get("value", 0)
        gas_limit = data.get("gas_limit", 1_000_000)
        
        if not caller or not contract_address:
            raise HTTPException(status_code=400, detail="Missing caller or contract_address")
        
        # Convert hex to bytes
        function_data = b''
        if function_data_hex:
            if function_data_hex.startswith("0x"):
                function_data_hex = function_data_hex[2:]
            function_data = bytes.fromhex(function_data_hex)
        
        # Call contract
        success, return_data, gas_used, error = chain.evm.call_contract(
            caller=caller,
            contract_address=contract_address,
            function_data=function_data,
            value=value,
            gas_limit=gas_limit
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=error)
        
        return {
            "success": True,
            "return_data": return_data.hex() if return_data else "",
            "gas_used": gas_used,
            "caller": caller,
            "contract_address": contract_address
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== METAMASK RPC ENDPOINTS ====================

@app.post("/")
async def json_rpc(request: dict):
    """MetaMask Web3 JSON-RPC endpoint"""
    method = request.get("method")
    params = request.get("params", [])
    id = request.get("id", 1)
    
    try:
        # Chain ID - Unicrium Mainnet = 1001
        if method == "eth_chainId":
            return {"jsonrpc": "2.0", "id": id, "result": "0x3e9"}
            
        # Block number
        elif method == "eth_blockNumber":
            return {"jsonrpc": "2.0", "id": id, "result": hex(chain.get_height())}
            
        # Get balance
        elif method == "eth_getBalance":
            address = params[0] if params else None
            if not address:
                return {"jsonrpc": "2.0", "id": id, "error": {"code": -32602, "message": "Invalid params"}}
            
            balance = chain.ledger.get_balance(address)
            # Convert to Wei-like (UNM has 8 decimals, add 10 zeros for compatibility)
            balance_wei = balance * (10 ** 10)
            return {"jsonrpc": "2.0", "id": id, "result": hex(balance_wei)}
            
        # Gas price
        elif method == "eth_gasPrice":
            return {"jsonrpc": "2.0", "id": id, "result": "0x3b9aca00"}  # 1 Gwei
            
        # Transaction count (nonce)
        elif method == "eth_getTransactionCount":
            address = params[0] if params else None
            if not address:
                return {"jsonrpc": "2.0", "id": id, "error": {"code": -32602, "message": "Invalid params"}}
            
            nonce = chain.ledger.get_nonce(address)
            return {"jsonrpc": "2.0", "id": id, "result": hex(nonce)}
            
        # Network version
        elif method == "net_version":
            return {"jsonrpc": "2.0", "id": id, "result": "1001"}
            
        # Listening
        elif method == "net_listening":
            return {"jsonrpc": "2.0", "id": id, "result": True}
            
        # Peer count
        elif method == "net_peerCount":
            peer_count = len(p2p_node.connections) if p2p_node else 0
            return {"jsonrpc": "2.0", "id": id, "result": hex(peer_count)}
            
        # Protocol version
        elif method == "eth_protocolVersion":
            return {"jsonrpc": "2.0", "id": id, "result": "0x1"}
            
        # Syncing
        elif method == "eth_syncing":
            return {"jsonrpc": "2.0", "id": id, "result": False}
            
        # Accounts (empty - MetaMask manages)
        elif method == "eth_accounts":
            return {"jsonrpc": "2.0", "id": id, "result": []}
            
        # Estimate gas
        elif method == "eth_estimateGas":
            return {"jsonrpc": "2.0", "id": id, "result": hex(21000)}
            
        # Get code
        elif method == "eth_getCode":
            address = params[0] if params else None
            if address and chain.evm.contract_exists(address):
                code = chain.evm.get_contract_code(address)
                return {"jsonrpc": "2.0", "id": id, "result": "0x" + code.hex()}
            return {"jsonrpc": "2.0", "id": id, "result": "0x"}
            
        else:
            return {"jsonrpc": "2.0", "id": id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}
            
    except Exception as e:
        return {"jsonrpc": "2.0", "id": id, "error": {"code": -32000, "message": str(e)}}

@app.get("/metamask")
async def metamask_info():
    """MetaMask connection info"""
    return {
        "network": {
            "name": "Unicrium Mainnet",
            "chainId": 1001,
            "chainIdHex": "0x3e9",
            "rpcUrl": "https://rpc.unicrium.network",
            "currencySymbol": "UNM",
            "decimals": 8,
            "explorerUrl": "https://www.unicrium.network"
        },
        "instructions": [
            "1. Open MetaMask",
            "2. Click 'Add Network' or go to Settings > Networks",
            "3. Click 'Add Network Manually'",
            "4. Enter the network details above",
            "5. Click 'Save' and switch to Unicrium network"
        ]
    }

@app.post("/debug/verify")
def verify_signature(data: dict):
    """Debug endpoint to verify signature"""
    try:
        from core.crypto import KeyPair
        from blockchain.models import Transaction
        
        # Verify signature
        tx = Transaction.from_dict(data)
        is_valid = tx.verify_signature()
        
        return {
            "valid": is_valid,
            "tx_hash": tx.txid()[:16] + "...",
            "sender": tx.sender
        }
    except Exception as e:
        return {"error": str(e)}
