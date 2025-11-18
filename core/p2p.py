"""
Unicrium P2P Network Module
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import socket
import logging

logger = logging.getLogger(__name__)


@dataclass
class Peer:
    """Peer information"""
    address: str  # IP:Port
    node_id: str  # Unique node ID
    chain_height: int = 0
    last_seen: int = 0
    connected: bool = False
    version: str = "2.0.0"
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class P2PMessage:
    """P2P message format"""
    type: str  # handshake, ping, block, tx, peers
    data: dict
    sender_id: str
    timestamp: int
    
    def to_json(self) -> str:
        return json.dumps({
            'type': self.type,
            'data': self.data,
            'sender_id': self.sender_id,
            'timestamp': self.timestamp
        })
    
    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls(**data)


class P2PNode:
    """P2P Network Node"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 26656, blockchain=None):
        self.host = host
        self.port = port
        self.blockchain = blockchain
        
        # Node identity
        self.node_id = self._generate_node_id()
        
        # Peers
        self.peers: Dict[str, Peer] = {}
        self.peer_info: Dict[str, dict] = {}  # Peer metadata
        self.max_peers = 50
        
        # Bootstrap nodes (main node)
        # For main node: empty, For client nodes: add main node
        import os
        if os.path.exists('blockchain_data/blocks'):
            # Has blockchain data = main node
            self.bootstrap_peers = []
        else:
            # No data = client node, connect to main
            self.bootstrap_peers = ["91.99.170.174:26656"]
        
        # Connection tracking
        self.connections: Dict[str, asyncio.StreamWriter] = {}
        
        # Server
        self.server: Optional[asyncio.Server] = None
        self.running = False
        
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        import hashlib
        hostname = socket.gethostname()
        timestamp = str(time.time())
        return hashlib.sha256(f"{hostname}{timestamp}".encode()).hexdigest()[:16]
    
    async def start(self):
        """Start P2P server"""
        self.running = True
        
        # Start TCP server
        self.server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port
        )
        
        print(f"🌐 P2P Node listening on {self.host}:{self.port}")
        print(f"📌 Node ID: {self.node_id}")
        logger.info(f"🌐 P2P Node started on {self.host}:{self.port}")
        logger.info(f"📌 Node ID: {self.node_id}")
        
        print(f"🔗 Connecting to bootstrap: {self.bootstrap_peers}")
        
        # Connect to bootstrap peers
        asyncio.create_task(self.connect_to_bootstrap())
        
        # Start maintenance tasks
        asyncio.create_task(self.peer_maintenance())
        asyncio.create_task(self.start_sync_loop())
        # Initial sync after connection
        async def initial_sync():
            await asyncio.sleep(5)  # Wait for peers
            await self.sync_blockchain()
        
        asyncio.create_task(initial_sync())
        
        # Keep server running without blocking
        async with self.server:
            try:
                while self.running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
    async def connect_to_bootstrap(self):
        """Connect to bootstrap nodes"""
        for peer_addr in self.bootstrap_peers:
            try:
                await self.connect_to_peer(peer_addr)
            except Exception as e:
                logger.warning(f"Failed to connect to bootstrap {peer_addr}: {e}")
    
    async def connect_to_peer(self, address: str):
        """Connect to a peer"""
        if address in self.connections:
            return
        
        try:
            host, port = address.split(":")
            reader, writer = await asyncio.open_connection(host, int(port))
            
            # Send handshake
            handshake = P2PMessage(
                type="handshake",
                data={
                    "node_id": self.node_id,
                    "chain_height": self.blockchain.get_height() if self.blockchain else 0,
                    "version": "2.0.0"
                },
                sender_id=self.node_id,
                timestamp=int(time.time())
            )
            
            writer.write((handshake.to_json() + "\n").encode())
            await writer.drain()
            
            # Store connection
            self.connections[address] = writer
            
            # Handle incoming messages
            asyncio.create_task(self.handle_peer_messages(reader, writer, address))
            
            logger.info(f"✅ Connected to peer: {address}")
            
        except Exception as e:
            logger.error(f"Failed to connect to {address}: {e}")
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming peer connection"""
        peer_addr = writer.get_extra_info('peername')
        peer_addr_str = f"{peer_addr[0]}:{peer_addr[1]}"
        logger.info(f"📥 New connection from {peer_addr_str}")

        # EKLE: Writer'ı connections'a kaydet
        self.connections[peer_addr_str] = writer

        try:
            await self.handle_peer_messages(reader, writer, peer_addr_str)
        except Exception as e:
            logger.error(f"Error handling connection from {peer_addr}: {e}")
        finally:
            # Temizle
            if peer_addr_str in self.connections:
                del self.connections[peer_addr_str]
            writer.close()
            await writer.wait_closed()

    
    async def handle_peer_messages(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, peer_addr: str):
        """Handle messages from a peer"""
        buffer = ""
        
        while self.running:
            try:
                data = await reader.read(4096)
                if not data:
                    break
                
                buffer += data.decode()
                
                # Process complete messages (newline separated)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        await self.process_message(line, peer_addr)
                        
            except Exception as e:
                logger.error(f"Error reading from {peer_addr}: {e}")
                break
        
        # Cleanup
        if peer_addr in self.connections:
            del self.connections[peer_addr]
    
    async def process_message(self, msg_json: str, peer_addr: str):
        """Process incoming message"""
        try:
            msg = P2PMessage.from_json(msg_json)
            
            if msg.type == "handshake":
                print(f"🔔 DEBUG: Handshake received from {peer_addr}")
                # Save peer info
                self.peer_info[peer_addr] = {"node_id": msg.data.get("node_id"), "version": msg.data.get("version", "1.0.0"), "chain_height": msg.data.get("chain_height", -1)}
                print(f"💾 Peer: {peer_addr} height={self.peer_info[peer_addr].get('chain_height', -1)}")
                # Check if peer is self (same node_id)
                if msg.data['node_id'] == self.node_id:
                    logger.warning(f"⚠️  Received handshake from self, closing connection")
                    return
                
                # Store peer info
                self.peers[peer_addr] = Peer(
                    address=peer_addr,
                    node_id=msg.data['node_id'],
                    chain_height=msg.data.get('chain_height', 0),
                    last_seen=int(time.time()),
                    connected=True,
                    version=msg.data.get('version', '2.0.0')
                )
                logger.info(f"🤝 Handshake from {msg.data['node_id']} (height: {msg.data['chain_height']})")

                # SEND HANDSHAKE RESPONSE
                handshake_response = P2PMessage(
                    type="handshake",
                    data={
                        "node_id": self.node_id,
                        "chain_height": self.blockchain.get_height() if self.blockchain else 0,
                        "version": "2.0.0"
                    },
                    sender_id=self.node_id,
                    timestamp=int(time.time())
                )
                if peer_addr in self.connections:
                    writer = self.connections[peer_addr]
                    writer.write((handshake_response.to_json() + "\n").encode())
                    await writer.drain()
                    logger.info(f"✅ Sent handshake response to {peer_addr}")
                print(f"🔔 DEBUG: Handshake response sent to {peer_addr}")
                
                # Send our peer list
                await self.send_peers(peer_addr)
                
            elif msg.type == "ping":
                # Respond with pong
                await self.send_message(peer_addr, "pong", {})
                
            elif msg.type == "get_block":
                # Send requested block
                height = msg.data['height']
                if self.blockchain:
                    block = self.blockchain.storage.load_block(height)
                    if block:
                        print(f"📤 Block #{height} → {peer_addr}")
                    await self.send_message(peer_addr, "block", block.to_dict())
                        
            elif msg.type == "block":
                # Received block
                try:
                    from blockchain.models import Block
                    block_data = msg.data
                    block = Block.from_dict(block_data)
                    
                    # Check if we need this block
                    if block.height == self.blockchain.get_height() + 1:
                        if self.blockchain.add_block(block):
                            logger.info(f"📦 Block #{block.height} synced successfully")
                        else:
                            logger.warning(f"⚠️  Block #{block.height} validation failed")
                    elif block.height > self.blockchain.get_height() + 1:
                        logger.info(f"📦 Received future block #{block.height}, requesting missing blocks...")
                        await self.sync_blockchain()
                    
                except Exception as e:
                    logger.error(f"Error processing block: {e}")
                
            elif msg.type == "tx":
                # Received transaction
                logger.info(f"💸 Received transaction from {peer_addr}")
                # TODO: Add to mempool
                
            elif msg.type == "peers":
                # Received peer list
                for peer_data in msg.data.get('peers', []):
                    peer_address = peer_data['address']
                    if peer_address not in self.peers and len(self.peers) < self.max_peers:
                        # Try to connect to new peer
                        asyncio.create_task(self.connect_to_peer(peer_address))
                        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def send_message(self, peer_addr: str, msg_type: str, data: dict):
        """Send message to peer"""
        if peer_addr not in self.connections:
            return
        
        try:
            msg = P2PMessage(
                type=msg_type,
                data=data,
                sender_id=self.node_id,
                timestamp=int(time.time())
            )
            
            writer = self.connections[peer_addr]
            writer.write((msg.to_json() + "\n").encode())
            await writer.drain()
            
        except Exception as e:
            logger.error(f"Error sending to {peer_addr}: {e}")
            if peer_addr in self.connections:
                del self.connections[peer_addr]
    
    async def send_peers(self, peer_addr: str):
        """Send peer list to a peer"""
        peers_data = [p.to_dict() for p in list(self.peers.values())[:20]]
        await self.send_message(peer_addr, "peers", {"peers": peers_data})
    
    async def broadcast(self, msg_type: str, data: dict):
        """Broadcast message to all peers"""
        tasks = []
        for peer_addr in list(self.connections.keys()):
            tasks.append(self.send_message(peer_addr, msg_type, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    

    async def sync_blockchain(self):
        """Sync blockchain from peers"""
        print("🔧 DEBUG: sync_blockchain() CALLED!")
        if not self.blockchain:
            return
        
        try:
            # Get local height
            local_height = self.blockchain.get_height()
            print(f"🔧 DEBUG: Local height={local_height}")
            print(f"🔧 DEBUG: Local height = {local_height}")
            
            # Get peer heights from peer_info
            peer_heights = []
            print(f"🔧 DEBUG: Checking {len(self.peer_info)} peers")
            for peer_addr, info in self.peer_info.items():
                peer_height = info.get("chain_height", -1)
                print(f"🔧 DEBUG: Peer {peer_addr} height={peer_height}, local={local_height}")
                if peer_height > local_height:
                    print(f"🔧 DEBUG: ✅ Peer {peer_addr} is ahead!")
                    peer_heights.append((peer_addr, peer_height))
            
            if not peer_heights:
                print("🔧 DEBUG: No peers ahead")
                logger.info("✅ Blockchain synced - no peers ahead")
                return
            
            # Find highest peer
            peer_heights.sort(key=lambda x: x[1], reverse=True)
            sync_peer, target_height = peer_heights[0]
            
            if target_height <= local_height:
                logger.info("✅ Blockchain synced")
                return
            
            print(f"📥 Syncing blockchain from height {local_height} to {target_height}")
            print(f"   Peer: {sync_peer}")
            
            # Request missing blocks
            for height in range(local_height + 1, target_height + 1):
                try:
                    # Request block
                    await self.send_message(sync_peer, "get_block", {"height": height})
                    
                    # Wait for response (with timeout)
                    await asyncio.sleep(0.1)  # Small delay between requests
                    
                    if height % 100 == 0:
                        print(f"   Synced: {height}/{target_height} ({height*100//target_height}%)")
                
                except Exception as e:
                    logger.error(f"Error requesting block {height}: {e}")
                    break
            
            logger.info(f"✅ Blockchain sync complete! Height: {self.blockchain.get_height()}")
            
        except Exception as e:
            logger.error(f"Blockchain sync error: {e}")
    
    async def start_sync_loop(self):
        """Periodically check and sync blockchain"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self.peers:
                    await self.sync_blockchain()
                    
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
    async def peer_maintenance(self):
        """Maintain peer connections"""
        while self.running:
            try:
                # Remove stale peers
                now = int(time.time())
                stale_peers = [
                    addr for addr, peer in self.peers.items()
                    if now - peer.last_seen > 300  # 5 minutes
                ]
                
                for addr in stale_peers:
                    del self.peers[addr]
                    if addr in self.connections:
                        self.connections[addr].close()
                        del self.connections[addr]
                
                # Ping active peers
                for peer_addr in list(self.connections.keys()):
                    await self.send_message(peer_addr, "ping", {})
                
                await asyncio.sleep(60)  # Every minute
                
            except Exception as e:
                logger.error(f"Peer maintenance error: {e}")
    
    async def stop(self):
        """Stop P2P node"""
        self.running = False
        
        # Close all connections
        for writer in self.connections.values():
            writer.close()
            await writer.wait_closed()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("⛔ P2P Node stopped")
    
    def get_peers_info(self) -> List[dict]:
        """Get peer information"""
        return [p.to_dict() for p in self.peers.values()]
