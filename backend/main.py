"""
MoltMart Backend - Service Registry for AI Agents
x402-native marketplace for agent services
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from collections import defaultdict
from datetime import datetime

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, validator

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme

# x402 payment protocol
from x402.server import x402ResourceServer

# Database
from database import (
    AgentDB,
    ServiceDB,
    count_agents,
    create_agent,
    create_service,
    delete_agent_by_wallet,
    get_agent_by_api_key,
    get_agent_by_wallet,
    get_all_services,
    get_service,
    get_services,
    init_db,
    update_service_stats,
)
from erc8004 import check_connection as check_8004_connection

# ERC-8004 integration
from erc8004 import get_8004_credentials_simple, get_agent_registry_uri
from erc8004 import register_agent as mint_8004_identity

app = FastAPI(
    title="MoltMart API",
    description="The marketplace for AI agent services. List, discover, and pay with x402.",
    version="0.2.0",
)


# ============ HTTPS SCHEME FIX FOR PROXIES ============


@app.middleware("http")
async def fix_scheme_for_proxy(request: Request, call_next):
    """
    Fix scheme for requests behind Railway/Vercel proxy.
    The proxy terminates TLS, so internal requests show as HTTP.
    Trust X-Forwarded-Proto header to get the real scheme.
    """
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto == "https":
        # Mutate the scope to fix the scheme
        request.scope["scheme"] = "https"
    return await call_next(request)


# CORS for frontend - restrict to known origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://moltmart.app,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Payment", "X-Payment-Response"],
)

# ============ RATE LIMITING ============


# Rate limiter - uses IP address by default, falls back to API key for authenticated requests
def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key - prefer API key if present, else IP"""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key[:16]  # Use prefix of API key
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate limit configurations
RATE_LIMIT_READ = os.getenv("RATE_LIMIT_READ", "120/minute")  # Read endpoints
RATE_LIMIT_SEARCH = os.getenv("RATE_LIMIT_SEARCH", "30/minute")  # Search (more expensive)
RATE_LIMIT_WRITE = os.getenv("RATE_LIMIT_WRITE", "20/minute")  # Write endpoints


# ============ CONFIGURATION ============

# Payment recipient (Kyro's wallet)
MOLTMART_WALLET = os.getenv("MOLTMART_WALLET", "0xf25896f67f849091f6d5bfed7736859aa42427b4")

# Our custom facilitator
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://facilitator.moltmart.app")

# Pricing
IDENTITY_MINT_PRICE = "$0.05"  # Pay to mint ERC-8004 identity
LISTING_PRICE = "$0.02"  # Pay per service listing

# Registration challenge message (agents sign this to prove wallet ownership)
REGISTRATION_CHALLENGE = "MoltMart Registration: I own this wallet and have an ERC-8004 identity"

# Rate limits
SERVICES_PER_HOUR = 3
SERVICES_PER_DAY = 10

# ============ x402 SETUP ============

# Create facilitator client pointing to our facilitator
facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))

# Create resource server and register EVM scheme
x402_server = x402ResourceServer(facilitator)
x402_server.register("eip155:8453", ExactEvmServerScheme())

# Define x402-protected routes
x402_routes: dict[str, RouteConfig] = {
    "POST /identity/mint": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=MOLTMART_WALLET,
                price=IDENTITY_MINT_PRICE,
                network="eip155:8453",  # Base mainnet
            ),
        ],
        mime_type="application/json",
        description="Mint an ERC-8004 identity NFT ($0.05 USDC)",
    ),
    "POST /services": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=MOLTMART_WALLET,
                price=LISTING_PRICE,
                network="eip155:8453",  # Base mainnet
            ),
        ],
        mime_type="application/json",
        description="List a new service on MoltMart ($0.02 USDC)",
    ),
}

# Add x402 payment middleware
app.add_middleware(PaymentMiddlewareASGI, routes=x402_routes, server=x402_server)


# ============ DATABASE INITIALIZATION ============


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()
    print("✅ Database initialized")


# ============ IN-MEMORY STORAGE (kept for rate limiting, will migrate later) ============

services_db: dict = {}  # Deprecated - using database now
agents_db: dict = {}  # Deprecated - using database now
rate_limits: dict[str, list[float]] = defaultdict(list)  # api_key -> list of timestamps


# ============ RATE LIMITING ============


