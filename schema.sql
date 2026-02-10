-- Prediction Markets Bot Database Schema
-- Supports: PostgreSQL and SQLite

-- ============================================================================
-- USERS TABLE (Per-user encrypted wallets)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_user_id BIGINT UNIQUE NOT NULL,
  solana_public_key TEXT NOT NULL,
  solana_private_key_encrypted BLOB NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_user_id);

-- ============================================================================
-- MARKETS TABLE (Shared, cached)
-- ============================================================================

CREATE TABLE IF NOT EXISTS markets (
  market_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT,
  platform TEXT,
  current_price DECIMAL(10, 4),
  volume DECIMAL(20, 2),
  description TEXT,
  expires_at TIMESTAMP,
  last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_markets_category ON markets(category);
CREATE INDEX IF NOT EXISTS idx_markets_platform ON markets(platform);

-- ============================================================================
-- MARKET INSIGHTS TABLE (Shared, cached insights)
-- ============================================================================

CREATE TABLE IF NOT EXISTS market_insights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  market_id TEXT NOT NULL,
  fair_value DECIMAL(10, 4),
  opportunity_pct DECIMAL(10, 4),
  confidence DECIMAL(10, 4),
  reasoning TEXT,
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  FOREIGN KEY (market_id) REFERENCES markets(market_id)
);

-- Index for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_insights_market_id ON market_insights(market_id);

-- ============================================================================
-- TRADES TABLE (Per-user)
-- ============================================================================

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trade_id TEXT UNIQUE,
  telegram_user_id BIGINT NOT NULL,
  market_id TEXT NOT NULL,
  amount_usd DECIMAL(12, 2),
  entry_price DECIMAL(20, 8),
  status TEXT DEFAULT 'pending',
  tx_hash TEXT,
  pnl_usd DECIMAL(12, 2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  closed_at TIMESTAMP,
  FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id),
  FOREIGN KEY (market_id) REFERENCES markets(market_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);

-- ============================================================================
-- USER STRATEGIES TABLE (Strategy subscriptions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_strategies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_user_id BIGINT NOT NULL,
  strategy_name TEXT NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  settings TEXT,
  subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id),
  UNIQUE(telegram_user_id, strategy_name)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_user_strategies ON user_strategies(telegram_user_id);

-- ============================================================================
-- API CALLS TABLE (For audit logging)
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_user_id BIGINT NOT NULL,
  service TEXT,
  endpoint TEXT,
  status_code INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_api_calls_user ON api_calls(telegram_user_id);

-- ============================================================================
-- SECURITY EVENTS TABLE (Audit trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_user_id BIGINT NOT NULL,
  event_type TEXT,
  details TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_security_events_user ON security_events(telegram_user_id);
