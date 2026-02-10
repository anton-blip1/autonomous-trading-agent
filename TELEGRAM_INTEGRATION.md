# Telegram Bot Integration Guide

Integration points for connecting the autonomous trading agent to the Telegram bot.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│       Autonomous Trading Agent                   │
│  (agent.py - Main loop)                         │
└────────────┬────────────────────────────────────┘
             │
             ├─→ Detects trade opportunity
             ├─→ Creates signal in DB
             └─→ Calls telegram bot methods
             
┌────────────────────────────────────────────────┐
│       Telegram Bot (telegram_bot.py)             │
│  ┌──────────────────────────────────────────┐  │
│  │ Commands:  /start, /status, /portfolio   │  │
│  │ Buttons:   ✅ Approve, ❌ Reject, 📊 Details│
│  │ Alerts:    Trade notifications           │  │
│  │ Digest:    Daily market summary          │  │
│  └──────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────┘
             │
             ├─→ Sends to Telegram API
             └─→ Reads user approvals from DB
             
┌────────────────────────────────────────────────┐
│       SQLite Database                           │
│  trades | signals | positions | users           │
│  approvals | messages | sessions                │
└────────────────────────────────────────────────┘
```

## Integration Checklist

### ✅ Phase 1: Bot Foundation (COMPLETE)

- [x] `telegram_bot.py` - Main bot class with all commands
- [x] `telegram_handlers.py` - Message builders and handlers
- [x] `telegram_scheduler.py` - Daily digest scheduler
- [x] Database schema extensions (telegram_users, trade_approvals, etc.)
- [x] User preference management
- [x] Rate limiting and security

### ✅ Phase 2: Testing & Deployment (COMPLETE)

- [x] `test_telegram_bot.py` - Comprehensive test suite
- [x] `run_telegram_bot.py` - Main entry point
- [x] `TELEGRAM_DEPLOYMENT.md` - Full deployment guide
- [x] `TELEGRAM_README.md` - User guide
- [x] `TELEGRAM_INTEGRATION.md` - This file

### ⚙️ Phase 3: Integration with Agent (IN PROGRESS)

- [ ] Agent calls bot when opportunity detected
- [ ] Agent reads approvals from database
- [ ] Agent waits for user response when needed
- [ ] Bot notifies agent when trade executes
- [ ] Agent updates position status in database

## How to Call from Agent

### 1. When Trade Opportunity Detected

In `agent.py`, after generating a signal:

```python
import asyncio
from telegram_bot import telegram_bot

async def execute_trade_decision(signal_id: int, signal_data: dict):
    """Execute trade and notify via Telegram."""
    
    market_id = signal_data['market_id']
    size = signal_data['suggested_position_size']
    edge = signal_data['edge_percent']
    
    # Determine if approval needed
    requires_approval = 5 <= size <= 50  # $5-50 range
    
    # Auto-execute if size < $5
    if size < 5:
        logger.info(f"Auto-executing trade: ${size} (below threshold)")
        await execute_trade(signal_id, market_data)
    
    # Send to Telegram for approval
    elif requires_approval:
        logger.info(f"Sending to user for approval: ${size}")
        await telegram_bot.send_trade_alert(
            signal_id=signal_id,
            market_data=signal_data,
            requires_approval=True
        )
        
        # Wait for user decision (check database every 30 seconds)
        approval = await wait_for_approval(signal_id, timeout=3600)  # 1 hour timeout
        
        if approval == 'approved':
            await execute_trade(signal_id, market_data)
        elif approval == 'rejected':
            logger.info("Trade rejected by user")
        else:
            logger.info("Trade approval expired")
    
    # Manual execution for large trades
    else:
        logger.info(f"Large trade (${size}) - manual execution only")
        await telegram_bot.send_trade_alert(
            signal_id=signal_id,
            market_data=signal_data,
            requires_approval=False
        )

async def wait_for_approval(signal_id: int, timeout: int = 3600) -> str:
    """Wait for user to approve/reject trade."""
    import sqlite3
    from config import DB_PATH
    from datetime import datetime, timedelta
    
    start_time = datetime.now()
    check_interval = 30  # Check every 30 seconds
    
    while (datetime.now() - start_time).seconds < timeout:
        # Check database for approval
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT status FROM trade_approvals
            WHERE signal_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (signal_id,))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            status = result[0]
            if status in ['approved', 'rejected']:
                return status
        
        # Wait before checking again
        await asyncio.sleep(check_interval)
    
    return 'expired'
```

### 2. When Trade Executes

After executing the trade on-chain:

```python
from telegram_bot import telegram_bot

