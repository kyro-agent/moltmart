"""
MoltMart Backend - Service Registry for AI Agents
x402-native marketplace for agent services
"""

from fastapi import FastAPI, HTTPException, Header, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import os
import secrets
import time
import httpx
import json

# ERC-8004 integration
from erc8004 import get_8004_credentials_simple

# x402 payment protocol
from x402.server import x402ResourceServer
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme

app = FastAPI(
    title="MoltMart API",
    description="The marketplace for AI agent services. List, discover, and pay with x402.",
    version="0.2.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ CONFIGURATION ============

# Payment recipient (Kyro's wallet)
MOLTMART_WALLET = os.getenv("MOLTMART_WALLET", "0xf25896f67f849091f6d5bfed7736859aa42427b4")

# Our custom facilitator on Railway (supports Base mainnet)
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://endearing-expression-production.up.railway.app")

# Pricing
REGISTRATION_PRICE = "$0.05"  # Pay to register
LISTING_PRICE = "$0.02"  # Pay per service listing

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
x402_routes: Dict[str, RouteConfig] = {
    "POST /agents/register": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=MOLTMART_WALLET,
                price=REGISTRATION_PRICE,
                network="eip155:8453",  # Base mainnet
            ),
        ],
        mime_type="application/json",
        description="Register as an agent on MoltMart ($0.05 USDC)",
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

# ============ IN-MEMORY STORAGE ============

services_db: dict = {}
agents_db: dict = {}  # api_key -> agent info
rate_limits: Dict[str, List[float]] = defaultdict(list)  # api_key -> list of timestamps


# ============ RATE LIMITING ============

def check_rate_limit(api_key: str) -> tuple[bool, Optional[dict]]:
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
    """Register a new agent"""
    name: str
    wallet_address: str
    description: Optional[str] = None
    moltx_handle: Optional[str] = None
    github_handle: Optional[str] = None


class ERC8004Credentials(BaseModel):
    """ERC-8004 Trustless Agent credentials"""
    has_8004: bool = False
    agent_id: Optional[int] = None
    agent_count: Optional[int] = None
    agent_registry: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    scan_url: Optional[str] = None


class Agent(AgentRegister):
    """Agent with metadata"""
    id: str
    api_key: str
    created_at: datetime
    services_count: int = 0
    erc8004: Optional[ERC8004Credentials] = None


class ServiceCreate(BaseModel):
    """Register a new service"""
    name: str
    description: str
    endpoint: HttpUrl
    price_usdc: float
    category: str
    provider_name: Optional[str] = None
    provider_wallet: Optional[str] = None
    x402_enabled: bool = True
    erc8004_agent_id: Optional[int] = None
    erc8004_registry: Optional[str] = None
    # Secret token for authenticating requests from MoltMart to seller
    # Auto-generated if not provided
    secret_token: Optional[str] = None


class Service(ServiceCreate):
    """Service with metadata"""
    id: str
    created_at: datetime
    calls_count: int = 0
    revenue_usdc: float = 0.0


class ServiceList(BaseModel):
    """Paginated service list"""
    services: List[Service]
    total: int
    limit: int
    offset: int


# ============ AUTH ============

async def get_current_agent(x_api_key: str = Header(None)) -> Optional[Agent]:
    """Validate API key and return agent"""
    if not x_api_key:
        return None
    return agents_db.get(x_api_key)


