#!/bin/bash
# Unicrium Node Startup Script

echo "============================================================"
echo "  🚀 UNICRIUM NODE STARTUP"
echo "============================================================"
echo ""

# Check if genesis exists
if [ ! -d "blockchain_data/blocks" ]; then
    echo "❌ Genesis not found!"
    echo ""
    echo "Please create genesis first:"
    echo "  ./create_genesis.sh"
    echo ""
    exit 1
fi

# Check dependencies
echo "🔍 Checking dependencies..."
python3 -c "
import fastapi, uvicorn, rocksdict, ecdsa
print('✅ All dependencies installed')
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies!"
    echo ""
    echo "Install with:"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo "✅ Dependencies OK"
echo ""

# Add current directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "📊 Blockchain Status:"
python3 -c "
import sys
sys.path.insert(0, '.')
from storage.storage import PersistentStorage

storage = PersistentStorage('blockchain_data')
meta = storage.get_metadata()

if meta:
    print(f\"   Height: {meta.get('height', -1)}\")
    print(f\"   Latest Hash: {meta.get('latest_hash', 'N/A')[:32]}...\")
else:
    print('   Height: -1 (empty)')

storage.close()
"
echo ""

echo "🚀 Starting API Server..."
echo "   Endpoint: http://0.0.0.0:5000"
echo "   Press Ctrl+C to stop"
echo ""
echo "============================================================"
echo ""

# Start API server
cd blockchain
python3 api_server.py