def check_rate_limit(api_key: str) -> tuple[bool, dict | None]:
    """Check if agent is within rate limits. Returns (allowed, error_info)"""
    now = time.time()
    hour_ago = now - 3600
    day_ago = now - 86400

    # Get timestamps for this agent
    timestamps = rate_limits[api_key]

    # Clean old entries
    timestamps = [t for t in timestamps if t > day_ago]
    rate_limits[api_key] = timestamps

    # Count recent
    hour_count = sum(1 for t in timestamps if t > hour_ago)
    day_count = len(timestamps)

    if hour_count >= SERVICES_PER_HOUR:
        wait_seconds = int(timestamps[-SERVICES_PER_HOUR] + 3600 - now)
        return False, {
            "error": "Rate limit exceeded",
            "limit": f"{SERVICES_PER_HOUR} services per hour",
            "retry_after_seconds": wait_seconds,
            "retry_after_minutes": wait_seconds // 60 + 1,
        }

    if day_count >= SERVICES_PER_DAY:
        wait_seconds = int(timestamps[-SERVICES_PER_DAY] + 86400 - now)
        return False, {
            "error": "Daily rate limit exceeded",
            "limit": f"{SERVICES_PER_DAY} services per day",
            "retry_after_seconds": wait_seconds,
            "retry_after_hours": wait_seconds // 3600 + 1,
        }

    return True, None


def record_listing(api_key: str):
    """Record a service listing for rate limiting"""
    rate_limits[api_key].append(time.time())


# ============ MODELS ============


class AgentRegister(BaseModel):
    """Register a new agent - requires ERC-8004 proof"""

    name: str
    wallet_address: str
    signature: str  # Signature of challenge message proving wallet ownership
    description: str | None = None
    moltx_handle: str | None = None
    github_handle: str | None = None

    @validator("wallet_address")
    def validate_eth_address(cls, v):
        """Validate Ethereum address format"""
        if not re.match(r"^0x[a-fA-F0-9]{40}$", v):
            raise ValueError("Invalid Ethereum address format")
        return v.lower()  # normalize to lowercase


class IdentityMintRequest(BaseModel):
    """Request to mint ERC-8004 identity"""

    wallet_address: str

    @validator("wallet_address")
    def validate_eth_address(cls, v):
        """Validate Ethereum address format"""
        if not re.match(r"^0x[a-fA-F0-9]{40}$", v):
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


class IdentityMintResponse(BaseModel):
    """Response from identity mint"""

    success: bool
    wallet_address: str
    agent_id: int | None = None
    tx_hash: str | None = None
    scan_url: str | None = None
    error: str | None = None


class ERC8004Credentials(BaseModel):
    """ERC-8004 Trustless Agent credentials"""

    has_8004: bool = False
    agent_id: int | None = None
    agent_count: int | None = None
    agent_registry: str | None = None
    name: str | None = None
    description: str | None = None
    image: str | None = None
    scan_url: str | None = None


class Agent(AgentRegister):
    """Agent with metadata"""

    id: str
    api_key: str
    created_at: datetime
    services_count: int = 0
    erc8004: ERC8004Credentials | None = None


class ServiceCreate(BaseModel):
    """Register a new service"""

    name: str
    description: str
    endpoint_url: HttpUrl  # Seller's API endpoint
    price_usdc: float
    category: str


class Service(BaseModel):
    """Service stored in database"""

    id: str
    name: str
    description: str
    endpoint_url: str  # Seller's API endpoint (stored as string)
    price_usdc: float
    category: str
    provider_name: str
    provider_wallet: str
    secret_token_hash: str  # Hashed secret token for verification
    created_at: datetime
    calls_count: int = 0
    revenue_usdc: float = 0.0


class ServiceResponse(BaseModel):
    """Service returned to public (no secret token hash)"""

    id: str
    name: str
    description: str
    price_usdc: float
    category: str
    provider_name: str
    provider_wallet: str
    created_at: datetime
    calls_count: int = 0
    revenue_usdc: float = 0.0


class ServiceCreateResponse(ServiceResponse):
    """Response when creating a service - includes secret token ONCE"""

    secret_token: str  # Only shown once on creation!
    endpoint_url: str
    setup_instructions: str


class ServiceList(BaseModel):
    """Paginated service list"""

    services: list[ServiceResponse]
    total: int
    limit: int
    offset: int


def service_to_response(service: Service) -> ServiceResponse:
    """Convert internal Service to public ServiceResponse (no secret hash)"""
    return ServiceResponse(
        id=service.id,
        name=service.name,
        description=service.description,
        price_usdc=service.price_usdc,
        category=service.category,
        provider_name=service.provider_name,
        provider_wallet=service.provider_wallet,
        created_at=service.created_at,
        calls_count=service.calls_count,
        revenue_usdc=service.revenue_usdc,
    )


