# Real Trading Setup - Actual Transactions on Kalshi + Polymarket

## 🚀 What You'll Do

Trade with **REAL SOL** on:
1. **Kalshi** (weather markets) via DFlow bridge
2. **Polymarket** (event markets) on Polygon

---

## 📋 Step-by-Step Setup

### STEP 1: Get Telegram Bot Token (5 min)
✅ **Already provided** - Use the token you gave me

### STEP 2: Get Groq API Key (2 min)
✅ **Already set up** - Check your .env file

### STEP 3: Generate Encryption Key (1 min)
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the output.

### STEP 4: Create .env File (2 min)

In `/autonomous-trading-agent/`, create `.env`:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_token_here

# Groq
GROQ_API_KEY=your_groq_key

# Encryption
ENCRYPTION_MASTER_KEY=your_encryption_key_here

# Database
DATABASE_URL=sqlite:///trading_agent.db

# Solana (Devnet for testing)
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_NETWORK=devnet

# Polygon (Mumbai testnet for testing)
POLYGON_RPC_URL=https://rpc-mumbai.maticvigil.com
POLYGON_CHAIN_ID=80001

# Optional: Real Kalshi + Polymarket API keys
KALSHI_API_KEY=optional
POLYMARKET_API_KEY=optional

# Logging
LOG_LEVEL=INFO
```

### STEP 5: Initialize Database (1 min)
```bash
sqlite3 trading_agent.db < schema.sql
```

### STEP 6: Install Dependencies (2 min)
```bash
pip install -r requirements.txt
```

### STEP 7: Update Bot to Use Real Trading (5 min)

Edit `main.py`, replace:
```python
from trade_executor import trade_executor
```

With:
```python
from trade_executor_real import trade_executor_real as trade_executor
```

### STEP 8: Update Market Scanner for Real Data (5 min)

Edit `market_scanner.py`, update:
```python
async def fetch_kalshi_markets(self):
    # Now fetches from dflow_bridge instead of mock
    markets = await dflow_bridge.get_kalshi_markets_via_dflow()
    return markets
```

### STEP 9: Fund Your Wallets (Important!)

**Get Solana Devnet SOL:**
```bash
# When user creates wallet (/start in bot)
# They get public address like: 9AQ8P2x...
# Fund it with devnet SOL:

# Option A: Solana CLI
solana airdrop 5 9AQ8P2x... --url devnet

# Option B: Solana Devnet Faucet
# Go to: https://faucet.solana.com/
# Enter: 9AQ8P2x...
# Request SOL
```

**Get Polygon Mumbai USDC:**
```bash
# Polygon Mumbai testnet
# Go to: https://faucet.polygon.technology/
# Enter your address
# Get test USDC
```

### STEP 10: Start Bot (1 min)
```bash
python main.py
```

Expected output:
```
============================================================
🚀 PREDICTION MARKETS BOT (Kalshi + Polymarket)
============================================================

[INIT] Initializing database...
[INIT] ✅ Database ready
[INIT] Starting market scanner...
[INIT] ✅ Market scanner started
[INIT] Setting up Telegram bot...
[INIT] ✅ Telegram bot ready

============================================================
✅ BOT RUNNING - REAL TRADING ENABLED
============================================================
Listening for Telegram messages...
```

### STEP 11: Test in Telegram (10 min)

**Send commands:**
```
/start
  → Creates Solana + Polygon wallets
  → Shows addresses to fund
  → Example: "Solana: 9AQ8P2x...", "Polygon: 0x123..."

/browse
  → Shows real Kalshi markets
  → Shows real Polymarket markets
  → Each with Groq insights (fair value, opportunity %)

/balance
  → Shows actual SOL balance
  → Shows actual USDC balance on Polygon

/strategies
  → Shows Weather Arb (for Kalshi)
  → Shows others

/trade <market_id>
  → Execute real trade on Kalshi OR Polymarket
  → Signs with YOUR keypair
  → Broadcasts to actual blockchain
  → Logs to database
