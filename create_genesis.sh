#!/bin/bash
# Unicrium Genesis Creation Script

echo "============================================================"
echo "  🌟 UNICRIUM GENESIS CREATION"
echo "============================================================"
echo ""

# Check if genesis already exists
if [ -d "blockchain_data/blocks" ]; then
    echo "⚠️  Warning: blockchain_data already exists!"
    echo ""
    read -p "Delete existing data and create new genesis? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Genesis creation cancelled."
        exit 1
    fi
    
    echo "🗑️  Removing existing blockchain_data..."
    rm -rf blockchain_data/
    echo "✅ Removed"
    echo ""
fi

echo "📦 Creating genesis block..."
echo ""

# Run genesis creation
python3 -c "
import sys
import os
sys.path.insert(0, '.')

# Import and run
from config import genesis_production
genesis_production.create_genesis()
"

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "  ✅ GENESIS CREATED SUCCESSFULLY!"
    echo "============================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Start API server: ./start_node.sh"
    echo "  2. Or manually: cd blockchain && python api_server.py"
    echo ""
else
    echo ""
    echo "❌ Genesis creation failed!"
    echo "Check error messages above."
    exit 1
fi
