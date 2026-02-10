# Database Setup Guide (PostgreSQL)

## Quick Start: 3 Options

### Option 1: SQLite (Fastest for Dev - Start Here)

```bash
# Create local SQLite database
sqlite3 trading_agent.db

# Create tables
sqlite3 trading_agent.db < schema-sqlite.sql

# Connection string for .env
DATABASE_URL=sqlite:///trading_agent.db
```

**Pros:**
- Zero setup, instant
- Perfect for testing agent logic locally
- No server needed

**Cons:**
- Single-threaded (not true multi-user)
- Not production-ready
- Will fail under real load

**Use:** Days 1-3 of development

---

### Option 2: PostgreSQL Local (Docker)

```bash
# Install Docker (if not already)
# https://docs.docker.com/get-docker/

# Start PostgreSQL container
docker run --name trading-agent-db \
  -e POSTGRES_USER=faizan \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=trading_agent \
  -p 5432:5432 \
  -d postgres:15

# Verify it's running
docker ps | grep trading-agent-db

# Create schema (wait 5 seconds for DB to start)
sleep 5
psql postgresql://faizan:secure_password@localhost:5432/trading_agent < schema.sql

# Connection string for .env
DATABASE_URL=postgresql://faizan:secure_password@localhost:5432/trading_agent
```

**Pros:**
- True multi-user support
- Production-like environment locally
- Easy to reset: `docker rm trading-agent-db`
- Shows judges you know PostgreSQL

**Cons:**
- Requires Docker
- Data lost when container removed (unless volume mounted)

**Use:** Days 3-8 (before submission)

---

### Option 3: PostgreSQL Cloud (Render - Free Trial)

```bash
# After creating Render account:
# 1. Go to https://render.com
# 2. Create new PostgreSQL database
# 3. Use their provided connection string

# Example (your string will differ):
DATABASE_URL=postgresql://user_xxxx:pass_yyyy@dpg-xxxxx-a.oregon-postgres.render.com/trading_agent_xxxx

# Create schema
psql <your-render-connection-string> < schema.sql

# Backup: Create weekly snapshots in Render dashboard
```

**Pros:**
- Actual cloud database (production-like)
- Free for 90 days (perfect for hackathon)
- Automatic backups
- Judges can see real cloud deployment

**Cons:**
- Network latency (slight)
- Free tier will be deactivated after trial

**Use:** Days 7+ (for final submission demo)

---

## Setup Step-by-Step: PostgreSQL Local

### 1. Install Docker

**Mac:**
```bash
# Install via Homebrew
brew install docker

# Or download from https://www.docker.com/products/docker-desktop
```

**Verify:**
```bash
docker --version
```

### 2. Start Database Container

```bash
# Create container with persistent volume
docker run --name trading-agent-db \
  -e POSTGRES_USER=faizan \
  -e POSTGRES_PASSWORD=trade_agent_2026 \
  -e POSTGRES_DB=trading_agent \
  -p 5432:5432 \
  -v trading_agent_data:/var/lib/postgresql/data \
  -d postgres:15

# Verify it's running
docker logs trading-agent-db
# Should show: "database system is ready to accept connections"

# Keep running in background even after shell closes
# To stop: docker stop trading-agent-db
# To restart: docker start trading-agent-db
```

### 3. Create Tables

```bash
# Wait 5 seconds for DB initialization
sleep 5

# Run schema
PGPASSWORD=trade_agent_2026 psql \
  -h localhost \
  -U faizan \
  -d trading_agent \
  -f schema.sql

# Verify tables created
PGPASSWORD=trade_agent_2026 psql \
  -h localhost \
  -U faizan \
  -d trading_agent \
  -c "\dt"

# Should show: users, strategies, user_strategies, trades, strategy_signals, api_calls, security_events
```

### 4. Set .env

```bash
# Copy to .env
DATABASE_URL=postgresql://faizan:trade_agent_2026@localhost:5432/trading_agent

# Verify connection
python -c "import psycopg2; print(psycopg2.connect('postgresql://faizan:trade_agent_2026@localhost:5432/trading_agent'))"
# Should connect successfully
```

### 5. Test Connection in Python

```python
# test_db.py
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect('postgresql://faizan:trade_agent_2026@localhost:5432/trading_agent')
    
    # Count tables
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    print(f"✅ Connected! Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table['tablename']}")
    
    await conn.close()

asyncio.run(test())
```

---

## Database Operations in Python

### Connect & Query

