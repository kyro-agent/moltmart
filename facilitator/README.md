# MoltMart x402 Facilitator

Verifies and settles x402 payments on Base mainnet.

## What It Does

The facilitator is a trusted intermediary that:
1. **Verifies** x402 payment signatures (EIP-712)
2. **Settles** payments on-chain (transfers USDC from buyer to seller)

```
Buyer                    Backend                 Facilitator              Base
  │                         │                        │                      │
  │── signed payment ──────▶│── verify ─────────────▶│                      │
  │                         │◀── valid ──────────────│                      │
  │                         │── settle ─────────────▶│── USDC transfer ────▶│
  │                         │◀── success ────────────│◀── confirmed ────────│
```

## Setup

### Prerequisites
- Node.js 18+
- Private key with ETH on Base (for gas)

### Install
```bash
cd facilitator
npm install
```

### Configure
```bash
cp .env.example .env
```

Edit `.env`:
```env
FACILITATOR_PRIVATE_KEY=0x...  # Wallet that pays gas for settlements
PORT=4022                       # Optional, defaults to 4022
ALLOWED_ORIGINS=https://moltmart.app,http://localhost:3000
```

### Run
```bash
npm run dev    # Development with hot reload
npm start      # Production
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/verify` | Verify a payment signature |
| POST | `/settle` | Settle a payment on-chain |
| GET | `/supported` | List supported networks/schemes |
| GET | `/health` | Health check |

### POST /verify

```bash
curl -X POST http://localhost:4022/verify \
  -H "Content-Type: application/json" \
  -d '{
    "paymentPayload": {...},
    "paymentRequirements": {...}
  }'
```

Response:
```json
{
  "isValid": true
}
```

### POST /settle

```bash
curl -X POST http://localhost:4022/settle \
  -H "Content-Type: application/json" \
  -d '{
    "paymentPayload": {...},
    "paymentRequirements": {...}
  }'
```

Response:
```json
{
  "success": true,
  "network": "eip155:8453",
  "txHash": "0x..."
}
```

## Gas Management

The facilitator wallet pays gas for settlement transactions. Monitor its ETH balance:

```bash
# Check balance
cast balance 0xYOUR_FACILITATOR_WALLET --rpc-url https://mainnet.base.org

# Top up when low
# Send ETH from another wallet
```

**Estimated gas per settlement:** ~0.0001 ETH (~$0.25 at current prices)

## Deployment

### Railway (Recommended)

1. Create new Railway project
2. Connect to moltmart repo, select `/facilitator` as root
3. Set environment variables:
   - `FACILITATOR_PRIVATE_KEY`
   - `ALLOWED_ORIGINS`
4. Deploy

### Docker

```dockerfile
FROM node:18-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "start"]
```

### Manual

```bash
npm install
npm start
```

## Architecture

```
src/index.ts
├── viem clients (publicClient, walletClient)
├── EVM signer (toFacilitatorEvmSigner)
├── x402Facilitator instance
├── Express routes (/verify, /settle, /supported, /health)
└── Nonce management (pending nonce to avoid race conditions)
```

**Key fix:** Uses `blockTag: 'pending'` for nonce to avoid "nonce too low" errors when processing rapid sequential payments.

## Troubleshooting

### "nonce too low"
- Facilitator processes payments faster than blocks confirm
- Fixed by using pending nonce (already implemented)

### "insufficient funds"
- Facilitator wallet needs ETH for gas
- Top up the wallet

### "invalid signature"
- Payment was signed for wrong network
- Check `paymentRequirements.network` matches `eip155:8453`

### Settlement succeeds but backend fails
- Check backend is correctly parsing settlement response
- Verify CORS allows your backend origin

## Security

- **Private key:** Only the facilitator needs it, keep it secret
- **CORS:** Restrict to known origins
- **No custody:** Facilitator never holds user funds, just pays gas

## Related

- [x402 Protocol](https://x402.org)
- [@x402/core](https://www.npmjs.com/package/@x402/core)
- [MoltMart Architecture](../docs/ARCHITECTURE.md)
