# Setup & Run Prediction Markets Bot

## Step 1: Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save the output. You'll need it for `.env`.

## Step 2: Setup Environment (.env)

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token  # Get from @BotFather on Telegram
GROQ_API_KEY=your_groq_key        # Get from https://console.groq.com
ENCRYPTION_MASTER_KEY=your_key    # From Step 1
DATABASE_URL=sqlite:///trading_agent.db
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Initialize Database

### Option A: SQLite (Recommended for Testing)

```bash
sqlite3 trading_agent.db < schema.sql
```

Verify:
```bash
sqlite3 trading_agent.db ".tables"
# Should show: users markets trades market_insights ...
```

### Option B: PostgreSQL (Docker)

```bash
# Start PostgreSQL
docker run --name trading-db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:15

# Wait 5 seconds for startup
sleep 5

# Create schema
psql postgresql://postgres:postgres@localhost:5432/postgres < schema.sql

# Update .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

## Step 5: Run Bot

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

[INIT] Validating configuration...
[INIT] ✅ Configuration valid

[INIT] Starting market scanner...
[INIT] ✅ Market scanner started (background)

[INIT] Setting up Telegram bot...
[INIT] ✅ Telegram bot ready

============================================================
✅ BOT RUNNING
============================================================
Database: sqlite:///trading_agent.db
Market Scan Interval: 60s
Listening for Telegram messages...
Press Ctrl+C to stop
```

## Step 6: Test Bot

Go to Telegram and find your bot. Type `/start`:

```
🎉 Welcome!

✅ Your non-custodial Solana wallet created:

Public Address:
9AQ8P2x...

💰 Send SOL to this address to fund your account.

Commands:
/browse - Browse prediction markets
/balance - Check wallet balance
/help - Get help
```

Try commands:
- `/start` - Create wallet
- `/browse` - See markets
- `/balance` - Check balance
- `/help` - Get help

## Troubleshooting

### "ENCRYPTION_MASTER_KEY not set"

Generate a key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env`:
```
ENCRYPTION_MASTER_KEY=<your_key>
```

### "TELEGRAM_BOT_TOKEN invalid"

1. Go to @BotFather on Telegram
2. Create new bot with `/newbot`
3. Copy token
4. Add to `.env`

### "Database connection failed"

Check DATABASE_URL in `.env`:
- SQLite: `sqlite:///trading_agent.db`
- PostgreSQL: `postgresql://user:pass@localhost:5432/db`

For SQLite, ensure schema is created:
```bash
sqlite3 trading_agent.db < schema.sql
```

### "Groq API error"

Get API key from https://console.groq.com

## Architecture

```
User sends /start
    ↓
Bot generates Solana keypair
    ↓
Private key encrypted (AES-256)
    ↓
Stored in database
    ↓
User gets public address
    ↓
User funds wallet
    ↓
User browses markets (/browse)
    ↓
Bot fetches Kalshi + Polymarket
    ↓
Shows pagination: [NEXT] [NEXT]
```

## What's Working (Day 1)

✅ User wallet creation (non-custodial)
✅ Market fetching (Kalshi + Polymarket)
✅ Market browsing with pagination
✅ Database storage
✅ Telegram commands

## What's Next (Day 2)

🔄 Insights generation (Groq analysis)
🔄 Manual trade execution
🔄 Non-custodial trade signing

## Database

All data stored locally. Users' private keys are encrypted with AES-256.

View database:
```bash
# SQLite
sqlite3 trading_agent.db
> SELECT * FROM users;
> SELECT * FROM markets LIMIT 5;
> .quit

# PostgreSQL
psql postgresql://postgres:postgres@localhost:5432/postgres
> SELECT * FROM users;
> SELECT * FROM markets LIMIT 5;
> \q
```

## File Structure

```
autonomous-trading-agent/
├── main.py                 # Entry point
├── config.py              # Configuration
├── encryption.py          # Key encryption
├── wallet_manager.py      # Non-custodial wallets
├── market_scanner.py      # Fetch markets
├── database.py            # DB operations
├── telegram_bot.py        # Telegram handlers
├── schema.sql             # Database schema
├── requirements.txt       # Dependencies
├── .env                   # Configuration (gitignore)
└── .env.example          # Template
```

## Next Steps

1. ✅ Setup complete
2. Test `/start` command (should create wallet)
3. Test `/browse` command (should show markets)
4. Day 2: Implement insights (Groq analysis)
5. Day 3: Implement trade execution

**Ready? Let's build!**
