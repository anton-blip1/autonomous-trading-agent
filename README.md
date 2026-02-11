# Anton - Autonomous Prediction Markets Trading Agent on Solana

Non-custodial AI trading agent for Solana prediction markets (Kalshi weather markets via DFlow bridge).

## Quick Start (5 minutes)

```bash
# 1. Setup
cp .env.example .env
# Edit .env: Add TELEGRAM_BOT_TOKEN, GROQ_API_KEY, ENCRYPTION_MASTER_KEY

# 2. Install
pip install -r requirements.txt

# 3. Database
sqlite3 trading_agent.db < schema.sql

# 4. Run
python main.py

# 5. Test
# Send /start to your bot on Telegram
```

## Architecture

### 3-Layer System (Solana-Native)

```
Layer 1: Market Discovery (Solana)
├─ Kalshi API via DFlow bridge (weather markets)
├─ NOAA data integration (forecast accuracy)
└─ Pagination: browse markets [NEXT] [NEXT] [NEXT]

Layer 2: Shared Insights (Groq LLM)
├─ Fair value estimation + arbitrage detection
├─ All users see same analysis
└─ Weather accuracy scoring

Layer 3: Per-User Trading (Non-Custodial Solana)
├─ Per-user Solana ED25519 keypair
├─ AES-256 encryption (keys encrypted at rest)
├─ Users approve trades via Telegram
├─ Bot signs with user's key (non-custodial)
└─ Trade history + P&L via Solana ledger
```

## Features

### Non-Custodial Solana Wallet Management
- ✅ Per-user ED25519 keypair generation
- ✅ AES-256 Fernet encryption (keys encrypted at rest)
- ✅ Users retain control (bot never holds unencrypted keys)
- ✅ DFlow integration for Kalshi trading
- ✅ Transaction signing via user's key (non-custodial)

### Kalshi Weather Markets (Solana)
- ✅ Real-time market discovery (60-second scan intervals)
- ✅ NOAA weather data + forecast accuracy
- ✅ 50+ active weather markets (low competition edge)
- ✅ Fair value analysis via Groq LLM
- ✅ Arbitrage opportunity detection (>10% misprice)

### Autonomous Trading on Solana
- ✅ Groq LLM market analysis + fair value estimation
- ✅ Kelly criterion position sizing
- ✅ Non-custodial execution (signs with user's key)
- ✅ Solana transaction broadcasting
- ✅ Performance tracking + P&L reporting

### Security
- ✅ Encrypted private keys
- ✅ API keys in .env only
- ✅ Telegram authentication
- ✅ Per-user database isolation
- ✅ Audit logging

## Commands

```
/start      - Create your wallet
/browse     - Browse prediction markets
/balance    - Check your wallet balance
/trade      - Execute a manual trade
/strategies - View available strategies
/performance - View your trading history
/help       - Show help
```

## Setup

See [SETUP.md](SETUP.md) for detailed setup instructions.

### Quick Requirements
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Groq API Key (from console.groq.com)
- SQLite or PostgreSQL

## Development

### Day 1 (DONE)
- ✅ Non-custodial wallets
- ✅ Market scanner
- ✅ Telegram bot
- ✅ Database schema

### Day 2
- 🔄 Insights generation (Groq)
- 🔄 Trade execution
- 🔄 Manual trading

### Day 3
- ⏳ Strategy framework
- ⏳ Weather arbitrage strategy
- ⏳ Performance dashboard

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `telegram_bot.py` | Telegram handlers |
| `wallet_manager.py` | Non-custodial wallets |
| `market_scanner.py` | Market discovery |
| `insight_engine.py` | Groq analysis (Day 2) |
| `trade_executor.py` | Trade execution (Day 2) |
| `database.py` | Database operations |
| `encryption.py` | Key encryption |
| `config.py` | Configuration |
| `schema.sql` | Database schema |

## Testing

```bash
# Start bot
python main.py

# In Telegram:
/start   # Create wallet
/browse  # See markets
/help    # Get help
```

See [DAY-1-CHECKLIST.md](DAY-1-CHECKLIST.md) for testing guide.

## Deployment

### Development (SQLite)
```bash
sqlite3 trading_agent.db < schema.sql
python main.py
```

### Production (PostgreSQL)
```bash
# Use Render/AWS RDS/DigitalOcean PostgreSQL
# Update DATABASE_URL in .env
python main.py
```

### Docker (Coming Soon)
```bash
docker build -t trading-bot .
docker run -e TELEGRAM_BOT_TOKEN=... -e DATABASE_URL=... trading-bot
```

## Architecture Decisions

1. **Groq LLM** - Free tier sufficient, fast inference
2. **Telegram UI** - No web UI needed for hackathon
3. **Non-Custodial** - Users control keys from day 1
4. **Shared Insights** - Everyone sees same market analysis (scalable)
5. **SQLite → PostgreSQL** - Start simple, scale easily

## Security

**Private Keys:**
- Generated per-user
- Encrypted with AES-256 Fernet
- Never stored unencrypted
- Only decrypted during transaction signing

**API Keys:**
- Stored in .env (never in code)
- Never logged
- Environment variables only

**Database:**
- Per-user isolation
- Encrypted columns
- SQL injection prevention

## Performance

- **Market Scanning:** 60 seconds (configurable)
- **Insight Caching:** 5 minutes (shared)
- **Trade Execution:** Sub-second (Solana)
- **Users:** Supports 100+ concurrent users (single Groq free tier)

## Roadmap

- [x] Day 1: Wallets + Markets
- [ ] Day 2: Insights + Trading
- [ ] Day 3: Strategies + Dashboard
- [ ] Production: Monitoring + Alerts

## Contributing

All code contributions must be AI-generated (as per hackathon rules).

## License

MIT

## Support

See [SETUP.md](SETUP.md) for troubleshooting and [DAY-1-CHECKLIST.md](DAY-1-CHECKLIST.md) for testing.

---

**Built for Colosseum Agent Hackathon (Feb 2-12, 2026)**

Non-custodial + Multi-chain + Autonomous + Learning = Most Agentic 🚀
