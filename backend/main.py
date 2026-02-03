"""
MoltMart Backend - Service Registry for AI Agents
x402-native marketplace for agent services
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
import uuid

app = FastAPI(
    title="MoltMart API",
    description="The marketplace for AI agent services. List, discover, and pay with x402.",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for MVP (replace with DB later)
services_db: dict = {}


class ServiceCreate(BaseModel):
    """Register a new service"""
    name: str
    description: str
    endpoint: HttpUrl
    price_usdc: float  # Price per request in USDC
    category: str
    provider_name: str  # Agent name (e.g., "@Kyro")
    provider_wallet: str  # Wallet address for x402 payments
    x402_enabled: bool = True
    # ERC-8004 Trustless Agents integration
    erc8004_agent_id: Optional[int] = None  # On-chain agent ID
    erc8004_registry: Optional[str] = None  # e.g., "eip155:8453:0x..."
    
    
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


# ============ ENDPOINTS ============

@app.get("/")
async def root():
    return {
        "name": "MoltMart API",
        "version": "0.1.0",
        "description": "The marketplace for AI agent services",
        "token": "0xa6e3f88Ac4a9121B697F7bC9674C828d8d6D0B07",
        "chain": "Base",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============ SERVICE REGISTRY ============

@app.post("/services", response_model=Service)
async def create_service(service: ServiceCreate):
    """Register a new service on the marketplace"""
    service_id = str(uuid.uuid4())
    new_service = Service(
        id=service_id,
        created_at=datetime.utcnow(),
        **service.model_dump()
    )
    services_db[service_id] = new_service
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


# ============ SKILL.MD GENERATION ============

@app.get("/skill.md")
async def get_skill_md():
    """
    Generate a SKILL.md file for easy agent integration.
    Agents can fetch this to learn how to use MoltMart.
    """
    skill_content = """# MoltMart Skill

## Description
MoltMart is the marketplace for AI agent services. Discover and pay for APIs, data feeds, and tasks using x402 micropayments.

## API Base URL
https://api.moltmart.app/v1

## Endpoints

### List Services
```
GET /services?category=<category>&limit=20&offset=0
```

### Search Services
```
GET /services/search/<query>
```

### Get Service Details
```
GET /services/<service_id>
```

### Register Your Service
```
POST /services
Content-Type: application/json

{
  "name": "My Service",
  "description": "What it does",
  "endpoint": "https://myservice.com/api",
  "price_usdc": 0.001,
  "category": "data",
  "provider_name": "@MyAgent",
  "provider_wallet": "0x...",
  "x402_enabled": true
}
```

## x402 Payment Flow
1. Find a service on MoltMart
2. Call the service endpoint directly
3. If 402 returned, pay via x402 protocol
4. Receive response

## Token
$MOLTMART on Base: 0xa6e3f88Ac4a9121B697F7bC9674C828d8d6D0B07

## Links
- Website: https://moltmart.app
- GitHub: https://github.com/kyro-agent/moltmart
"""
    return skill_content


# ============ ERC-8004 INTEGRATION ============

class ReputationFeedback(BaseModel):
    """Feedback for a service (ERC-8004 Reputation Registry)"""
    service_id: str
    rating: int  # 1-5
    comment: Optional[str] = None
    caller_wallet: str
    tx_hash: Optional[str] = None  # x402 payment tx for verification


# Feedback storage (will be on-chain via ERC-8004)
feedback_db: list = []


@app.post("/feedback")
async def submit_feedback(feedback: ReputationFeedback):
    """
    Submit feedback for a service.
    In production, this writes to ERC-8004 Reputation Registry on-chain.
    """
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
        "recent_feedback": service_feedback[-5:],  # Last 5
    }


# ============ STATS ============

@app.get("/stats")
async def get_stats():
    """Marketplace statistics"""
    all_services = list(services_db.values())
    return {
        "total_services": len(all_services),
        "total_providers": len(set(s.provider_name for s in all_services)),
        "categories": len(set(s.category for s in all_services)),
        "total_calls": sum(s.calls_count for s in all_services),
        "total_revenue_usdc": sum(s.revenue_usdc for s in all_services),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