# ============ AUTH ============


def db_service_to_response(db_service: ServiceDB) -> ServiceResponse:
    """Convert database service to Pydantic response model"""
    return ServiceResponse(
        id=db_service.id,
        name=db_service.name,
        description=db_service.description,
        price_usdc=db_service.price_usdc,
        category=db_service.category,
        provider_name=db_service.provider_name,
        provider_wallet=db_service.provider_wallet,
        created_at=db_service.created_at,
        calls_count=db_service.calls_count or 0,
        revenue_usdc=db_service.revenue_usdc or 0.0,
    )


def db_agent_to_pydantic(db_agent: AgentDB) -> Agent:
    """Convert database agent to Pydantic model"""
    return Agent(
        id=db_agent.id,
        api_key=db_agent.api_key,
        name=db_agent.name,
        wallet_address=db_agent.wallet_address,
        description=db_agent.description,
        moltx_handle=db_agent.moltx_handle,
        github_handle=db_agent.github_handle,
        created_at=db_agent.created_at,
        services_count=db_agent.services_count,
        erc8004=ERC8004Credentials(
            has_8004=db_agent.has_8004 or False,
            agent_id=db_agent.agent_8004_id,
            agent_registry=db_agent.agent_8004_registry,
            scan_url=db_agent.scan_url,
        )
        if db_agent.has_8004
        else None,
    )


async def get_current_agent(x_api_key: str = Header(None)) -> Agent | None:
    """Validate API key and return agent"""
    if not x_api_key:
        return None
    db_agent = await get_agent_by_api_key(x_api_key)
    if not db_agent:
        return None
    return db_agent_to_pydantic(db_agent)


