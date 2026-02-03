"""
ERC-8004 Trustless Agents Integration

Queries Ethereum mainnet for agent identity and reputation.
"""

import os
import json
import httpx
from typing import Optional, Dict, Any
from functools import lru_cache

# Contract addresses (Ethereum Mainnet)
IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
REPUTATION_REGISTRY = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

# Default public RPC (rate limited, replace with your own for production)
ETH_RPC_URL = os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com")

# Load ABIs
ABI_DIR = os.path.join(os.path.dirname(__file__), "abis")


@lru_cache(maxsize=1)
def get_identity_abi() -> list:
    with open(os.path.join(ABI_DIR, "IdentityRegistry.json")) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_reputation_abi() -> list:
    with open(os.path.join(ABI_DIR, "ReputationRegistry.json")) as f:
        return json.load(f)


def encode_function_call(abi: list, function_name: str, args: list) -> str:
    """Encode a function call using the ABI."""
    from eth_abi import encode
    from eth_utils import function_signature_to_4byte_selector
    
    # Find function in ABI
    func = next((f for f in abi if f.get("name") == function_name and f.get("type") == "function"), None)
    if not func:
        raise ValueError(f"Function {function_name} not found in ABI")
    
    # Build signature
    input_types = [inp["type"] for inp in func.get("inputs", [])]
    signature = f"{function_name}({','.join(input_types)})"
    selector = function_signature_to_4byte_selector(signature)
    
    # Encode arguments
    if args:
        encoded_args = encode(input_types, args)
        return "0x" + selector.hex() + encoded_args.hex()
    return "0x" + selector.hex()


async def eth_call(to: str, data: str) -> str:
    """Make an eth_call to the Ethereum mainnet."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            ETH_RPC_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": to, "data": data}, "latest"],
                "id": 1,
            },
            timeout=10.0,
        )
        result = response.json()
        if "error" in result:
            raise Exception(f"RPC error: {result['error']}")
        return result.get("result", "0x")


async def get_agent_balance(wallet_address: str) -> int:
    """Check how many agent NFTs a wallet owns."""
    try:
        abi = get_identity_abi()
        data = encode_function_call(abi, "balanceOf", [wallet_address])
        result = await eth_call(IDENTITY_REGISTRY, data)
        return int(result, 16) if result and result != "0x" else 0
    except Exception as e:
        print(f"Error checking agent balance: {e}")
        return 0


async def get_agent_token_by_index(wallet_address: str, index: int = 0) -> Optional[int]:
    """Get the agent token ID owned by a wallet at a given index."""
    try:
        abi = get_identity_abi()
        data = encode_function_call(abi, "tokenOfOwnerByIndex", [wallet_address, index])
        result = await eth_call(IDENTITY_REGISTRY, data)
        return int(result, 16) if result and result != "0x" else None
    except Exception as e:
        print(f"Error getting agent token: {e}")
        return None


async def get_agent_uri(token_id: int) -> Optional[str]:
    """Get the agent's registration file URI."""
    try:
        abi = get_identity_abi()
        data = encode_function_call(abi, "tokenURI", [token_id])
        result = await eth_call(IDENTITY_REGISTRY, data)
        
        if not result or result == "0x":
            return None
            
        # Decode string from ABI encoding
        # Skip first 64 chars (offset) + 64 chars (length), then decode hex to string
        if len(result) > 130:
            hex_str = result[130:]
            # Remove trailing zeros and decode
            uri_bytes = bytes.fromhex(hex_str.rstrip("0") if len(hex_str) % 2 == 0 else hex_str[:-1].rstrip("0"))
            return uri_bytes.decode("utf-8", errors="ignore").rstrip("\x00")
        return None
    except Exception as e:
        print(f"Error getting agent URI: {e}")
        return None


async def fetch_agent_registration(uri: str) -> Optional[Dict[str, Any]]:
    """Fetch and parse the agent registration file."""
    try:
        # Handle IPFS URIs
        if uri.startswith("ipfs://"):
            uri = f"https://ipfs.io/ipfs/{uri[7:]}"
        elif uri.startswith("data:"):
            # Handle base64 data URIs
            import base64
            if "base64," in uri:
                data = uri.split("base64,")[1]
                return json.loads(base64.b64decode(data).decode())
        
        async with httpx.AsyncClient() as client:
            response = await client.get(uri, timeout=10.0, follow_redirects=True)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"Error fetching registration file: {e}")
    return None


async def get_8004_credentials(wallet_address: str) -> Optional[Dict[str, Any]]:
    """
    Get ERC-8004 credentials for a wallet address.
    
    Returns:
        {
            "agent_id": 123,
            "agent_registry": "eip155:1:0x8004A169...",
            "name": "AgentName",
            "description": "...",
            "image": "https://...",
            "services": [...],
            "x402_support": True,
            "8004scan_url": "https://8004scan.io/agent/123"
        }
    """
    # Check if wallet has any agent NFTs
    balance = await get_agent_balance(wallet_address)
    if balance == 0:
        return None
    
    # Get the first agent token
    token_id = await get_agent_token_by_index(wallet_address, 0)
    if token_id is None:
        return None
    
    # Get the registration file URI
    uri = await get_agent_uri(token_id)
    
    credentials = {
        "agent_id": token_id,
        "agent_registry": f"eip155:1:{IDENTITY_REGISTRY}",
        "8004scan_url": f"https://8004scan.io/agent/{token_id}",
    }
    
    # Try to fetch registration file for more details
    if uri:
        registration = await fetch_agent_registration(uri)
        if registration:
            credentials.update({
                "name": registration.get("name"),
                "description": registration.get("description"),
                "image": registration.get("image"),
                "services": registration.get("services", []),
                "x402_support": registration.get("x402Support", False),
            })
    
    return credentials


# Simplified version that doesn't need eth_abi (uses raw encoding)
async def get_8004_credentials_simple(wallet_address: str) -> Optional[Dict[str, Any]]:
    """
    Simplified ERC-8004 lookup using raw RPC calls.
    Falls back to this if eth_abi is not installed.
    """
    try:
        # balanceOf(address) selector = 0x70a08231
        # Pad address to 32 bytes
        padded_addr = wallet_address.lower().replace("0x", "").zfill(64)
        data = f"0x70a08231{padded_addr}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ETH_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{"to": IDENTITY_REGISTRY, "data": data}, "latest"],
                    "id": 1,
                },
                timeout=10.0,
            )
            result = response.json()
            
            if "error" in result:
                return None
                
            balance = int(result.get("result", "0x0"), 16)
            
            if balance == 0:
                return None
            
            # Has at least one agent - return basic info
            # Full lookup would require tokenOfOwnerByIndex + tokenURI
            return {
                "has_8004": True,
                "agent_count": balance,
                "agent_registry": f"eip155:1:{IDENTITY_REGISTRY}",
                "8004scan_url": f"https://8004scan.io/address/{wallet_address}",
            }
            
    except Exception as e:
        print(f"Error in simple 8004 lookup: {e}")
        return None