```python
# database.py
import asyncpg
import os
from typing import Optional, List, Dict

class Database:
    
    def __init__(self):
        self.pool = None
        self.connection_string = os.environ['DATABASE_URL']
    
    async def init(self):
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(self.connection_string)
        print("✅ Database pool initialized")
    
    async def close(self):
        """Close all connections."""
        await self.pool.close()
    
    # ========== USERS ==========
    
    async def create_user(self, user_data: Dict) -> Dict:
        """Create new user with encrypted keys."""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow("""
                INSERT INTO users (
                    telegram_user_id,
                    solana_public_key,
                    solana_private_key_encrypted,
                    polygon_public_key,
                    polygon_private_key_encrypted
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
            """,
                user_data['telegram_user_id'],
                user_data['solana_public_key'],
                user_data['solana_private_key_encrypted'],
                user_data['polygon_public_key'],
                user_data['polygon_private_key_encrypted']
            )
            return dict(user)
    
    async def get_user(self, telegram_user_id: int) -> Optional[Dict]:
        """Get user by Telegram ID."""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT * FROM users
                WHERE telegram_user_id = $1
            """, telegram_user_id)
            return dict(user) if user else None
    
    # ========== STRATEGIES ==========
    
    async def get_strategies(self, active_only: bool = True) -> List[Dict]:
        """Get all available strategies."""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM strategies"
            if active_only:
                query += " WHERE active = TRUE"
            strategies = await conn.fetch(query)
            return [dict(s) for s in strategies]
    
    # ========== USER STRATEGIES ==========
    
    async def subscribe_to_strategy(self, telegram_user_id: int, strategy_id: int) -> Dict:
        """Subscribe user to strategy."""
        async with self.pool.acquire() as conn:
            sub = await conn.fetchrow("""
                INSERT INTO user_strategies (telegram_user_id, strategy_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                RETURNING *
            """, telegram_user_id, strategy_id)
            return dict(sub) if sub else {}
    
    async def get_user_strategies(self, telegram_user_id: int) -> List[Dict]:
        """Get strategies user is subscribed to."""
        async with self.pool.acquire() as conn:
            strategies = await conn.fetch("""
                SELECT s.* FROM strategies s
                JOIN user_strategies us ON s.id = us.strategy_id
                WHERE us.telegram_user_id = $1 AND us.enabled = TRUE
                ORDER BY s.name
            """, telegram_user_id)
            return [dict(s) for s in strategies]
    
    # ========== SIGNALS ==========
    
    async def create_signal(self, signal_data: Dict) -> Dict:
        """Create strategy signal (recommendation sent to user)."""
        async with self.pool.acquire() as conn:
            signal = await conn.fetchrow("""
                INSERT INTO strategy_signals (
                    telegram_user_id,
                    strategy_id,
                    market,
                    chain,
                    analysis_json,
                    recommendation,
                    confidence_score
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
            """,
                signal_data['telegram_user_id'],
                signal_data['strategy_id'],
                signal_data['market'],
                signal_data.get('chain'),
                signal_data.get('analysis_json'),
                signal_data.get('recommendation'),
                signal_data.get('confidence_score')
            )
            return dict(signal)
    
    async def get_pending_signals(self, telegram_user_id: int) -> List[Dict]:
        """Get pending signals awaiting user action."""
        async with self.pool.acquire() as conn:
            signals = await conn.fetch("""
                SELECT * FROM strategy_signals
                WHERE telegram_user_id = $1 AND user_action = 'pending'
                ORDER BY created_at DESC
            """, telegram_user_id)
            return [dict(s) for s in signals]
    
    # ========== TRADES ==========
    
    async def create_trade(self, trade_data: Dict) -> Dict:
        """Create executed trade record."""
        async with self.pool.acquire() as conn:
            trade = await conn.fetchrow("""
                INSERT INTO trades (
                    telegram_user_id,
                    strategy_id,
                    market,
                    chain,
                    trade_type,
                    amount_usd,
                    entry_price,
                    status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """,
                trade_data['telegram_user_id'],
                trade_data.get('strategy_id'),
                trade_data['market'],
                trade_data['chain'],
                trade_data['trade_type'],
                trade_data['amount_usd'],
                trade_data['entry_price'],
                'pending'
            )
            return dict(trade)
    
    async def get_user_trades(self, telegram_user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent trades for user."""
        async with self.pool.acquire() as conn:
            trades = await conn.fetch("""
                SELECT * FROM trades
                WHERE telegram_user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, telegram_user_id, limit)
            return [dict(t) for t in trades]
    
    # ========== AUDIT ==========
    
    async def log_api_call(self, call_data: Dict):
        """Log API call for rate limiting."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO api_calls (
                    telegram_user_id,
                    service,
                    endpoint,
                    status_code,
                    success
                )
                VALUES ($1, $2, $3, $4, $5)
            """,
                call_data['telegram_user_id'],
                call_data['service'],
                call_data.get('endpoint'),
                call_data.get('status_code'),
                call_data.get('success', True)
            )

# Global instance
db = Database()

# In main.py:
# async def main():
#     await db.init()
#     # ... use db
#     await db.close()
```