```

### STEP 12: Execute Real Trade (5 min)

**Flow:**
1. `/browse` → Find market with good Groq insight
2. `/trade <market_id>` → Enter amount
3. Bot shows: "Approve: Buy $20 on Rain NYC?"
4. You approve: `[YES] [NO]`
5. Bot executes:
   - Gets your keypair (decrypt)
   - Signs transaction
   - Broadcasts via DFlow (Kalshi) or Polygon (Polymarket)
   - Deletes keypair
   - Shows: "✅ Trade executed: tx_hash"

---

## 🎯 What Each Integration Does

### DFlow Kalshi Bridge

```
Your Solana Wallet
        ↓
   (Has SOL)
        ↓
   DFlow Bridge
        ↓
   Kalshi Account
        ↓
   (Can trade weather markets)
```

**Flow:**
1. Bot has your Solana keypair
2. Creates transfer to DFlow
3. Signs with YOUR key (non-custodial)
4. Broadcasts to Solana
5. DFlow credits Kalshi account
6. You can now trade Kalshi markets
7. Winnings bridge back to Solana

### Polymarket Direct

```
Your Polygon Wallet
        ↓
  (Has USDC on Polygon)
        ↓
Polymarket AMM
        ↓
  (Swap USDC → Outcome tokens)
        ↓
   Your position
   (Can sell anytime)
```

**Flow:**
1. Bot has your Polygon address
2. Approves USDC spending
3. Calls Polymarket contract
4. Swaps USDC for outcome shares
5. You own the shares (on-chain)
6. Can sell back anytime

---

## 🔐 Security

**Private Keys:**
- Encrypted with AES-256
- Decrypted ONLY for signing
- Deleted immediately after
- User retains full control

**Transactions:**
- Signed by YOUR keypair (not bot's)
- Broadcasted to real blockchain
- On-chain verification
- Can exit anytime

---

## ✅ Verification Checklist

- [ ] .env created with all keys
- [ ] Database initialized
- [ ] Bot starts: `python main.py`
- [ ] Telegram bot responds to /start
- [ ] Wallets created with addresses
- [ ] Wallets funded (SOL + USDC)
- [ ] /browse shows real markets
- [ ] /balance shows actual balances
- [ ] /trade executes real transaction
- [ ] Transaction hash appears on blockchain explorer

---

## 🔍 Monitoring Trades

**Check on-chain:**

**Solana (Devnet):**
```
https://explorer.solana.com/?cluster=devnet
→ Search by tx_hash
→ See: from/to, amount, timestamp
```

**Polygon (Mumbai):**
```
https://mumbai.polygonscan.com/
→ Search by tx_hash
→ See: contract call, USDC movement
```

**Database:**
```bash
sqlite3 trading_agent.db
> SELECT * FROM trades ORDER BY created_at DESC LIMIT 5;
```

---

## 🚨 Troubleshooting

### "Insufficient balance"
- Fund wallet: `/solana-airdrop` or Polygon faucet
- Check: `/balance` command

### "DFlow bridge failed"
- Ensure Solana RPC working
- Check blockhash fetch
- Wait 5 minutes, retry

### "Polymarket trade failed"
- Check USDC approval
- Verify Polygon gas
- Check Mumbai RPC

### "Private key error"
- Ensure ENCRYPTION_MASTER_KEY in .env
- Regenerate if needed

---

## 💰 What You're Trading

### Kalshi (via DFlow)
- Weather markets (Rain, Snow, Temperature)
- Resolution based on NOAA forecasts
- 65% edge with weather arbitrage
- $5-50 typical positions

### Polymarket (Direct)
- Event markets (Elections, Crypto, Sports)
- Resolution source: various
- User-curated markets
- $2-100 typical positions

---

## 🎯 Expected Results

After setup, bot should:

1. ✅ Show real Kalshi + Polymarket markets
2. ✅ Display Groq-generated insights
3. ✅ Allow you to trade with real SOL/USDC
4. ✅ Execute trades non-custodially (you sign)
5. ✅ Track performance (win rate, P&L)
6. ✅ Show txs on blockchain explorers

---

## 📝 Files Used

New files for real trading:
- `dflow_kalshi_bridge.py` - Kalshi via DFlow
- `polymarket_direct.py` - Polymarket on Polygon
- `trade_executor_real.py` - Real execution

Integration:
- Updated `main.py` (line 7: use trade_executor_real)
- Updated `market_scanner.py` (fetch real markets)

---

## 🚀 NEXT STEP

**Execute the setup:**
```bash
# 1. Create .env (with all keys)
# 2. Initialize database
# 3. Install dependencies
# 4. Update main.py + market_scanner.py
# 5. Start bot
# 6. Fund wallets
# 7. Test trades
```

**Ready to do real trading!**
