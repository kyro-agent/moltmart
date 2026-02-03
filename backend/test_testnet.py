#!/usr/bin/env python3
"""
Test ERC-8004 minting on Base Sepolia testnet.
Bypasses x402 to test just the mint+transfer logic.

Usage:
  USE_TESTNET=true python3 test_testnet.py
"""

import os
import asyncio

# Force testnet
os.environ["USE_TESTNET"] = "true"

from erc8004 import (
    register_agent,
    get_8004_credentials_simple,
    check_connection,
    BASE_CHAIN_ID,
    IDENTITY_REGISTRY,
)

TEST_WALLET = "0x90d9c75f3761c02Bf3d892A701846F6323e9112D"


async def main():
    print("=" * 50)
    print("ERC-8004 Testnet Test")
    print("=" * 50)
    
    # Check connection
    print("\n1. Checking connection...")
    conn = check_connection()
    print(f"   Chain ID: {BASE_CHAIN_ID}")
    print(f"   Registry: {IDENTITY_REGISTRY}")
    print(f"   Connected: {conn.get('connected')}")
    print(f"   Operator: {conn.get('operator_address')}")
    print(f"   Operator ETH: {conn.get('operator_balance_eth')}")
    
    if not conn.get("connected"):
        print("\n❌ Not connected! Check RPC and operator key.")
        return
    
    if not conn.get("operator_address"):
        print("\n❌ FACILITATOR_PRIVATE_KEY not set!")
        print("   Set it in environment or run on Railway")
        return
        
    if (conn.get("operator_balance_eth") or 0) < 0.001:
        print(f"\n⚠️ Operator needs testnet ETH!")
        print(f"   Get from: https://www.coinbase.com/faucets/base-sepolia")
        print(f"   Send to: {conn.get('operator_address')}")
        return
    
    # Check if wallet already has ERC-8004
    print(f"\n2. Checking existing ERC-8004 for {TEST_WALLET[:10]}...")
    creds = await get_8004_credentials_simple(TEST_WALLET)
    if creds and creds.get("has_8004"):
        print(f"   ✅ Already has ERC-8004! Count: {creds.get('agent_count')}")
    else:
        print("   ❌ No ERC-8004 found")
    
    # Mint new identity
    print(f"\n3. Minting ERC-8004 for {TEST_WALLET[:10]}...")
    agent_uri = f"https://moltmart.app/identity/{TEST_WALLET}/profile.json"
    
    result = register_agent(agent_uri, TEST_WALLET)
    
    print(f"   Result: {result}")
    
    if result.get("success"):
        print(f"\n✅ SUCCESS!")
        print(f"   Agent ID: {result.get('agent_id')}")
        print(f"   Mint TX: {result.get('tx_hash')}")
        print(f"   Transfer TX: {result.get('transfer_tx_hash')}")
        print(f"   Owner: {result.get('owner')}")
        
        # Verify ownership
        print(f"\n4. Verifying ownership...")
        creds = await get_8004_credentials_simple(TEST_WALLET)
        if creds and creds.get("has_8004"):
            print(f"   ✅ Wallet now owns ERC-8004!")
        else:
            print(f"   ❌ Transfer may have failed - check on-chain")
    else:
        print(f"\n❌ FAILED: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
