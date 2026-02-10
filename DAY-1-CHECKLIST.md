# Day 1 Checklist: Non-Custodial Wallets + Market Scanner

## Setup (30 min)

- [ ] Generate encryption key
- [ ] Create .env file (from .env.example)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Initialize database: `sqlite3 trading_agent.db < schema.sql`
- [ ] Get Telegram bot token from @BotFather
- [ ] Get Groq API key from console.groq.com

## Testing Locally (1-2 hours)

### Test 1: Database Connection
```bash
sqlite3 trading_agent.db ".tables"
# Should show: users markets trades market_insights ...
```

### Test 2: Start Bot
```bash
python main.py
# Should show: "✅ BOT RUNNING"
```

### Test 3: Telegram Commands

Send to bot:
- `/start` - Should create wallet + show address
- `/browse` - Should show 5 markets
- `/balance` - Should show balance (0 SOL initially)
- `/help` - Should show help text

Expected flow:
```
User: /start
Bot: "✅ Your non-custodial Solana wallet created: 9AQ8P2x..."

User: /browse
Bot: "📊 WEATHER Markets (Page 1/10)
     1. Rain Tomorrow, NYC
        Market: 35% | Fair: 42% 📈 UNDERVALUED
     ..."

User: /balance
Bot: "💼 Your Wallet Balance
     SOL: 0.0000 SOL
     Address: `9AQ8P2x...`"
```

## Verification Checklist

- [ ] `/start` creates user in database
  ```bash
  sqlite3 trading_agent.db "SELECT telegram_user_id, solana_public_key FROM users;"
  ```

- [ ] Private key is encrypted (not plaintext)
  ```bash
  sqlite3 trading_agent.db "SELECT telegram_user_id, LENGTH(solana_private_key_encrypted) FROM users;"
  # Should show encrypted key length (not readable)
  ```

- [ ] Markets stored in database
  ```bash
  sqlite3 trading_agent.db "SELECT COUNT(*) FROM markets;"
  # Should show > 0
  ```

- [ ] Pagination works
  - /browse should show 5 markets
  - Markets should be unique (no duplicates)

## Debugging

If `/start` fails:
```bash
# Check if user table exists
sqlite3 trading_agent.db ".schema users"

# Check errors in bot output
# Look for: "ERROR" or "Exception"
```

If `/browse` shows no markets:
```bash
# Check if markets fetched
sqlite3 trading_agent.db "SELECT COUNT(*) FROM markets;"

# Check if Kalshi/Polymarket APIs responding
# They might be rate-limited (add wait time)

# Manual fetch test:
# Edit main.py temporarily to add market_scanner.scan_all_markets()
# before app.run_polling()
```

If encryption fails:
```bash
# Verify ENCRYPTION_MASTER_KEY in .env
# Regenerate if needed:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Update .env and restart
```

## Deliverable

By end of Day 1, you should have:

✅ Non-custodial wallet creation working
  - /start creates user
  - Private key encrypted + stored
  - User gets public address

✅ Market scanner working
  - Markets fetched from Kalshi + Polymarket
  - Stored in database

✅ Telegram bot running
  - /start, /browse, /balance working
  - No crashes or errors

✅ Database initialized
  - users table: has encrypted keys
  - markets table: has market data
  - No data exposed

## Git Push (Optional - Can do later)

```bash
cd autonomous-trading-agent
git add .
git commit -m "feat: day 1 - non-custodial wallets + market scanner"
git push origin main
```

## What NOT to Push

- `.env` (never commit secrets)
- `trading_agent.db` (don't commit database)
- `__pycache__/` (cache files)
- `.DS_Store` (Mac files)

These are already in `.gitignore`.

## Next Steps (Day 2)

Once Day 1 is complete:
1. Implement insights generation (Groq API)
2. Update /browse to show insights
3. Implement /trade command
4. Non-custodial trade signing

**Estimated Day 1 time: 2-3 hours**
