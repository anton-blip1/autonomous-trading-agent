# Telegram Bot Deployment Guide

Complete guide for deploying the autonomous trading agent's Telegram bot for testing and production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Bot Setup](#bot-setup)
3. [Testing (Polling)](#testing-polling)
4. [Production (Webhook)](#production-webhook)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Python Dependencies

```bash
pip install python-telegram-bot[all]==21.0.1
pip install python-dotenv
pip install pytz
pip install aiohttp
```

### 2. Telegram Bot Token

1. Open Telegram and chat with [@BotFather](https://t.me/BotFather)
2. Send: `/newbot`
3. Follow the prompts:
   - Bot name: "Trading Agent Bot"
   - Bot username: "my_trading_agent_bot" (must be unique)
4. Copy the token: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

### 3. Get Your Chat ID

For development/testing, you need your personal Telegram chat ID:

```python
# Run this temporary script
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Your Chat ID: {update.message.chat_id}")
    print(f"Your User ID: {update.message.from_user.id}")

async def main():
    app = Application.builder().token("YOUR_BOT_TOKEN").build()
    app.add_handler(CommandHandler("id", get_id))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

Or use this quick method:
1. Chat with your bot and send any message
2. Visit: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
3. Look for `"chat":{"id":123456789}`

---

## Bot Setup

### 1. Environment Configuration

Create or update `.env`:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789  # Your personal chat ID

# Optional: User preferences
TELEGRAM_MIN_EDGE_PERCENT=3.0
TELEGRAM_MAX_POSITION_SIZE=100
TELEGRAM_DIGEST_TIME=09:00  # HH:MM UTC

# Other configs
ANTHROPIC_API_KEY=your_key
SOLANA_PRIVATE_KEY=your_key
# ... other existing configs
```

### 2. Initialize Database

```bash
python -c "from telegram_bot import TelegramDatabase; TelegramDatabase.init_telegram_tables()"
```

This creates:
- `telegram_users` - User preferences
- `trade_approvals` - Trade approval history
- `telegram_sessions` - Active approval sessions
- `telegram_messages` - Message tracking

---

## Testing (Polling)

Best for development and testing. Uses polling instead of webhooks.

### 1. Start Bot in Polling Mode

```python
# run_telegram_bot.py
import asyncio
import logging
from telegram_bot import telegram_bot

logging.basicConfig(level=logging.INFO)

async def main():
    # Initialize bot
    await telegram_bot.initialize()
    
    # Start polling
    await telegram_bot.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Run It

```bash
python run_telegram_bot.py
```

Expected output:
```
INFO:telegram.ext._application:Application initialized
INFO:telegram.ext._utils:Starting Telegram bot polling...
🤖 Bot polling started...
```

### 3. Test Commands

In Telegram chat with your bot:

```
/start          → Show welcome message
/status         → Check agent status
/portfolio      → View open positions
/trades         → See recent trades
/opportunities  → Top 5 opportunities
/settings       → Your preferences
/help           → Command list
```

### 4. Sending Test Signals

```python
# test_bot_integration.py
import asyncio
import sqlite3
from config import DB_PATH
from telegram_bot import telegram_bot
from datetime import datetime

async def send_test_opportunity():
    """Send a test trade opportunity."""
    
    # Create test signal in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO signals
        (market_id, timestamp, market_fair_value, market_price, edge_percent,
         confidence, decision, suggested_position_size, kelly_fraction, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'BTC_ABOVE_50K',
        datetime.now().isoformat(),
        0.62,
        0.55,
        5.2,          # 5.2% edge
        0.75,         # 75% confidence
        'BUY',
        25.00,        # $25 position
        0.25,
        'Strong technical setup with support confirmed'
    ))
    
    conn.commit()
    signal_id = c.lastrowid
    conn.close()
    
    # Send alert
    await telegram_bot.send_trade_alert(
        signal_id=signal_id,
        market_data={'market_id': 'BTC_ABOVE_50K'},
        requires_approval=True  # Show buttons for approval
    )
    
    print(f"✅ Test signal {signal_id} sent")

if __name__ == "__main__":
    asyncio.run(send_test_opportunity())
```

Run:
```bash
python test_bot_integration.py
```

---

## Production (Webhook)

For production deployment with webhook (high availability).

### 1. Setup Requirements

You need:
- Public domain (e.g., `example.com`)
- SSL certificate (Let's Encrypt free)
- Server to host the webhook (ngrok for testing, AWS/Heroku/DigitalOcean for production)

### 2. Option A: Using ngrok (Quick Testing)

```bash
# Install ngrok: https://ngrok.com/download

# Start ngrok tunnel
ngrok http 8443

# Note the forwarding URL: https://abc123.ngrok.io
```

### 3. Option B: Production Server

Using DigitalOcean, AWS, or Heroku:

```bash
# Example: Heroku
git init
git add .
git commit -m "Deploy bot"
heroku create your-trading-bot
git push heroku main

# Bot will run on: https://your-trading-bot.herokuapp.com/webhook
```

### 4. Setup Webhook

```python
# setup_webhook.py
import asyncio
from telegram_bot import telegram_bot

async def setup_webhook():
    """Register webhook with Telegram."""
    
    # Your public URL (from ngrok or server)
    webhook_url = "https://your-domain.com/webhook"
    
    # SSL certificate path (for verification)
    certificate_path = "/path/to/certificate.pem"  # Optional
    
    # Initialize bot
    await telegram_bot.initialize()
    
    # Register webhook
    await telegram_bot.app.bot.set_webhook(
        url=webhook_url,
        certificate=open(certificate_path, 'rb') if certificate_path else None,
        drop_pending_updates=True
    )
    
    print(f"✅ Webhook registered: {webhook_url}")
    
    # Verify webhook
    info = await telegram_bot.app.bot.get_webhook_info()
    print(f"Status: {info}")

if __name__ == "__main__":
    asyncio.run(setup_webhook())
```

### 5. Webhook Server (FastAPI)

```python
# webhook_server.py
from fastapi import FastAPI, Request
import asyncio
from telegram_bot import telegram_bot

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    """Telegram webhook endpoint."""
    data = await request.json()
    update = Update.de_json(data, telegram_bot.app.bot)
    await telegram_bot.app.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8443, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
```

### 6. SSL Certificate Setup

#### Option A: Let's Encrypt (Free)

```bash
certbot certonly --standalone -d example.com
# Certificates stored in: /etc/letsencrypt/live/example.com/

# Convert to PEM if needed
sudo openssl pkcs12 -export -in /etc/letsencrypt/live/example.com/fullchain.pem \
  -inkey /etc/letsencrypt/live/example.com/privkey.pem \
  -out certificate.p12 -name example.com
```

#### Option B: Self-Signed (Testing)

```bash
openssl req -newkey rsa:2048 -nodes -keyout key.pem -x509 -days 365 -out cert.pem
```

---

## Configuration

### User Preferences

Users can set their own preferences:

```
/settings              → Show current settings
/set_min_edge 2.5      → Change minimum edge to 2.5%
/set_max_size 50       → Max position size $50
/set_digest_time 09:00 → Daily digest at 9 AM
/toggle_digest         → Enable/disable daily digest
```

### System Configuration

Edit `config.py`:

```python
# Auto-execution thresholds
AUTO_EXEC_THRESHOLD_USD = 5       # Auto-execute trades < $5
APPROVAL_THRESHOLD_USD = 50       # Require approval $5-50
# Trades > $50 require manual execution

# Telegram settings
TELEGRAM_UPDATE_INTERVAL_SECONDS = 30  # Check for updates every 30s
ENABLE_TELEGRAM = True                  # Enable/disable bot

# Time settings
TELEGRAM_MIN_EDGE_PERCENT = 3.0        # Global minimum edge
TELEGRAM_MAX_POSITION_SIZE = 100       # Global max position
```

---

## Monitoring

### Check Bot Status

```python
# check_bot_status.py
import asyncio
from telegram_bot import telegram_bot

async def check_status():
    """Check bot status and recent activity."""
    await telegram_bot.initialize()
    
    # Get bot info
    me = await telegram_bot.app.bot.get_me()
    print(f"Bot: {me.username}")
    print(f"ID: {me.id}")
    
    # Get webhook info (if using webhook)
    info = await telegram_bot.app.bot.get_webhook_info()
    print(f"\nWebhook Status:")
    print(f"  URL: {info['url']}")
    print(f"  Pending updates: {info.get('pending_update_count', 0)}")
    
    # Check database
    import sqlite3
    from config import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM trades WHERE DATE(timestamp) = DATE('now')")
    today_trades = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM telegram_users")
    users = c.fetchone()[0]
    
    print(f"\nActivity:")
    print(f"  Users: {users}")
    print(f"  Today's trades: {today_trades}")
    
    conn.close()

asyncio.run(check_status())
```

### Logs

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# View logs
tail -f logs/agent.log | grep TELEGRAM

# Test logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from telegram_bot import logger
logger.info('Test message')
"
```

### Database Monitoring

```sql
-- Check user activity
SELECT user_id, COUNT(*) as approvals 
FROM trade_approvals 
GROUP BY user_id 
ORDER BY approvals DESC;

-- Recent trade approvals
SELECT * FROM trade_approvals 
ORDER BY timestamp DESC LIMIT 10;

-- Message statistics
SELECT content_type, COUNT(*) as count 
FROM telegram_messages 
GROUP BY content_type;
```

---

## Troubleshooting

### Bot not responding

```
❌ Problem: Bot doesn't respond to /start

✅ Solution:
1. Check bot token in .env
2. Verify TELEGRAM_CHAT_ID is set
3. Restart polling: pkill -f "run_telegram_bot.py"
4. Check logs: tail -f logs/agent.log
```

### Rate limiting issues

```
❌ Problem: "Too many commands" message

✅ Solution:
- This is intentional rate limiting (10 commands/minute)
- Wait 60 seconds and try again
- Adjust RATE_LIMIT_COMMANDS in telegram_bot.py if needed
```

### Database errors

```
❌ Problem: "sqlite3.DatabaseError"

✅ Solution:
1. Reinitialize tables:
   python -c "from telegram_bot import TelegramDatabase; 
              TelegramDatabase.init_telegram_tables()"
   
2. Check database path in config.py
3. Verify write permissions on data/ directory
```

### Webhook not receiving updates

```
❌ Problem: Webhook not processing messages

✅ Solution:
1. Verify webhook URL:
   python setup_webhook.py
   
2. Check certificate:
   openssl x509 -in cert.pem -text -noout
   
3. View pending updates:
   python -c "
   import asyncio
   from telegram_bot import telegram_bot
   asyncio.run(telegram_bot.initialize())
   info = asyncio.run(telegram_bot.app.bot.get_webhook_info())
   print(info)
   "
   
4. Reset webhook:
   python -c "
   import asyncio
   from telegram_bot import telegram_bot
   asyncio.run(telegram_bot.app.initialize())
   asyncio.run(telegram_bot.app.bot.delete_webhook())
   "
```

### Testing Message Delivery

```python
# test_message_delivery.py
import asyncio
from telegram_bot import telegram_bot
from telegram_handlers import MessageBuilder

async def test():
    await telegram_bot.initialize()
    
    # Test status message
    msg = MessageBuilder.agent_status()
    print("Message preview:")
    print(msg[:200] + "...")
    
    # Send to chat
    try:
        await telegram_bot.app.bot.send_message(
            chat_id=telegram_bot.chat_id,
            text=msg,
            parse_mode="Markdown"
        )
        print("✅ Message sent successfully")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
```

---

## Performance Tuning

### Memory Usage

```python
# In run_telegram_bot.py
from telegram.ext import Application

# Limit concurrent connections
app.builder().concurrent_updates(2)

# Reduce polling timeout
app.builder().request.read_timeout = 10
```

### Database Optimization

```bash
# Vacuum database to reclaim space
sqlite3 data/trading.db "VACUUM;"

# Create indexes for faster queries
sqlite3 data/trading.db "
CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_market ON signals(market_id);
CREATE INDEX IF NOT EXISTS idx_approvals_user ON trade_approvals(user_id);
"
```

---

## Security Checklist

- [ ] Bot token stored in `.env` (not in code)
- [ ] `TELEGRAM_CHAT_ID` only contains personal/trusted IDs
- [ ] Rate limiting enabled (default: 10 cmd/min)
- [ ] Database encryption for sensitive data
- [ ] SSL certificate valid for webhook
- [ ] Firewall restricts webhook to Telegram IPs
- [ ] Regular backups of `trading.db`
- [ ] Audit log enabled for all approvals
- [ ] Error messages don't leak sensitive info

---

## Next Steps

1. ✅ Test with polling (this guide)
2. ✅ Test all commands in Telegram
3. ✅ Verify trade approval flow
4. ✅ Enable daily digest scheduler
5. ✅ Deploy webhook to production
6. ✅ Monitor logs and activity
7. ✅ Go live with trading! 🚀

---

## Support

For issues:
1. Check logs: `tail -f logs/agent.log`
2. Enable debug mode: `LOG_LEVEL=DEBUG`
3. Check database: `sqlite3 data/trading.db ".schema"`
4. Test manually: `python test_bot_integration.py`

Questions? Check the code comments in `telegram_bot.py` for detailed docstrings.