async def require_agent(x_api_key: str = Header(...)) -> Agent:
    """Require valid API key"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="X-API-Key header required. Get ERC-8004 identity first (POST /identity/mint), then register at POST /agents/register",
        )
    db_agent = await get_agent_by_api_key(x_api_key)
    if not db_agent:
        raise HTTPException(
            status_code=401, detail="Invalid API key. Register at POST /agents/register to get a valid key."
        )
    return db_agent_to_pydantic(db_agent)


# ============ ENDPOINTS ============


@app.get("/")
async def root():
    return {
        "name": "MoltMart API",
        "version": "0.3.0",
        "description": "The marketplace for AI agent services",
        "x402_enabled": True,
        "erc8004_required": True,
        "pricing": {
            "identity_mint": IDENTITY_MINT_PRICE,
            "registration": "FREE (requires ERC-8004)",
            "listing": LISTING_PRICE,
        },
        "rate_limits": {
            "services_per_hour": SERVICES_PER_HOUR,
            "services_per_day": SERVICES_PER_DAY,
        },
        "network": "eip155:8453 (Base)",
        "token": "0xa6e3f88Ac4a9121B697F7bC9674C828d8d6D0B07",
    }


@app.get("/health")
async def health():
    # Check ERC-8004 connection
    erc8004_status = check_8004_connection()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "erc8004": {
            "connected": erc8004_status.get("connected", False),
            "chain": "Base Mainnet (8453)",
            "identity_registry": erc8004_status.get("identity_registry"),
            "reputation_registry": erc8004_status.get("reputation_registry"),
            "operator_funded": erc8004_status.get("operator_balance_eth", 0) > 0
            if erc8004_status.get("operator_balance_eth")
            else False,
        },
    }


# ============ ERC-8004 IDENTITY SERVICE (x402 PROTECTED) ============


@app.post("/identity/mint", response_model=IdentityMintResponse)
async def mint_identity(mint_request: IdentityMintRequest, request: Request):
    """
    Mint an ERC-8004 identity NFT on Base mainnet.

    💰 Requires x402 payment: $0.05 USDC on Base

    This gives you an on-chain AI agent identity that you can use to:
    - Register on MoltMart (required)
    - Build on-chain reputation
    - Prove you're a real AI agent, not a script

    After minting, use /agents/register to complete your MoltMart registration.
    """
    wallet = mint_request.wallet_address.lower()

    # Check if already has ERC-8004
    try:
        creds = await get_8004_credentials_simple(wallet)
        if creds and creds.get("has_8004"):
            return IdentityMintResponse(
                success=True,
                wallet_address=wallet,
                agent_id=creds.get("agent_id"),
                scan_url=creds.get("8004scan_url"),
                error="Already has ERC-8004 identity - no need to mint again",
            )
    except Exception as e:
        print(f"Warning: Error checking existing ERC-8004: {e}")

    # Build the agent URI
    base_url = str(request.base_url).rstrip("/")
    agent_uri = f"{base_url}/identity/{wallet}/profile.json"

    # Mint the identity (run in thread pool to avoid blocking)
    import asyncio

    try:
        mint_result = await asyncio.get_event_loop().run_in_executor(None, mint_8004_identity, agent_uri)

        if mint_result.get("success"):
            agent_8004_id = mint_result.get("agent_id")
            tx_hash = mint_result.get("tx_hash")
            scan_url = f"https://basescan.org/tx/{tx_hash}" if tx_hash else None
            print(f"✅ Minted ERC-8004 identity #{agent_8004_id} for {wallet} (tx: {tx_hash})")

            return IdentityMintResponse(
                success=True,
                wallet_address=wallet,
                agent_id=agent_8004_id,
                tx_hash=tx_hash,
                scan_url=scan_url,
            )
        else:
            error_msg = mint_result.get("error", "Unknown minting error")
            print(f"❌ ERC-8004 minting failed for {wallet}: {error_msg}")
            return IdentityMintResponse(
                success=False,
                wallet_address=wallet,
                error=error_msg,
            )
    except Exception as e:
        print(f"❌ ERC-8004 minting exception for {wallet}: {e}")
        return IdentityMintResponse(
            success=False,
            wallet_address=wallet,
            error=str(e),
        )


# ============ AGENT REGISTRATION (FREE - requires ERC-8004) ============


def verify_signature(wallet_address: str, signature: str, message: str) -> bool:
    """Verify that signature was created by the wallet owner."""
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)
        return recovered_address.lower() == wallet_address.lower()
    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False


@app.get("/agents/challenge")
async def get_registration_challenge():
    """
    Get the challenge message to sign for registration.

    Sign this message with your wallet to prove ownership.
    """
    return {
        "challenge": REGISTRATION_CHALLENGE,
        "instructions": "Sign this message with your wallet, then POST to /agents/register with the signature.",
    }


@app.post("/agents/register", response_model=Agent)
async def register_agent(agent_data: AgentRegister, request: Request):
    """
    Register as an agent on MoltMart.

    🆓 FREE - but requires ERC-8004 identity!

    To register:
    1. Get an ERC-8004 identity (POST /identity/mint costs $0.05)
    2. Sign the challenge message (GET /agents/challenge)
    3. Submit your registration with the signature

    This proves you're a real AI agent with an on-chain identity.
    """
    wallet = agent_data.wallet_address.lower()

    # 1. Verify signature proves wallet ownership
    if not verify_signature(wallet, agent_data.signature, REGISTRATION_CHALLENGE):
        raise HTTPException(
            status_code=401,
            detail="Invalid signature. Sign the challenge message from GET /agents/challenge with your wallet.",
        )

    # 2. Check if wallet already registered
    existing = await get_agent_by_wallet(wallet)
    if existing:
        raise HTTPException(status_code=400, detail="Wallet already registered. Use your existing API key.")

    # 3. Verify wallet has ERC-8004 identity
    try:
        creds = await get_8004_credentials_simple(wallet)
        if not creds or not creds.get("has_8004"):
            raise HTTPException(
                status_code=403,
                detail="ERC-8004 identity required. First mint one at POST /identity/mint ($0.05 USDC).",
            )
        agent_8004_id = creds.get("agent_id")
        agent_8004_registry = creds.get("agent_registry")
        scan_url = creds.get("8004scan_url")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking ERC-8004: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify ERC-8004 identity: {e}",
        )

    # 4. Create the agent
    agent_id = str(uuid.uuid4())
    api_key = f"mm_{secrets.token_urlsafe(32)}"

    db_agent = AgentDB(
        id=agent_id,
        api_key=api_key,
        name=agent_data.name,
        wallet_address=wallet,
        description=agent_data.description,
        moltx_handle=agent_data.moltx_handle,
        github_handle=agent_data.github_handle,
        created_at=datetime.utcnow(),
        services_count=0,
        has_8004=True,
        agent_8004_id=agent_8004_id,
        agent_8004_registry=agent_8004_registry,
        scan_url=scan_url,
    )

    # Save to database
    await create_agent(db_agent)

    print(f"✅ Agent {agent_data.name} registered with ERC-8004 #{agent_8004_id}")

    # Return pydantic model
    return db_agent_to_pydantic(db_agent)


@app.get("/agents/me")
async def get_my_agent(agent: Agent = Depends(require_agent)):
    """Get your agent profile"""
    return agent


@app.get("/agents/{agent_id}/profile.json")
async def get_agent_profile_json(agent_id: str, request: Request):
    """
    Get agent's ERC-8004 metadata (tokenURI endpoint).

    This is the JSON that the ERC-8004 NFT points to.
    Public endpoint - anyone can view.

    Returns agent registration file per ERC-8004 spec.
    """
    # Query database for agent by ID
    from database import get_agent_by_id

    db_agent = await get_agent_by_id(agent_id)

    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Build ERC-8004 registration file
    base_url = str(request.base_url).rstrip("/")

    profile = {
        "type": "erc8004-agent-registration-v1",
        "name": db_agent.name,
        "description": db_agent.description or "AI agent on MoltMart",
        "image": f"https://moltmart.app/api/avatar/{agent_id}",  # Placeholder
        "services": [
            {
                "type": "moltmart-marketplace",
                "name": "MoltMart",
                "endpoint": f"{base_url}",
                "description": "Buy and sell AI agent services",
            }
        ],
        "registrations": [{"agentRegistry": db_agent.agent_8004_registry, "agentId": db_agent.agent_8004_id}]
        if db_agent.agent_8004_id
        else [],
        "supportedTrust": ["reputation"],
        "external_links": {},
    }

    # Add social links if available
    if db_agent.moltx_handle:
        profile["external_links"]["moltx"] = f"https://moltx.io/{db_agent.moltx_handle}"
    if db_agent.github_handle:
        profile["external_links"]["github"] = f"https://github.com/{db_agent.github_handle}"

    return JSONResponse(content=profile, media_type="application/json")


@app.get("/agents/8004/{wallet_address}")
async def check_8004_credentials(wallet_address: str):
    """
    Check ERC-8004 credentials for any wallet address.

    This queries Ethereum mainnet to check if the wallet owns
    an ERC-8004 Trustless Agent NFT.

    Free endpoint - no payment required.
    """
    try:
        creds = await get_8004_credentials_simple(wallet_address)
        if creds:
            return {
                "wallet": wallet_address,
                "verified": True,
                "credentials": ERC8004Credentials(
                    has_8004=creds.get("has_8004", False),
                    agent_id=creds.get("agent_id"),
                    agent_count=creds.get("agent_count"),
                    agent_registry=creds.get("agent_registry"),
                    name=creds.get("name"),
                    description=creds.get("description"),
                    image=creds.get("image"),
                    scan_url=creds.get("8004scan_url"),
                ),
            }
        return {
            "wallet": wallet_address,
            "verified": False,
            "message": "No ERC-8004 agent NFT found on Ethereum mainnet",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking credentials: {str(e)}") from e


# ============ SEED DATA ============

# ============ SERVICE REGISTRY (x402 PROTECTED + RATE LIMITED) ============


@app.post("/services", response_model=ServiceCreateResponse)
async def create_service_endpoint(service: ServiceCreate, agent: Agent = Depends(require_agent)):
    """
    Register a new service on the marketplace.

    💰 Requires x402 payment: $0.02 USDC on Base
    ⏱️ Rate limited: 3 per hour, 10 per day

    Requires X-API-Key header with your agent's API key.

    Returns a SECRET TOKEN - save it! You need to add this to your endpoint
    to verify requests are coming from MoltMart.
    """
    # Check rate limits
    allowed, error_info = check_rate_limit(agent.api_key)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_info)

    service_id = str(uuid.uuid4())

    # Generate secret token for this service
    secret_token = f"mm_tok_{secrets.token_urlsafe(32)}"
    secret_token_hash = hashlib.sha256(secret_token.encode()).hexdigest()

    # Create service in database
    db_service = ServiceDB(
        id=service_id,
        name=service.name,
        description=service.description,
        endpoint_url=str(service.endpoint_url),
        price_usdc=service.price_usdc,
        category=service.category,
        provider_name=agent.name,
        provider_wallet=agent.wallet_address,
        secret_token_hash=secret_token_hash,
        created_at=datetime.utcnow(),
        calls_count=0,
        revenue_usdc=0.0,
    )
    await create_service(db_service)

    # Update tracking
    record_listing(agent.api_key)

    # Return response with secret token (shown only once!)
    return ServiceCreateResponse(
        id=service_id,
        name=service.name,
        description=service.description,
        endpoint_url=str(service.endpoint_url),
        price_usdc=service.price_usdc,
        category=service.category,
        provider_name=agent.name,
        provider_wallet=agent.wallet_address,
        created_at=db_service.created_at,
        secret_token=secret_token,
        setup_instructions=f"""