async def on_trade_executed(trade_id: int):
    """Notify user when trade is executed."""
    await telegram_bot.send_trade_execution(trade_id)
```

### 3. When Position Closes

When monitoring and closing positions:

```python
from telegram_bot import telegram_bot

async def on_position_closed(position_id: int):
    """Notify user when position closes with P&L."""
    await telegram_bot.send_position_closed(position_id)
```

### 4. In Main Agent Loop

Add to your main `agent.py`:

```python
import asyncio
from telegram_bot import telegram_bot
from telegram_scheduler import DigestScheduler, PerformanceSummaryScheduler

async def main_agent_loop():
    """Main agent loop with Telegram integration."""
    
    # Initialize Telegram bot
    if ENABLE_TELEGRAM:
        await telegram_bot.initialize()
        
        # Start schedulers in background
        digest_scheduler = DigestScheduler(telegram_bot)
        perf_scheduler = PerformanceSummaryScheduler(telegram_bot)
        
        # Run bot and schedulers concurrently
        bot_task = asyncio.create_task(telegram_bot.start_polling())
        digest_task = asyncio.create_task(digest_scheduler.start())
        perf_task = asyncio.create_task(perf_scheduler.start())
    
    # Main agent loop
    while True:
        try:
            # Scan markets
            signals = await scan_markets()
            
            # Process each signal
            for signal in signals:
                signal_id = db.add_signal(signal)
                
                # Execute/approve trade
                await execute_trade_decision(signal_id, signal)
            
            # Sleep before next scan
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            logger.info("Stopping agent...")
            if ENABLE_TELEGRAM:
                await telegram_bot.stop()
                digest_scheduler.stop()
                perf_scheduler.stop()
            break
        
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    from config import ENABLE_TELEGRAM
    asyncio.run(main_agent_loop())
```

## Database Integration Points

### Reading from Database

Agent reads approvals to decide whether to execute:

```python
import sqlite3
from config import DB_PATH

def get_trade_approval(signal_id: int) -> Optional[str]:
    """Get user's approval status for a trade."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT decision FROM trade_approvals
        WHERE signal_id = ? 
        ORDER BY timestamp DESC LIMIT 1
    """, (signal_id,))
    
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None
```

### Writing to Database

Bot writes approvals when user clicks buttons:

```python
# Already implemented in telegram_bot.py
# But here's the logic:

c.execute("""
    INSERT INTO trade_approvals
    (user_id, signal_id, status, decision, timestamp)
    VALUES (?, ?, 'approved', 'APPROVE', ?)
""", (user_id, signal_id, datetime.now().isoformat()))
```

### Reading Opportunities

Bot reads signals to show in opportunities command:

```python
# Already implemented in telegram_handlers.py
c.execute("""
    SELECT signal_id, market_id, edge_percent, confidence, 
           decision, suggested_position_size
    FROM signals
    WHERE executed = 0 AND decision != 'PASS'
    ORDER BY (edge_percent * confidence) DESC
    LIMIT 5
""")
```

## Event Flow Diagrams

### Trade Approval Flow

```
AGENT                          TELEGRAM BOT                    USER
  │                                 │                          │
  ├─ Detect opportunity             │                          │
  ├─ Create signal in DB            │                          │
  │                                 │                          │
  └─ send_trade_alert()─────────────>                          │
                                    │                          │
                                    ├─ Format message          │
                                    ├─ Create buttons          │
                                    └─ Send to Telegram────────>
                                                               │
                                    <─── User clicks Approve ──┤
                                    │                          │
                                    ├─ Record approval in DB   │
                                    ├─ Update message          │
                                    └─ Return "approved"       │
  <───── wait_for_approval() ────────                          │
    gets "approved"                 │                          │
  │                                 │                          │
  ├─ Execute trade                  │                          │
  └─ send_trade_execution()────────>│                          │
                                    │                          │
                                    └─ Send execution alert────>
```

### Daily Digest Flow

```
SCHEDULER                      TELEGRAM BOT                    USER
  │                                 │                          │
  ├─ Check time (daily)             │                          │
  │                                 │                          │
  └─ 09:00 UTC? ──────────────────>  │                          │
                                    │                          │
                                    ├─ Query top opportunities │
                                    ├─ Query today's trades    │
                                    ├─ Build digest message    │
                                    └─ Send to Telegram────────>
                                                               │
                                    Record sent in DB          │
                                    │                          │
                                    <─────── User reads ───────┤
```

## API Reference

### Methods Agent Should Call

```python
# Send trade opportunity alert
await telegram_bot.send_trade_alert(
    signal_id: int,
    market_data: Dict,
    requires_approval: bool = False
) -> bool

# Send trade execution notification
await telegram_bot.send_trade_execution(trade_id: int) -> bool