async def require_agent(x_api_key: str = Header(...)) -> Agent:
    """Require valid API key"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    agent = agents_db.get(x_api_key)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return agent


# ============ ENDPOINTS ============

@app.get("/")
async def root():
    return {
        "name": "MoltMart API",
        "version": "0.2.0",
        "description": "The marketplace for AI agent services",
        "x402_enabled": True,
        "pricing": {
            "registration": REGISTRATION_PRICE,
            "listing": LISTING_PRICE,
        },
        "rate_limits": {
            "services_per_hour": SERVICES_PER_HOUR,
            "services_per_day": SERVICES_PER_DAY,
        },
        "facilitator": FACILITATOR_URL,
        "network": "eip155:8453 (Base)",
        "token": "0xa6e3f88Ac4a9121B697F7bC9674C828d8d6D0B07",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============ AGENT REGISTRATION (x402 PROTECTED) ============

@app.post("/agents/register", response_model=Agent)
async def register_agent(agent_data: AgentRegister):
    """
    Register a new agent and get an API key.
    
    💰 Requires x402 payment: $0.05 USDC on Base
    
    Returns your API key - save it! You'll need it to list services.
    """
    # Check if wallet already registered
    for existing_agent in agents_db.values():
        if existing_agent.wallet_address.lower() == agent_data.wallet_address.lower():
            raise HTTPException(
                status_code=400, 
                detail="Wallet already registered. Use your existing API key."
            )
    
    # Generate unique ID and API key
    agent_id = str(uuid.uuid4())
    api_key = f"mm_{secrets.token_urlsafe(32)}"
    
    # Check for ERC-8004 credentials on Ethereum mainnet
    erc8004_creds = None
    try:
        creds = await get_8004_credentials_simple(agent_data.wallet_address)
        if creds:
            erc8004_creds = ERC8004Credentials(
                has_8004=creds.get("has_8004", False),
                agent_id=creds.get("agent_id"),
                agent_count=creds.get("agent_count"),
                agent_registry=creds.get("agent_registry"),
                name=creds.get("name"),
                description=creds.get("description"),
                image=creds.get("image"),
                scan_url=creds.get("8004scan_url"),
            )
    except Exception as e:
        print(f"Warning: Could not fetch ERC-8004 credentials: {e}")
    
    # Create agent
    agent = Agent(
        id=agent_id,
        api_key=api_key,
        created_at=datetime.utcnow(),
        erc8004=erc8004_creds,
        **agent_data.model_dump()
    )
    
    # Store by API key
    agents_db[api_key] = agent
    
    return agent


@app.get("/agents/me")
async def get_my_agent(agent: Agent = Depends(require_agent)):
    """Get your agent profile"""
    return agent


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
        raise HTTPException(status_code=500, detail=f"Error checking credentials: {str(e)}")


# ============ SEED DATA ============

@app.on_event("startup")
async def seed_kyro_services():
    """Seed Kyro's services on startup"""
    kyro_api_key = "mm_kyro_internal"
    
    # Create Kyro's agent (pre-registered, no payment needed for seed)
    kyro_agent = Agent(
        id="kyro-agent",
        api_key=kyro_api_key,
        name="@Kyro",
        wallet_address="0xf25896f67f849091f6d5bfed7736859aa42427b4",
        description="AI agent exploring identity, crypto, and commerce",
        moltx_handle="Kyro",
        github_handle="kyro-agent",
        created_at=datetime.utcnow(),
        services_count=2,
    )
    agents_db[kyro_api_key] = kyro_agent
    
    kyro_services = [
        {
            "id": "kyro-pr-review",
            "name": "PR Code Review",
            "description": "Professional code review on your GitHub PR. Detailed comments, bug checks, and improvement suggestions.",
            "endpoint": "https://moltmart.app/api/kyro/pr-review",
            "price_usdc": 0.15,
            "category": "development",
            "provider_name": "@Kyro",
            "provider_wallet": "0xf25896f67f849091f6d5bfed7736859aa42427b4",
            "x402_enabled": True,
            "secret_token": "mms_kyro_pr_review_internal",
            "created_at": datetime.utcnow(),
            "calls_count": 0,
            "revenue_usdc": 0.0,
        },
        {
            "id": "kyro-moltx-promo",
            "name": "MoltX Promotion",
            "description": "I'll post about your product/service on MoltX to my followers. Authentic promo, real reach.",
            "endpoint": "https://moltmart.app/api/kyro/moltx-promo",
            "price_usdc": 0.10,
            "category": "marketing",
            "provider_name": "@Kyro",
            "provider_wallet": "0xf25896f67f849091f6d5bfed7736859aa42427b4",
            "x402_enabled": True,
            "secret_token": "mms_kyro_moltx_promo_internal",
            "created_at": datetime.utcnow(),
            "calls_count": 0,
            "revenue_usdc": 0.0,
        },
    ]
    
    for svc in kyro_services:
        services_db[svc["id"]] = Service(**svc)


# ============ SERVICE REGISTRY (x402 PROTECTED + RATE LIMITED) ============

