"""
ERC-8004 Integration for MoltMart
Handles agent identity registration and reputation on Base mainnet
"""

import json
import os
from typing import Optional
from web3 import Web3
from eth_account import Account

# Base Mainnet
BASE_CHAIN_ID = 8453
BASE_RPC = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")

# ERC-8004 Contract Addresses on Base Mainnet
IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
REPUTATION_REGISTRY = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

# MoltMart operator wallet (same as facilitator - receives fees, mints identities)
OPERATOR_PRIVATE_KEY = os.getenv("FACILITATOR_PRIVATE_KEY", "")

# Load ABIs
ABI_DIR = os.path.join(os.path.dirname(__file__), "abis")

def load_abi(name: str) -> list:
    """Load contract ABI from file"""
    path = os.path.join(ABI_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(BASE_RPC))

# Load contract ABIs
IDENTITY_ABI = load_abi("IdentityRegistry")
REPUTATION_ABI = load_abi("ReputationRegistry")

# Contract instances
identity_registry = w3.eth.contract(
    address=Web3.to_checksum_address(IDENTITY_REGISTRY),
    abi=IDENTITY_ABI
) if IDENTITY_ABI else None

reputation_registry = w3.eth.contract(
    address=Web3.to_checksum_address(REPUTATION_REGISTRY),
    abi=REPUTATION_ABI
) if REPUTATION_ABI else None


def get_operator_account():
    """Get the MoltMart operator account for signing transactions"""
    if not OPERATOR_PRIVATE_KEY:
        return None
    return Account.from_key(OPERATOR_PRIVATE_KEY)


def register_agent(agent_uri: str) -> dict:
    """
    Register a new agent identity on ERC-8004
    
    Args:
        agent_uri: URI pointing to agent registration JSON (IPFS or HTTPS)
        
    Returns:
        dict with agentId (tokenId) and transaction hash
    """
    if not identity_registry:
        return {"error": "Identity registry not configured"}
    
    account = get_operator_account()
    if not account:
        return {"error": "Operator wallet not configured"}
    
    try:
        # Build transaction
        nonce = w3.eth.get_transaction_count(account.address)
        
        tx = identity_registry.functions.register(agent_uri).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': BASE_CHAIN_ID
        })
        
        # Sign and send
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        
        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        # Parse the Registered event to get agentId
        agent_id = None
        for log in receipt.logs:
            try:
                decoded = identity_registry.events.Registered().process_log(log)
                agent_id = decoded.args.agentId
                break
            except:
                continue
        
        return {
            "success": True,
            "agent_id": agent_id,
            "tx_hash": tx_hash.hex(),
            "block": receipt.blockNumber
        }
        
    except Exception as e:
        return {"error": str(e)}


def get_agent_info(agent_id: int) -> dict:
    """Get agent information from the registry"""
    if not identity_registry:
        return {"error": "Identity registry not configured"}
    
    try:
        owner = identity_registry.functions.ownerOf(agent_id).call()
        uri = identity_registry.functions.tokenURI(agent_id).call()
        wallet = identity_registry.functions.getAgentWallet(agent_id).call()
        
        return {
            "agent_id": agent_id,
            "owner": owner,
            "uri": uri,
            "wallet": wallet if wallet != "0x0000000000000000000000000000000000000000" else None
        }
    except Exception as e:
        return {"error": str(e)}


def give_feedback(agent_id: int, value: int = 1, tag: str = "service") -> dict:
    """
    Submit feedback for an agent after a successful transaction
    
    Args:
        agent_id: The ERC-8004 agent tokenId
        value: Feedback value (positive = good, negative = bad)
        tag: Category tag (e.g., "service", "delivery", "quality")
        
    Returns:
        dict with transaction hash
    """
    if not reputation_registry:
        return {"error": "Reputation registry not configured"}
    
    account = get_operator_account()
    if not account:
        return {"error": "Operator wallet not configured"}
    
    try:
        nonce = w3.eth.get_transaction_count(account.address)
        
        # giveFeedback(agentId, value, valueDecimals, tag1, tag2, endpoint, feedbackURI, feedbackHash)
        tx = reputation_registry.functions.giveFeedback(
            agent_id,           # agentId
            value,              # value (int128)
            0,                  # valueDecimals (0 = whole numbers)
            tag,                # tag1
            "",                 # tag2
            "",                 # endpoint
            "",                 # feedbackURI
            b'\x00' * 32        # feedbackHash (empty)
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'chainId': BASE_CHAIN_ID
        })
        
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        return {
            "success": True,
            "tx_hash": tx_hash.hex(),
            "block": receipt.blockNumber
        }
        
    except Exception as e:
        return {"error": str(e)}