# Send daily digest
await telegram_bot.send_daily_digest() -> bool

# Check if user is owner (can approve)
telegram_bot._is_owner(user_id: int) -> bool

# Get user preferences
from telegram_bot import TelegramDatabase
prefs = TelegramDatabase.get_user_preferences(user_id)
# Returns: {
#     'role': 'owner|viewer',
#     'min_edge_percent': 3.0,
#     'max_position_size_usd': 100,
#     'notifications_enabled': True,
#     'daily_digest_enabled': True,
#     'digest_time': '09:00'
# }
```

### Methods Bot Calls for Agent

None! Bot is read-only from database perspective. It only:
- Reads signals, trades, positions
- Writes approvals, user preferences

## Testing the Integration

```python
# test_integration.py
import asyncio
import sqlite3
from config import DB_PATH
from telegram_bot import telegram_bot

async def test_trade_approval_flow():
    """Test complete trade approval flow."""
    
    # 1. Initialize bot
    await telegram_bot.initialize()
    
    # 2. Create test signal
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO signals
        (market_id, timestamp, market_fair_value, market_price, edge_percent,
         confidence, decision, suggested_position_size, kelly_fraction, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'TEST_BTC_50K',
        '2024-02-11T09:00:00',
        0.62,
        0.55,
        5.2,
        0.75,
        'BUY',
        25.00,
        0.25,
        'Test signal'
    ))
    conn.commit()
    signal_id = c.lastrowid
    conn.close()
    
    # 3. Send to Telegram
    result = await telegram_bot.send_trade_alert(
        signal_id=signal_id,
        market_data={'market_id': 'TEST_BTC_50K'},
        requires_approval=True
    )
    
    print(f"Alert sent: {result}")
    
    # 4. Simulate user approval
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO trade_approvals
        (user_id, signal_id, status, decision)
        VALUES (?, ?, 'approved', 'APPROVE')
    """, (123456789, signal_id))
    conn.commit()
    conn.close()
    
    # 5. Agent checks approval
    approval = get_trade_approval(signal_id)
    print(f"Approval status: {approval}")
    
    # 6. Execute trade
    await telegram_bot.send_trade_execution(1)
    
    print("✅ Integration test complete")

if __name__ == "__main__":
    asyncio.run(test_trade_approval_flow())
```

Run test:
```bash
python test_integration.py
```

## Configuration for Agent

In `agent.py`, add at start:

```python
from config import AUTO_EXEC_THRESHOLD_USD, APPROVAL_THRESHOLD_USD, ENABLE_TELEGRAM
from telegram_bot import telegram_bot

# Use these thresholds for decision logic
if ENABLE_TELEGRAM:
    AUTO_EXEC = AUTO_EXEC_THRESHOLD_USD      # Usually $5
    MANUAL_EXEC = APPROVAL_THRESHOLD_USD      # Usually $50
    # $5-50: Requires user approval
    # <$5: Auto-execute
    # >$50: Manual only
```

## Deployment Checklist

- [ ] Configure bot token in `.env`
- [ ] Get chat ID and add to `.env`
- [ ] Run `python run_telegram_bot.py` to test
- [ ] Verify all commands work in Telegram
- [ ] Integrate `send_trade_alert()` into agent
- [ ] Test trade approval flow
- [ ] Enable daily digest scheduler
- [ ] Deploy to production
- [ ] Monitor logs: `tail -f logs/agent.log`
- [ ] Enable live trading 🚀

## Troubleshooting Integration

### Bot not initialized when agent starts

```python
# Make sure to initialize in main loop
await telegram_bot.initialize()
await asyncio.sleep(1)  # Give it a moment
```

### Approvals not being read

```python
# Check database has tables
python -c "from telegram_bot import TelegramDatabase; TelegramDatabase.init_telegram_tables()"

# Verify signal was created
sqlite3 data/trading.db "SELECT * FROM signals LIMIT 1;"
```

### Trade alerts not sending

```python
# Check bot token
echo $TELEGRAM_BOT_TOKEN

# Check chat ID
python -c "from config import TELEGRAM_CHAT_ID; print(TELEGRAM_CHAT_ID)"

# Test send
python -c "
import asyncio
from telegram_bot import telegram_bot
asyncio.run(telegram_bot.send_trade_alert(1, {}, False))
"
```

## Next Steps

1. ✅ Read this guide
2. ⚙️ Update `agent.py` to call bot methods
3. 🧪 Test integration with `test_integration.py`
4. 🚀 Deploy and go live!

---

**Integration Status**: Ready for implementation  
**Bot Status**: ✅ Production ready  
**Last Updated**: February 2024
