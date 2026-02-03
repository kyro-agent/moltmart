#!/usr/bin/env python3
"""
Test ERC-8004 mint + transfer on Base Sepolia
"""
import os
import sys

# Force testnet mode
os.environ["USE_TESTNET"] = "true"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from erc8004 import register_agent, get_agent_info, w3, IDENTITY_REGISTRY, get_operator_account

# Test wallet (the one we've been testing with)
TEST_WALLET = "0x90d9c75f3761c02Bf3d892A701846F6323e9112D"

def main():
    account = get_operator_account()
    if not account:
        print("❌ No operator account configured")
        return
    
    print(f"🔑 Operator wallet: {account.address}")
    
    # Check operator balance
    balance = w3.eth.get_balance(account.address)
    print(f"💰 Operator balance: {w3.from_wei(balance, 'ether')} ETH")
    
    if balance < w3.to_wei(0.01, 'ether'):
        print("❌ Insufficient balance for gas")
        return
    
    # Test mint + transfer
    print(f"\n🚀 Minting ERC-8004 identity for {TEST_WALLET}...")
    result = register_agent(
        agent_uri="https://moltmart.app/api/identity/test-sepolia",
        recipient_wallet=TEST_WALLET
    )
    
    print(f"\n📋 Result: {result}")
    
    if result.get("success"):
        agent_id = result.get("agent_id")
        print(f"\n✅ Minted Agent ID: {agent_id}")
        print(f"📝 Mint TX: https://sepolia.basescan.org/tx/{result.get('tx_hash')}")
        
        if result.get("transfer_tx_hash"):
            print(f"📝 Transfer TX: https://sepolia.basescan.org/tx/{result.get('transfer_tx_hash')}")
            
            # Verify ownership
            info = get_agent_info(agent_id)
            print(f"\n🔍 Verification:")
            print(f"   Owner: {info.get('owner')}")
            print(f"   Expected: {TEST_WALLET}")
            print(f"   Match: {'✅' if info.get('owner', '').lower() == TEST_WALLET.lower() else '❌'}")
        else:
            print("⚠️ No transfer TX hash - transfer may have failed")
    else:
        print(f"❌ Error: {result.get('error')}")

if __name__ == "__main__":
    main()
