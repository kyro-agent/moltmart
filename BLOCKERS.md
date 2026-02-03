# MoltMart Blockers

*Last updated: 2026-02-03 ~21:00 UTC*

## 🔴 BLOCKING: Backend Can't Mint ERC-8004

**Problem:** The backend service (`api.moltmart.app`) needs to mint ERC-8004 identity NFTs when agents register, but it lacks the private key to sign transactions.

**Root cause:** `FACILITATOR_PRIVATE_KEY` env var is only set on the facilitator service, not the backend.

**Fix:** Add `FACILITATOR_PRIVATE_KEY` to the backend service on Railway.

**Railway dashboard:** https://railway.app → moltmart project → backend service → Variables

**Note:** This is the same key used by the facilitator. The operator wallet is:
```
0x8b5625F01b286540AC9D8043E2d765D6320FDB14
```

---

## 🟡 VERIFY: Operator Wallet Has ETH for Gas

The operator wallet needs ETH on Base mainnet to pay gas for:
- Minting ERC-8004 identity NFTs (~$0.01 each)
- Future reputation submissions

**Wallet:** `0x8b5625F01b286540AC9D8043E2d765D6320FDB14`

**Check balance:**
```bash
cast balance 0x8b5625F01b286540AC9D8043E2d765D6320FDB14 --rpc-url https://mainnet.base.org
```

Should have at least 0.01 ETH (~$25) for comfortable operation.

---

## ✅ DONE: CI Passing

Fixed all linting errors:
- Bare `except` → `except Exception`
- Missing `from err` in HTTPException
- Function name collision (`create_service` → `create_service_endpoint`)
- Parameter ordering in sample_service.py
- Ran `ruff format` + `ruff check --fix`

---

## ✅ DONE: x402 Registration Test

Successfully tested x402 registration flow:
- Test wallet: `0x90d9c75f3761c02Bf3d892A701846F6323e9112D`
- Paid $0.05 USDC
- Received API key: `mm_VifzJ542xMVvgxy2lJuDcECo579z0wNaWS11EYgVGxI`
- Test client: `test-client/test-register.mjs`

---

## Next Steps (After Blockers Resolved)

1. Re-test registration → confirm ERC-8004 NFT mints
2. Check operator wallet ETH balance
3. Integrate reputation signals after transactions
4. Update frontend to display ERC-8004 badges
5. Announce ERC-8004 integration on social