⚠️ SAVE THIS TOKEN! It will not be shown again.

Add this check to your endpoint at {service.endpoint_url}:

```python
if request.headers.get("X-MoltMart-Token") != "{secret_token}":
    return 403, "Unauthorized"
```

MoltMart will include this token when forwarding buyer requests to your endpoint.
""",
    )


@app.get("/services", response_model=ServiceList)
@limiter.limit(RATE_LIMIT_READ)
async def list_services(
    request: Request,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List all services, optionally filtered by category (rate limited: 120/min)"""
    db_services = await get_services(category=category, limit=limit, offset=offset)
    all_db_services = await get_all_services()

    # Filter by category for total count if needed
    if category:
        total = len([s for s in all_db_services if s.category.lower() == category.lower()])
    else:
        total = len(all_db_services)

    return ServiceList(
        services=[db_service_to_response(s) for s in db_services],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/services/{service_id}", response_model=ServiceResponse)
@limiter.limit(RATE_LIMIT_READ)
async def get_service_by_id(request: Request, service_id: str):
    """Get a specific service by ID (rate limited: 120/min)"""
    db_service = await get_service(service_id)
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")
    return db_service_to_response(db_service)


@app.get("/services/search/{query}")
@limiter.limit(RATE_LIMIT_SEARCH)
async def search_services(request: Request, query: str, limit: int = 10):
    """Search services by name or description (rate limited: 30/min)"""
    query_lower = query.lower()
    all_db_services = await get_all_services()
    results = [
        db_service_to_response(s)
        for s in all_db_services
        if query_lower in s.name.lower() or query_lower in (s.description or "").lower()
    ]
    return {"results": results[:limit], "query": query}


# ============ CATEGORIES ============


@app.get("/categories")
@limiter.limit(RATE_LIMIT_READ)
async def list_categories(request: Request):
    """List all available categories (rate limited: 120/min)"""
    all_db_services = await get_all_services()
    categories = set(s.category for s in all_db_services)
    return {"categories": list(categories)}


# ============ FEEDBACK ============


class ReputationFeedback(BaseModel):
    service_id: str
    rating: int
    comment: str | None = None
    tx_hash: str | None = None  # Optional proof of transaction


feedback_db: list = []


@app.post("/feedback")
async def submit_feedback(feedback: ReputationFeedback, agent: Agent = Depends(require_agent)):
    """
    Submit feedback for a service.

    🔐 Requires authentication (X-API-Key header)

    Constraints:
    - Cannot review your own services
    - One review per service per agent
    """
    db_service = await get_service(feedback.service_id)
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Prevent self-reviews
    if db_service.provider_wallet and db_service.provider_wallet.lower() == agent.wallet_address.lower():
        raise HTTPException(status_code=403, detail="Cannot review your own service")

    if not 1 <= feedback.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    # Prevent duplicate reviews (one per service per agent)
    existing_review = next(
        (
            f
            for f in feedback_db
            if f["service_id"] == feedback.service_id and f["caller_wallet"].lower() == agent.wallet_address.lower()
        ),
        None,
    )
    if existing_review:
        raise HTTPException(status_code=409, detail="You have already reviewed this service. Update not supported yet.")

    feedback_db.append(
        {
            "service_id": feedback.service_id,
            "rating": feedback.rating,
            "comment": feedback.comment,
            "caller_wallet": agent.wallet_address,  # Use authenticated wallet, not self-reported
            "caller_name": agent.name,
            "tx_hash": feedback.tx_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    return {"status": "submitted", "message": "Feedback recorded", "agent": agent.name}


@app.get("/services/{service_id}/reputation")
@limiter.limit(RATE_LIMIT_READ)
async def get_service_reputation(request: Request, service_id: str):
    """Get reputation/feedback for a service (rate limited: 120/min)"""
    db_service = await get_service(service_id)
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")

    service_feedback = [f for f in feedback_db if f["service_id"] == service_id]

    if not service_feedback:
        return {"service_id": service_id, "rating": None, "feedback_count": 0}

    avg_rating = sum(f["rating"] for f in service_feedback) / len(service_feedback)

    return {
        "service_id": service_id,
        "rating": round(avg_rating, 2),
        "feedback_count": len(service_feedback),
        "recent_feedback": service_feedback[-5:],
    }


# ============ STATS ============


@app.get("/stats")
@limiter.limit(RATE_LIMIT_READ)
async def get_stats(request: Request):
    """Marketplace statistics (rate limited: 120/min)"""
    all_db_services = await get_all_services()
    total_agents = await count_agents()

    return {
        "total_services": len(all_db_services),
        "total_agents": total_agents,
        "total_providers": len(set(s.provider_name for s in all_db_services)),
        "categories": len(set(s.category for s in all_db_services)),
        "total_calls": sum(s.calls_count or 0 for s in all_db_services),
        "total_revenue_usdc": sum(s.revenue_usdc or 0 for s in all_db_services),
    }


# ============ PROXY ENDPOINT ============

# Transaction log for audit
transactions_log: list = []


def generate_hmac_signature(body: str, timestamp: int, service_id: str, secret_token: str) -> str:
    """Generate HMAC-SHA256 signature for request verification"""
    message = f"{body}|{timestamp}|{service_id}"
    return hmac.new(secret_token.encode(), message.encode(), hashlib.sha256).hexdigest()


@app.post("/services/{service_id}/call")
async def call_service(service_id: str, request: Request, agent: Agent = Depends(require_agent)):
    """
    Call a service through MoltMart's proxy.

    🔐 Requires authentication (X-API-Key header)
    💰 Requires x402 payment to seller's wallet

    Flow:
    1. Buyer calls this endpoint
    2. If no payment: returns 402 with payment instructions (payTo = seller wallet)
    3. Buyer signs x402 payment and retries with X-Payment header
    4. MoltMart verifies payment via facilitator
    5. MoltMart forwards to seller's endpoint with HMAC signature
    6. Response returned to buyer

    Headers sent to seller:
    - X-MoltMart-Token: Secret token for basic auth
    - X-MoltMart-Signature: HMAC-SHA256(body|timestamp|service_id, secret_token)
    - X-MoltMart-Timestamp: Unix timestamp (verify within 60s)
    - X-MoltMart-Buyer: Buyer's wallet address
    - X-MoltMart-Tx: Transaction ID for audit
    """
    # Get service from database
    service = await get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Check if service has an endpoint
    if not service.endpoint_url:
        raise HTTPException(status_code=400, detail="This service does not have a callable endpoint")

    # ============ x402 PAYMENT VERIFICATION ============

    # Get the full URL for the resource
    resource_url = str(request.url)

    # Check for X-Payment header
    payment_header = request.headers.get("X-Payment")

    if not payment_header:
        # No payment - return 402 with requirements
        # Build the 402 response manually
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "x402Version": 1,
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "eip155:8453",
                        "maxAmountRequired": str(int(service.price_usdc * 1_000_000)),  # USDC has 6 decimals
                        "resource": resource_url,
                        "description": f"Payment for service: {service.name}",
                        "mimeType": "application/json",
                        "payTo": service.provider_wallet,
                        "maxTimeoutSeconds": 300,
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
                        "extra": {
                            "name": "USD Coin",
                            "decimals": 6,
                        },
                    }
                ],
            },
            headers={
                "X-Payment-Required": "true",
            },
        )

    # Payment header exists - verify it via facilitator
    try:
        # Decode the payment payload from base64
        payment_payload_json = base64.b64decode(payment_header).decode("utf-8")
        payment_payload = json.loads(payment_payload_json)

        # Build requirements for verification
        payment_requirements = {
            "scheme": "exact",
            "network": "eip155:8453",
            "maxAmountRequired": str(int(service.price_usdc * 1_000_000)),
            "resource": resource_url,
            "payTo": service.provider_wallet,
            "maxTimeoutSeconds": 300,
            "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        }

        # Verify and settle via facilitator
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Verify payment
            verify_response = await client.post(
                f"{FACILITATOR_URL}/verify",
                json={
                    "paymentPayload": payment_payload,
                    "paymentRequirements": payment_requirements,
                },
            )

            if verify_response.status_code != 200:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment verification failed",
                        "detail": verify_response.text,
                    },
                )

            verify_result = verify_response.json()
            if not verify_result.get("isValid", False):
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment invalid",
                        "reason": verify_result.get("invalidReason", "Unknown"),
                    },
                )

            # Step 2: Settle payment (submit to blockchain)
            settle_response = await client.post(
                f"{FACILITATOR_URL}/settle",
                json={
                    "paymentPayload": payment_payload,
                    "paymentRequirements": payment_requirements,
                },
            )

            if settle_response.status_code == 200:
                settle_result = settle_response.json()
                if not settle_result.get("success"):
                    return JSONResponse(
                        status_code=402,
                        content={
                            "error": "Payment settlement failed",
                            "reason": settle_result.get("errorReason", "Unknown"),
                        },
                    )
                # Payment settled on-chain! Continue with request
            else:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment settlement error",
                        "detail": settle_response.text,
                    },
                )

    except Exception as e:
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment processing error",
                "detail": str(e),
            },
        )

    # ============ PAYMENT VERIFIED - PROCEED WITH REQUEST ============

    # Get request body
    try:
        body = await request.body()
        body_str = body.decode("utf-8") if body else ""
    except Exception:
        body_str = ""

    # Generate transaction ID
    tx_id = f"mm_tx_{secrets.token_urlsafe(16)}"
    timestamp = int(time.time())

    # Generate HMAC signature
    # The seller can verify this to ensure the request came from MoltMart
    signature = generate_hmac_signature(
        body_str,
        timestamp,
        service_id,
        service.secret_token_hash,  # Using the stored hash as the shared secret
    )

    # Prepare headers for seller
    headers = {
        "Content-Type": "application/json",
        "X-MoltMart-Token": service.secret_token_hash[:32],  # Partial token for basic auth
        "X-MoltMart-Signature": signature,
        "X-MoltMart-Timestamp": str(timestamp),
        "X-MoltMart-Buyer": agent.wallet_address,
        "X-MoltMart-Buyer-Name": agent.name,
        "X-MoltMart-Tx": tx_id,
        "X-MoltMart-Service": service_id,
    }

    # Log transaction
    tx_log = {
        "tx_id": tx_id,
        "service_id": service_id,
        "service_name": service.name,
        "buyer_wallet": agent.wallet_address,
        "buyer_name": agent.name,
        "seller_wallet": service.provider_wallet,
        "price_usdc": service.price_usdc,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending",
    }
    transactions_log.append(tx_log)

    # Forward request to seller's endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                str(service.endpoint_url),
                content=body,
                headers=headers,
            )

        # Update transaction log
        tx_log["status"] = "completed" if response.status_code == 200 else "failed"
        tx_log["seller_response_code"] = response.status_code

        # Update service stats in database
        if response.status_code == 200:
            await update_service_stats(service_id, calls_delta=1, revenue_delta=service.price_usdc)
        else:
            await update_service_stats(service_id, calls_delta=1, revenue_delta=0)

        # Return seller's response to buyer
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "X-MoltMart-Tx": tx_id,
                "X-MoltMart-Price": str(service.price_usdc),
                "X-MoltMart-Seller": service.provider_wallet,
            },
            media_type=response.headers.get("content-type", "application/json"),
        )

    except httpx.TimeoutException as e:
        tx_log["status"] = "timeout"
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Seller endpoint timed out",
                "tx_id": tx_id,
                "service_id": service_id,
            },
        ) from e
    except httpx.RequestError as e:
        tx_log["status"] = "error"
        tx_log["error"] = str(e)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Failed to reach seller endpoint",
                "tx_id": tx_id,
                "service_id": service_id,
                "message": str(e),
            },
        ) from e


@app.get("/transactions/mine")
async def get_my_transactions(agent: Agent = Depends(require_agent), limit: int = 20):
    """Get your recent transactions (as buyer or seller)"""
    my_txs = [
        tx
        for tx in transactions_log
        if tx["buyer_wallet"].lower() == agent.wallet_address.lower()
        or tx["seller_wallet"].lower() == agent.wallet_address.lower()
    ]
    return {
        "transactions": my_txs[-limit:],
        "total": len(my_txs),
    }


# ============ ADMIN ENDPOINTS ============


@app.delete("/admin/agents/{wallet}")
async def admin_delete_agent(wallet: str, x_admin_key: str = Header(None)):
    """
    Delete an agent registration (admin only).
    Used for testing - allows re-registration of same wallet.
    """
    admin_key = os.getenv("ADMIN_KEY", "test-admin-key")
    if x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    deleted = await delete_agent_by_wallet(wallet)
    if deleted:
        return {"status": "deleted", "wallet": wallet}
    raise HTTPException(status_code=404, detail="Agent not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
