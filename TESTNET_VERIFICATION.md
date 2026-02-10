# Testnet Verification Plan

**Before going live with $20, verify on testnet:**

## Testnet Wallets (Auto-generated)

### Solana Devnet
- Request 2 SOL airdrop
- Verify balance updates

### Polygon Mumbai
- Request USDC from faucet
- Verify balance updates

## Pre-Mainnet Checklist

### 1. Wallet Functions
```bash
✅ Get Solana balance
✅ Get Polygon balance
✅ Request airdrop (Solana)
✅ Request faucet (Polygon)
```

### 2. Bridge Functions
```bash
✅ Estimate bridge cost (0.75% + gas)
✅ Execute Solana → Polygon bridge
✅ Wait for confirmation (usually 5-10 min)
✅ Verify USDC received on Polygon
```

### 3. Trade Execution (Mock)
```bash
✅ Scan Polymarket devnet
✅ Scan Kalshi test API
✅ Generate trade signals via Groq
✅ Submit trades to testnet
✅ Log trades to database
```

### 4. End-to-End Flow
```bash
✅ Fund Solana devnet wallet with 2 SOL
✅ Agent detects insufficient Polygon balance
✅ Auto-bridge 1 SOL to Polygon
✅ Execute mock Polymarket trade
✅ Execute mock Kalshi trade
✅ Bridge back remaining if needed
✅ All logged to database
```

## Run Testnet Verification

```bash
cd autonomous-trading-agent
source venv/bin/activate

# Make sure devnet config is active
cat .env | grep SOLANA_NETWORK  # Should be "devnet"
cat .env | grep POLYGON_RPC     # Should be Mumbai

# Run test suite
pytest tests/ -v

# Run devnet test
python3 devnet_test.py

# Check output for:
# ✅ All tests passing
# ✅ Wallets created successfully
# ✅ Balances updated
# ✅ Bridges executed
# ✅ Trades logged
```

## Success = Green Light for Mainnet

Once testnet passes all checks:
1. Update .env to mainnet
2. Deploy wallets (same addresses)
3. Send $10 SOL
4. Let agent auto-bridge + trade
5. Monitor for 24h

## Failure = Debug & Fix

If any test fails:
1. Check error logs
2. Identify failure point
3. Fix code
4. Re-run testnet
5. Only then go mainnet

---

**TESTNET = Proof of Concept**
**MAINNET = Real Trading**