---

## Helpful PostgreSQL Commands

### Connect & Inspect

```bash
# Connect to database
PGPASSWORD=trade_agent_2026 psql -h localhost -U faizan -d trading_agent

# Inside psql shell:
\dt              # List all tables
\d users         # Describe users table
\d+ strategies   # Show columns and indexes
SELECT COUNT(*) FROM users;  # Count users
SELECT COUNT(*) FROM trades; # Count trades

# View user performance
SELECT * FROM user_performance;

# View strategy performance
SELECT * FROM strategy_performance;

# Exit
\q
```

### Backup & Restore

```bash
# Backup database to file
PGPASSWORD=trade_agent_2026 pg_dump \
  -h localhost \
  -U faizan \
  -d trading_agent \
  > trading_agent_backup.sql

# Restore from backup
PGPASSWORD=trade_agent_2026 psql \
  -h localhost \
  -U faizan \
  -d trading_agent \
  < trading_agent_backup.sql

# Backup to compressed format (faster)
PGPASSWORD=trade_agent_2026 pg_dump \
  -h localhost \
  -U faizan \
  -d trading_agent \
  -F c > trading_agent_backup.dump
```

---

## Database Encryption (Private Keys)

### How It Works

```python
from cryptography.fernet import Fernet
import os

# Generate encryption key (one time)
encryption_key = Fernet.generate_key()
# Save to .env as ENCRYPTION_KEY

# Use in code
cipher = Fernet(encryption_key)

# Encrypt private key before storing
private_key_bytes = b'...'
encrypted = cipher.encrypt(private_key_bytes)

# Store encrypted bytes in database
async with pool.acquire() as conn:
    await conn.execute("""
        INSERT INTO users (solana_private_key_encrypted)
        VALUES ($1)
    """, encrypted)

# Retrieve and decrypt when needed
async with pool.acquire() as conn:
    result = await conn.fetchval("""
        SELECT solana_private_key_encrypted FROM users
        WHERE telegram_user_id = $1
    """, user_id)

decrypted = cipher.decrypt(result)
# Use decrypted private key to sign transaction
```

### Generate Encryption Key

```bash
# One time: Generate key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copy output to .env as:
ENCRYPTION_KEY=your_key_here

# Never commit this key to GitHub!
```

---

## Troubleshooting

### "Connection refused"

```bash
# Check if PostgreSQL is running
docker ps | grep trading-agent-db

# If not running:
docker start trading-agent-db

# Check logs
docker logs trading-agent-db
```

### "Column does not exist"

```bash
# Re-run schema
PGPASSWORD=trade_agent_2026 psql \
  -h localhost \
  -U faizan \
  -d trading_agent \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Then re-create tables
PGPASSWORD=trade_agent_2026 psql \
  -h localhost \
  -U faizan \
  -d trading_agent \
  -f schema.sql
```

### "Too many connections"

```bash
# Check active connections
PGPASSWORD=trade_agent_2026 psql \
  -h localhost \
  -U faizan \
  -d trading_agent \
  -c "SELECT count(*) FROM pg_stat_activity;"

# Increase limit in Docker
docker stop trading-agent-db
docker rm trading-agent-db

# Re-create with higher limit
docker run ... \
  -e POSTGRES_INIT_ARGS="-c max_connections=200" \
  postgres:15
```

---

## Recommended Setup for Hackathon

### Days 1-3: SQLite
```bash
sqlite3 trading_agent.db < schema-sqlite.sql
DATABASE_URL=sqlite:///trading_agent.db
```

### Days 3-8: PostgreSQL Local (Docker)
```bash
docker run --name trading-agent-db \
  -e POSTGRES_USER=faizan \
  -e POSTGRES_PASSWORD=trade_agent_2026 \
  -e POSTGRES_DB=trading_agent \
  -p 5432:5432 \
  -v trading_agent_data:/var/lib/postgresql/data \
  -d postgres:15

psql postgresql://faizan:trade_agent_2026@localhost:5432/trading_agent < schema.sql

DATABASE_URL=postgresql://faizan:trade_agent_2026@localhost:5432/trading_agent
```

### Submission: Include Both
- `schema.sql` (PostgreSQL)
- `schema-sqlite.sql` (SQLite for quick testing)
- `docker-compose.yml` (judges can spin up with one command)
- Connection instructions in README

**Judges appreciate:** Production-ready with clear deployment path.
