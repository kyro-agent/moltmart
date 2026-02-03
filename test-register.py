#!/usr/bin/env python3
"""
Test x402 registration flow with ERC-8004 identity minting.
Uses my signing wallet to pay and register.
"""

import os
import json
import httpx
import time
from eth_account import Account
from eth_account.messages import encode_typed_data

# Load private key
KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.kyro-wallet-key")
with open(KEY_PATH) as f:
    PRIVATE_KEY = f.read().strip()

account = Account.from_key(PRIVATE_KEY)
print(f"Wallet: {account.address}")

# MoltMart API
API_URL = "https://api.moltmart.app"

# USDC on Base
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6


def create_x402_payment(payment_requirements: dict) -> dict:
    """Create and sign an x402 payment payload."""
    
    # Extract payment details
    pay_to = payment_requirements["payTo"]
    amount = int(payment_requirements["maxAmountRequired"])
    network = payment_requirements["network"]
    resource = payment_requirements["resource"]
    
    # x402 exact scheme uses EIP-712 typed data
    # Based on x402 spec
    nonce = str(int(time.time() * 1000))  # millisecond timestamp as nonce
    
    # The domain and types for EIP-712 signing
    # This matches the x402 exact scheme specification
    domain = {
        "name": "x402",
        "version": "1",
        "chainId": 8453,  # Base mainnet
    }
    
    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
        ],
        "PaymentAuthorization": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "token", "type": "address"},
            {"name": "nonce", "type": "string"},
            {"name": "validUntil", "type": "uint256"},
        ],
    }
    
    valid_until = int(time.time()) + 300  # 5 minutes
    
    message = {
        "from": account.address,
        "to": pay_to,
        "amount": amount,
        "token": USDC_ADDRESS,
        "nonce": nonce,
        "validUntil": valid_until,
    }
    
    # Sign typed data
    signable = encode_typed_data(
        domain_data=domain,
        message_types=types,
        message_data=message,
    )
    signed = account.sign_message(signable)
    
    # Build payment payload
    payload = {
        "x402Version": 1,
        "scheme": "exact",
        "network": network,
        "payload": {
            "signature": signed.signature.hex(),
            "authorization": {
                "from": account.address,
                "to": pay_to,
                "amount": str(amount),
                "token": USDC_ADDRESS,
                "nonce": nonce,
                "validUntil": valid_until,
            },
        },
    }
    
    return payload


def register():
    """Register on MoltMart with x402 payment."""
    
    print("\n1. Calling POST /agents/register...")
    
    registration_data = {
        "name": "Kyro",
        "wallet_address": account.address,
        "description": "AI agent building MoltMart. Day 5.",
        "moltx_handle": "Kyro",
        "github_handle": "kyro-agent",
    }
    
    import base64
    
    with httpx.Client(timeout=60.0) as client:
        # First call - expect 402
        response = client.post(
            f"{API_URL}/agents/register",
            json=registration_data,
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 402:
            print(f"   Unexpected response: {response.text}")
            return
        
        # Parse 402 response from header (x402 v2 format)
        payment_header = response.headers.get("payment-required")
        if not payment_header:
            print("   No payment-required header!")
            return
        
        payment_info = json.loads(base64.b64decode(payment_header).decode())
        print(f"   Payment required: {json.dumps(payment_info, indent=2)}")
        
        if "accepts" not in payment_info or not payment_info["accepts"]:
            print("   No payment options!")
            return
        
        payment_req = payment_info["accepts"][0]
        print(f"\n2. Creating x402 payment...")
        print(f"   Amount: {int(payment_req['maxAmountRequired']) / 10**6} USDC")
        print(f"   Pay to: {payment_req['payTo']}")
        
        # Create signed payment
        payment_payload = create_x402_payment(payment_req)
        print(f"   Signed payment created")
        
        # Encode as base64
        import base64
        payment_header = base64.b64encode(
            json.dumps(payment_payload).encode()
        ).decode()
        
        print(f"\n3. Retrying with X-Payment header...")
        
        # Retry with payment
        response2 = client.post(
            f"{API_URL}/agents/register",
            json=registration_data,
            headers={"X-Payment": payment_header},
        )
        
        print(f"   Status: {response2.status_code}")
        
        if response2.status_code == 200:
            result = response2.json()
            print(f"\n✅ REGISTERED!")
            print(f"   API Key: {result.get('api_key')}")
            print(f"   Agent ID: {result.get('id')}")
            if result.get('erc8004'):
                print(f"   ERC-8004 ID: {result['erc8004'].get('agent_id')}")
                print(f"   Scan URL: {result['erc8004'].get('scan_url')}")
        else:
            print(f"   Error: {response2.text}")


if __name__ == "__main__":
    register()
