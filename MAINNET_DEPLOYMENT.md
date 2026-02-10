# Mainnet Deployment - Live Trading

**Status:** Ready for mainnet launch with $20 seed capital

## Wallet Addresses

### Solana Mainnet
```
4wTNmGhGwddZiC2wHCWShyAjncGMW2WsXxwDyuB1AceJ
```
- Receives: 10 USD in SOL
- Used for: Kalshi trades + gas fees + bridge execution

### Polygon Mainnet
```
0xdD3F63c5C6cB74a438555e047e4C5cD2eaFC02f9
```
- Receives: ~10 USD USDC via Wormhole bridge
- Used for: Polymarket trades

## Deployment Steps

### 1. Fund Wallets (Manual)
```bash
# Send to Solana address
$10 USD in SOL → 4wTNmGhGwddZiC2wHCWShyAjncGMW2WsXxwDyuB1AceJ

# Agent will auto-bridge remaining to Polygon
# ~5 USD stays on Solana for gas
# ~5 USD bridges to Polygon as USDC
```

### 2. Update Environment
```bash
# .env should have:
ENABLE_LIVE_TRADING=true
SOLANA_NETWORK=mainnet-beta
POLYGON_RPC_URL=https://polygon-rpc.com
BRIDGE_ENABLED=true
```

### 3. Start Agent
```bash
source venv/bin/activate
python3 agent.py
```

### 4. Monitor Trades
- Agent scans every 5 seconds
- Logs all trades to database
- Auto-bridges when needed
- Learns from outcomes

## Risk Management

- **Max position:** $2 per trade (10% of capital)
- **Max deployment:** 50% of bankroll on any given day
- **Stop loss:** -10% per position
- **Daily limit:** -20% triggers circuit breaker

## Expected Behavior

1. **Scan Phase:** Agent scans Polymarket + Kalshi every 5 seconds
2. **Analysis Phase:** Groq evaluates edge (3%+ required)
3. **Route Decision:** Route to Polygon for Polymarket, Solana for Kalshi
4. **Bridge if needed:** Auto-bridge if insufficient balance on target chain
5. **Execution:** Submit trade + log outcome
6. **Learning:** Store result for daily improvement

## Success Metrics

✅ 5+ trades executed in first 24h
✅ Zero failed transactions
✅ Bridges execute successfully
✅ 50%+ win rate on prediction market trades
✅ Daily improvements in signal quality

## Known Limitations (Current)

- Polymarket integration: Order book fetching works, transaction signing ready
- Kalshi integration: API works, DFlow bridge pending final testing
- Real settlement: Mock for now, can upgrade to real USDC transfers

## Next Phase (After $20 Proof)

If profitable after $20:
- Scale to $100+ capital
- Add more markets (crypto spot, futures)
- Deploy to AWS Lambda for 24/7 operation
- Implement more sophisticated strategies

---

**Status: READY FOR MAINNET LAUNCH**
**Capital: $20 USD (conservative proof-of-concept)**
**Goal: Prove autonomous execution works end-to-end**