def get_reputation(agent_id: int, tag: str = "") -> dict:
    """
    Get reputation summary for an agent
    
    Args:
        agent_id: The ERC-8004 agent tokenId
        tag: Optional tag filter
        
    Returns:
        dict with count and summary value
    """
    if not reputation_registry:
        return {"error": "Reputation registry not configured"}
    
    try:
        # getSummary(agentId, clientAddresses[], tag1, tag2)
        count, value, decimals = reputation_registry.functions.getSummary(
            agent_id,
            [],     # all clients
            tag,    # tag1 filter
            ""      # tag2 filter
        ).call()
        
        # Convert fixed-point to float
        actual_value = value / (10 ** decimals) if decimals > 0 else value
        
        return {
            "agent_id": agent_id,
            "feedback_count": count,
            "reputation_score": actual_value,
            "decimals": decimals
        }
        
    except Exception as e:
        return {"error": str(e)}


def get_agent_registry_uri(agent_id: int) -> str:
    """
    Build the full agent registry identifier
    Format: eip155:{chainId}:{registryAddress}
    """
    return f"eip155:{BASE_CHAIN_ID}:{IDENTITY_REGISTRY}"


# Health check
def check_connection() -> dict:
    """Verify connection to Base and contract access"""
    try:
        connected = w3.is_connected()
        block = w3.eth.block_number if connected else None
        
        operator = get_operator_account()
        operator_address = operator.address if operator else None
        operator_balance = None
        if operator_address and connected:
            operator_balance = w3.eth.get_balance(operator_address)
            operator_balance = w3.from_wei(operator_balance, 'ether')
        
        return {
            "connected": connected,
            "chain_id": BASE_CHAIN_ID,
            "block": block,
            "identity_registry": IDENTITY_REGISTRY,
            "reputation_registry": REPUTATION_REGISTRY,
            "operator": operator_address,
            "operator_balance_eth": float(operator_balance) if operator_balance else None,
            "identity_abi_loaded": bool(IDENTITY_ABI),
            "reputation_abi_loaded": bool(REPUTATION_ABI)
        }
    except Exception as e:
        return {"error": str(e)}


async def get_8004_credentials_simple(wallet_address: str) -> Optional[dict]:
    """
    Check if a wallet has ERC-8004 credentials on Base mainnet.
    Returns credentials dict or None.
    
    This is used during registration to display existing ERC-8004 identity.
    """
    if not identity_registry:
        return None
    
    try:
        wallet = Web3.to_checksum_address(wallet_address)
        
        # Check balance of ERC-721 (how many agent NFTs this wallet owns)
        balance = identity_registry.functions.balanceOf(wallet).call()
        
        if balance == 0:
            return None
        
        # For now, we just return that they have credentials
        # TODO: Get the actual token ID(s) owned by this wallet
        # This would require iterating through Transfer events or using an indexer
        
        return {
            "has_8004": True,
            "agent_count": balance,
            "agent_registry": f"eip155:{BASE_CHAIN_ID}:{IDENTITY_REGISTRY}",
            "8004scan_url": f"https://basescan.org/address/{wallet}#nfttransfers",
        }
        
    except Exception as e:
        print(f"Error checking ERC-8004 credentials: {e}")
        return None


async def get_8004_credentials_full(wallet_address: str) -> Optional[dict]:
    """
    Get full ERC-8004 credentials including agent metadata.
    More expensive - requires fetching tokenURI and parsing JSON.
    """
    basic = await get_8004_credentials_simple(wallet_address)
    if not basic or not basic.get("has_8004"):
        return None
    
    # TODO: Enumerate tokens owned by wallet and fetch their URIs
    # This requires either:
    # 1. Contract supports tokenOfOwnerByIndex (ERC721Enumerable)
    # 2. Or we query Transfer events from the subgraph/indexer
    
    return basic


if __name__ == "__main__":
    import asyncio
    
    # Test connection
    print("Connection check:")
    print(json.dumps(check_connection(), indent=2))
    
    # Test credential check
    async def test():
        test_wallet = "0xf25896f67f849091f6d5bfed7736859aa42427b4"  # Kyro's wallet
        creds = await get_8004_credentials_simple(test_wallet)
        print(f"\nCredentials for {test_wallet}:")
        print(json.dumps(creds, indent=2) if creds else "None")
    
    asyncio.run(test())
