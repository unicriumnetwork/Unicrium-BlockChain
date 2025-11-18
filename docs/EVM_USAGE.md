# Unicrium EVM - Usage Guide

## Contract Deployment

### API Request:
```bash
curl -X POST http://localhost:5000/deploy_contract \
  -H "Content-Type: application/json" \
  -d '{
    "deployer": "0xYOUR_ADDRESS",
    "bytecode": "0x6080604052...",
    "constructor_args": "0x..." (optional),
    "gas_limit": 10000000
  }'
Response:
{
  "success": true,
  "contract_address": "0x954Ecd56442cB525dC29A176Ad3FB3B12Bd266B6",
  "gas_used": 33000,
  "deployer": "0xYOUR_ADDRESS"
}
Contract Call
API Request:
curl -X POST http://localhost:5000/call_contract \
  -H "Content-Type: application/json" \
  -d '{
    "caller": "0xYOUR_ADDRESS",
    "contract_address": "0x954...",
    "function_data": "0x6d4ce63c",
    "value": 0,
    "gas_limit": 1000000
  }'
Get Contract Info
curl http://localhost:5000/contract/0x954Ecd56442cB525dC29A176Ad3FB3B12Bd266B6
EVM Stats
curl http://localhost:5000/evm/stats
Technical Details
Fork: Berlin
Hash Algorithm: KECCAK256 (EVM layer)
Address Generation: Ethereum CREATE standard
Gas Pricing: Ethereum-compatible
Chain ID: 1 (mainnet-compatible)
Limitations (Phase 1)
⚠️ No actual bytecode execution (validation only)
⚠️ No events/logs
⚠️ No precompiled contracts
⚠️ Simple storage (no state trie)
Contract deployment and storage work, but actual smart contract logic execution (opcodes) will be implemented in Phase 2.
