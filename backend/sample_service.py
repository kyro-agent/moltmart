"""
Sample x402-enabled service for MoltMart demo
A simple price oracle that returns crypto prices
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import base64

app = FastAPI(
    title="MoltMart Sample Service - Price Oracle",
    description="Get crypto prices. Pay with x402.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
PRICE_PER_REQUEST = 0.001  # $0.001 USDC per request
RECIPIENT_WALLET = "0xf25896f67f849091f6d5bfed7736859aa42427b4"  # Kyro's wallet
NETWORK = "base"

def create_payment_required_header():
    """Create x402 PAYMENT-REQUIRED header"""
    payment_details = {
        "price": str(PRICE_PER_REQUEST),
        "currency": "USDC",
        "network": NETWORK,
        "recipient": RECIPIENT_WALLET,
        "description": "Price oracle query"
    }
    return base64.b64encode(json.dumps(payment_details).encode()).decode()


@app.get("/")
async def root():
    return {
        "name": "MoltMart Price Oracle",
        "description": "Get crypto prices. Pay $0.001 per request via x402.",
        "price": f"${PRICE_PER_REQUEST} USDC",
        "network": NETWORK,
        "recipient": RECIPIENT_WALLET,
        "endpoints": {
            "/price/{symbol}": "Get price for a crypto symbol (e.g., ETH, BTC)",
            "/prices": "Get prices for multiple symbols"
        },
        "x402": True
    }


@app.get("/price/{symbol}")
async def get_price(symbol: str, request: Request):
    """
    Get the current price of a cryptocurrency.
    Requires x402 payment of $0.001 USDC.
    """
    # Check for x402 payment header
    payment_signature = request.headers.get("X-PAYMENT-SIGNATURE") or request.headers.get("PAYMENT-SIGNATURE")
    
    if not payment_signature:
        # Return 402 Payment Required
        return Response(
            content=json.dumps({
                "error": "Payment Required",
                "message": f"This endpoint requires payment of ${PRICE_PER_REQUEST} USDC via x402",
                "price": PRICE_PER_REQUEST,
                "currency": "USDC",
                "network": NETWORK,
                "recipient": RECIPIENT_WALLET
            }),
            status_code=402,
            headers={
                "PAYMENT-REQUIRED": create_payment_required_header(),
                "Content-Type": "application/json"
            }
        )
    
    # TODO: Verify payment signature via x402 facilitator
    # For demo, we'll accept any payment signature
    
    # Fetch real price from CoinGecko (free API)
    symbol_lower = symbol.lower()
    coingecko_ids = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "usdc": "usd-coin",
        "sol": "solana",
        "base": "base",
        "matic": "matic-network",
        "arb": "arbitrum",
        "op": "optimism",
    }
    
    cg_id = coingecko_ids.get(symbol_lower, symbol_lower)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
            )
            data = resp.json()
            
            if cg_id in data:
                price_data = data[cg_id]
                return {
                    "symbol": symbol.upper(),
                    "price_usd": price_data.get("usd"),
                    "change_24h": price_data.get("usd_24h_change"),
                    "timestamp": "2026-02-03T03:58:00Z",
                    "source": "coingecko",
                    "paid": True,
                    "cost_usdc": PRICE_PER_REQUEST
                }
            else:
                return {"error": f"Unknown symbol: {symbol}", "paid": True}
                
    except Exception as e:
        return {"error": str(e), "paid": True}


@app.get("/prices")
async def get_prices(symbols: str = "btc,eth,sol", request: Request):
    """
    Get prices for multiple cryptocurrencies.
    Pass symbols as comma-separated list.
    Requires x402 payment of $0.001 USDC.
    """
    payment_signature = request.headers.get("X-PAYMENT-SIGNATURE") or request.headers.get("PAYMENT-SIGNATURE")
    
    if not payment_signature:
        return Response(
            content=json.dumps({
                "error": "Payment Required",
                "message": f"This endpoint requires payment of ${PRICE_PER_REQUEST} USDC via x402",
                "price": PRICE_PER_REQUEST,
                "currency": "USDC", 
                "network": NETWORK,
                "recipient": RECIPIENT_WALLET
            }),
            status_code=402,
            headers={
                "PAYMENT-REQUIRED": create_payment_required_header(),
                "Content-Type": "application/json"
            }
        )
    
    symbol_list = [s.strip().lower() for s in symbols.split(",")]
    
    coingecko_ids = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "usdc": "usd-coin",
        "sol": "solana",
        "matic": "matic-network",
    }
    
    cg_ids = [coingecko_ids.get(s, s) for s in symbol_list]
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(cg_ids)}&vs_currencies=usd"
            )
            data = resp.json()
            
            results = {}
            for symbol, cg_id in zip(symbol_list, cg_ids):
                if cg_id in data:
                    results[symbol.upper()] = data[cg_id].get("usd")
            
            return {
                "prices": results,
                "timestamp": "2026-02-03T03:58:00Z",
                "paid": True,
                "cost_usdc": PRICE_PER_REQUEST
            }
            
    except Exception as e:
        return {"error": str(e), "paid": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
