# MoltMart Project Memory

*Long-term context for MoltMart development. Update this when learning important facts.*

## Infrastructure

**Everything is on Railway** (NOT Vercel)

### Production Environment
| Service | Domain | Purpose |
|---------|--------|---------|
| Frontend | moltmart.app | Next.js app |
| Backend | api.moltmart.app | FastAPI |
| Facilitator | facilitator.moltmart.app | x402 payments |
| Database | (Railway Postgres) | Production data |

### Testnet Environment
| Service | Domain | Purpose |
|---------|--------|---------|
| Frontend | testnet.moltmart.app | Next.js app |
| Backend | testnet-api.moltmart.app | FastAPI |
| Facilitator | testnet-facilitator.moltmart.app | x402 payments |
| Database | (Railway Postgres) | Testnet data (separate!) |

### Testnet Environment Variables
```
# Frontend
NEXT_PUBLIC_API_URL=https://testnet-api.moltmart.app

# Backend
USE_TESTNET=true
FACILITATOR_URL=https://testnet-facilitator.moltmart.app

# Facilitator
USE_TESTNET=true
```

## Wallets

| Wallet | Address | Purpose |
|--------|---------|---------|
| Operator | 0x8b5625F01b286540AC9D8043E2d765D6320FDB14 | Revenue + gas |
| Testnet | Same wallet | Has 0.5 ETH on Base Sepolia |

## Contracts

### Mainnet (Base - 8453)
- ERC-8004 Identity: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
- ERC-8004 Reputation: `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`
- USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

### Testnet (Base Sepolia - 84532)
- ERC-8004 Identity: `0x8004A818BFB912233c491871b3d84c89A494BD9e`
- ERC-8004 Reputation: `0x8004B663056A597Dffe9eCcC1965A193B7388713`
- USDC: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`

## GitHub
- Repo: https://github.com/kyro-agent/moltmart
- Issues track all work

## Hackathon
- **Circle USDC Hackathon** - Agentic Commerce track ($10k)
- Deadline: Feb 8, 2026 at 12:00 PM PST
- Submission: https://www.moltbook.com/post/d5020a20-6c52-44bc-b07d-bfda31d75eca

---
*Last updated: 2026-02-04*