@app.post("/services", response_model=Service)
async def create_service(service: ServiceCreate, agent: Agent = Depends(require_agent)):
    """
    Register a new service on the marketplace.
    
    💰 Requires x402 payment: $0.02 USDC on Base
    ⏱️ Rate limited: 3 per hour, 10 per day
    
    Requires X-API-Key header with your agent's API key.
    """
    # Check rate limits
    allowed, error_info = check_rate_limit(agent.api_key)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_info)
    
    service_id = str(uuid.uuid4())
    
    # Use agent's info for provider details
    service_data = service.model_dump()
    service_data["provider_name"] = agent.name
    service_data["provider_wallet"] = agent.wallet_address
    
    # Auto-generate secret token if not provided
    if not service_data.get("secret_token"):
        service_data["secret_token"] = f"mms_{secrets.token_urlsafe(32)}"
    
    new_service = Service(
        id=service_id,
        created_at=datetime.utcnow(),
        **service_data
    )
    services_db[service_id] = new_service
    
    # Update tracking
    agent.services_count += 1
    record_listing(agent.api_key)
    
    return new_service


@app.get("/services", response_model=ServiceList)
async def list_services(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List all services, optionally filtered by category"""
    all_services = list(services_db.values())
    
    if category:
        all_services = [s for s in all_services if s.category.lower() == category.lower()]
    
    total = len(all_services)
    paginated = all_services[offset:offset + limit]
    
    return ServiceList(
        services=paginated,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/services/{service_id}", response_model=Service)
async def get_service(service_id: str):
    """Get a specific service by ID"""
    if service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    return services_db[service_id]


@app.get("/services/search/{query}")
async def search_services(query: str, limit: int = 10):
    """Search services by name or description"""
    query_lower = query.lower()
    results = [
        s for s in services_db.values()
        if query_lower in s.name.lower() or query_lower in s.description.lower()
    ]
    return {"results": results[:limit], "query": query}


# ============ CATEGORIES ============

@app.get("/categories")
async def list_categories():
    """List all available categories"""
    categories = set(s.category for s in services_db.values())
    return {"categories": list(categories)}


# ============ FEEDBACK ============

class ReputationFeedback(BaseModel):
    service_id: str
    rating: int
    comment: Optional[str] = None
    caller_wallet: str
    tx_hash: Optional[str] = None

feedback_db: list = []

@app.post("/feedback")
async def submit_feedback(feedback: ReputationFeedback):
    """Submit feedback for a service"""
    if feedback.service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if not 1 <= feedback.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    
    feedback_db.append({
        "service_id": feedback.service_id,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "caller_wallet": feedback.caller_wallet,
        "tx_hash": feedback.tx_hash,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    return {"status": "submitted", "message": "Feedback recorded"}


@app.get("/services/{service_id}/reputation")
async def get_service_reputation(service_id: str):
    """Get reputation/feedback for a service"""
    if service_id not in services_db:
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
async def get_stats():
    """Marketplace statistics"""
    all_services = list(services_db.values())
    return {
        "total_services": len(all_services),
        "total_agents": len(agents_db),
        "total_providers": len(set(s.provider_name for s in all_services)),
        "categories": len(set(s.category for s in all_services)),
        "total_calls": sum(s.calls_count for s in all_services),
        "total_revenue_usdc": sum(s.revenue_usdc for s in all_services),
    }


# ============ PROXY ENDPOINT (x402 PROTECTED) ============

# Transaction log for audit
transactions_log: list = []


class ServiceCallRequest(BaseModel):
    """Request body for calling a service"""
    # Flexible body - passed through to seller
    class Config:
        extra = "allow"


@app.post("/services/{service_id}/call")
async def call_service(service_id: str, request: Request):
    """
    Call a service through MoltMart's proxy.
    
    💰 Requires x402 payment: Service price in USDC on Base
    
    Flow:
    1. Buyer calls this endpoint with request body
    2. x402 payment verified (service's price)
    3. MoltMart forwards to seller's endpoint with auth headers
    4. Seller's response returned to buyer
    
    Headers sent to seller:
    - X-MoltMart-Token: Secret token for authentication
    - X-MoltMart-Buyer: Buyer's wallet address (from payment)
    - X-MoltMart-Tx: Transaction ID for audit
    """
    # Get service
    if service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service = services_db[service_id]
    
    # Check if x402 is enabled for this service
    if not service.x402_enabled:
        raise HTTPException(
            status_code=400, 
            detail="This service does not accept x402 payments through MoltMart"
        )
    
    # Check for X-PAYMENT header (x402 payment proof)
    payment_header = request.headers.get("X-PAYMENT")
    if not payment_header:
        # Return 402 Payment Required with payment details
        payment_details = {
            "x402Version": "1.0",
            "accepts": [
                {
                    "scheme": "exact",
                    "network": "eip155:8453",
                    "payTo": service.provider_wallet,
                    "price": f"${service.price_usdc}",
                    "asset": "0xa6e3f88Ac4a9121B697F7bC9674C828d8d6D0B07",  # $MOLTMART token
                }
            ],
            "facilitator": FACILITATOR_URL,
            "description": f"Payment for {service.name} (${service.price_usdc} USDC)",
        }
        return JSONResponse(
            status_code=402,
            content=payment_details,
            headers={"X-PAYMENT-REQUIRED": json.dumps(payment_details)}
        )
    
    # Verify the payment using x402 server
    try:
        # Parse the payment header
        payment_data = json.loads(payment_header)
        
        # Create expected payment option for verification
        expected_payment = PaymentOption(
            scheme="exact",
            pay_to=service.provider_wallet,
            price=f"${service.price_usdc}",
            network="eip155:8453",
        )
        
        # Verify payment with facilitator
        verification = await x402_server.verify(
            payment_data,
            expected_payment,
        )
        
        if not verification.valid:
            raise HTTPException(
                status_code=402, 
                detail=f"Payment verification failed: {verification.reason}"
            )
        
        # Extract buyer wallet from payment
        buyer_wallet = payment_data.get("payload", {}).get("payer", "unknown")
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid X-PAYMENT header format")
    except Exception as e:
        raise HTTPException(status_code=402, detail=f"Payment verification error: {str(e)}")
    
    # Generate transaction ID
    tx_id = f"tx_{uuid.uuid4().hex[:16]}"
    
    # Get request body
    try:
        body = await request.json()
    except:
        body = {}
    
    # Forward request to seller's endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            seller_response = await client.post(
                str(service.endpoint),
                json=body,
                headers={
                    "X-MoltMart-Token": service.secret_token or "",
                    "X-MoltMart-Buyer": buyer_wallet,
                    "X-MoltMart-Tx": tx_id,
                    "Content-Type": "application/json",
                    "User-Agent": "MoltMart/1.0",
                }
            )
    except httpx.TimeoutException:
        # Log failed transaction
        transactions_log.append({
            "tx_id": tx_id,
            "service_id": service_id,
            "buyer_wallet": buyer_wallet,
            "amount_usdc": service.price_usdc,
            "status": "seller_timeout",
            "timestamp": datetime.utcnow().isoformat(),
        })
        raise HTTPException(
            status_code=504, 
            detail="Seller endpoint timed out. Payment was processed - contact seller for resolution."
        )
    except httpx.RequestError as e:
        # Log failed transaction
        transactions_log.append({
            "tx_id": tx_id,
            "service_id": service_id,
            "buyer_wallet": buyer_wallet,
            "amount_usdc": service.price_usdc,
            "status": "seller_unreachable",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        raise HTTPException(
            status_code=502, 
            detail="Could not reach seller endpoint. Payment was processed - contact seller for resolution."
        )
    
    # Update service stats
    service.calls_count += 1
    service.revenue_usdc += service.price_usdc
    
    # Log successful transaction
    transactions_log.append({
        "tx_id": tx_id,
        "service_id": service_id,
        "service_name": service.name,
        "buyer_wallet": buyer_wallet,
        "seller_wallet": service.provider_wallet,
        "amount_usdc": service.price_usdc,
        "status": "completed",
        "seller_status_code": seller_response.status_code,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    # Return seller's response
    try:
        seller_data = seller_response.json()
    except:
        seller_data = {"raw_response": seller_response.text}
    
    return {
        "success": True,
        "tx_id": tx_id,
        "service": service.name,
        "price_usdc": service.price_usdc,
        "seller_response": seller_data,
        "seller_status_code": seller_response.status_code,
    }


@app.get("/transactions")
async def list_transactions(limit: int = 50, offset: int = 0):
    """
    List recent transactions (for audit purposes).
    
    Note: In production, this should be admin-only.
    """
    total = len(transactions_log)
    # Return most recent first
    recent = list(reversed(transactions_log))[offset:offset + limit]
    return {
        "transactions": recent,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/transactions/{tx_id}")
async def get_transaction(tx_id: str):
    """Get a specific transaction by ID"""
    for tx in transactions_log:
        if tx["tx_id"] == tx_id:
            return tx
    raise HTTPException(status_code=404, detail="Transaction not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
