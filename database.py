"""
SQLite database models for the autonomous trading agent.
Tracks trades, positions, market data, and learning outcomes.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from config import DB_PATH


class TradingDatabase:
    """SQLite wrapper for trading agent persistence."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Markets table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS markets (
                market_id TEXT PRIMARY KEY,
                platform TEXT,  -- 'polymarket' or 'kalshi'
                title TEXT,
                description TEXT,
                category TEXT,
                created_at TIMESTAMP,
                closes_at TIMESTAMP,
                status TEXT,  -- 'open', 'closed', 'resolved'
                yes_price REAL,
                no_price REAL,
                bid_ask_spread REAL,
                volume_usd REAL,
                liquidity_usd REAL,
                last_updated TIMESTAMP,
                data_hash TEXT UNIQUE
            )
        """
        )

        # Trading signals (decisions made by Claude)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                timestamp TIMESTAMP,
                market_fair_value REAL,
                market_price REAL,
                edge_percent REAL,
                confidence REAL,
                decision TEXT,  -- 'BUY', 'SELL', 'HOLD', 'PASS'
                suggested_position_size REAL,
                kelly_fraction REAL,
                reasoning TEXT,
                claude_reasoning TEXT,
                executed BOOLEAN DEFAULT 0,
                FOREIGN KEY(market_id) REFERENCES markets(market_id)
            )
        """
        )

        # Trades executed
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                signal_id INTEGER,
                timestamp TIMESTAMP,
                side TEXT,  -- 'YES' or 'NO'
                amount_usd REAL,
                entry_price REAL,
                tx_hash TEXT,
                status TEXT,  -- 'pending', 'confirmed', 'failed'
                error_message TEXT,
                FOREIGN KEY(market_id) REFERENCES markets(market_id),
                FOREIGN KEY(signal_id) REFERENCES signals(signal_id)
            )
        """
        )

        # Open positions
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                position_id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                side TEXT,  -- 'YES' or 'NO'
                amount_usd REAL,
                entry_price REAL,
                entry_timestamp TIMESTAMP,
                stop_loss_price REAL,
                profit_target_price REAL,
                status TEXT,  -- 'open', 'closed', 'stopped'
                exit_price REAL,
                exit_timestamp TIMESTAMP,
                pnl_usd REAL,
                pnl_percent REAL,
                FOREIGN KEY(market_id) REFERENCES markets(market_id)
            )
        """
        )

        # Market scorecards (for learning)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS scorecards (
                scorecard_id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                timestamp TIMESTAMP,
                feature_weather_indicator REAL,
                feature_sentiment_score REAL,
                feature_volume_trend REAL,
                feature_bid_ask_spread REAL,
                feature_historical_accuracy REAL,
                predicted_edge REAL,
                actual_edge REAL,
                prediction_error REAL,
                FOREIGN KEY(market_id) REFERENCES markets(market_id)
            )
        """
        )

        # Portfolio history (daily snapshots)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_history (
                day TEXT PRIMARY KEY,
                total_balance_usd REAL,
                positions_count INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                daily_pnl_usd REAL,
                daily_pnl_percent REAL,
                win_rate REAL,
                avg_trade_size_usd REAL
            )
        """
        )

        # Agent learning log
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                event_type TEXT,  -- 'trade_executed', 'signal_generated', 'market_analyzed'
                market_id TEXT,
                details JSON,
                model_version TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def add_market(self, market_data):
        """Insert or update market data."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                """
                INSERT OR REPLACE INTO markets (
                    market_id, platform, title, description, category,
                    created_at, closes_at, status, yes_price, no_price,
                    bid_ask_spread, volume_usd, liquidity_usd, last_updated, data_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    market_data["market_id"],
                    market_data["platform"],
                    market_data["title"],
                    market_data["description"],
                    market_data.get("category"),
                    market_data.get("created_at"),
                    market_data.get("closes_at"),
                    market_data.get("status"),
                    market_data["yes_price"],
                    market_data["no_price"],
                    market_data.get("bid_ask_spread"),
                    market_data.get("volume_usd"),
                    market_data.get("liquidity_usd"),
                    datetime.now().isoformat(),
                    market_data.get("data_hash"),
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to add market: {e}")
        finally:
            conn.close()

    def add_signal(self, signal_data):
        """Record a trading signal from Claude."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                """
                INSERT INTO signals (
                    market_id, timestamp, market_fair_value, market_price, edge_percent,
                    confidence, decision, suggested_position_size, kelly_fraction,
                    reasoning, claude_reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    signal_data["market_id"],
                    datetime.now().isoformat(),
                    signal_data["fair_value"],
                    signal_data["market_price"],
                    signal_data["edge_percent"],
                    signal_data["confidence"],
                    signal_data["decision"],
                    signal_data["position_size"],
                    signal_data["kelly_fraction"],
                    signal_data["reasoning"],
                    signal_data.get("claude_reasoning"),
                ),
            )
            conn.commit()
            return c.lastrowid
        except Exception as e:
            print(f"[DB ERROR] Failed to add signal: {e}")
            return None
        finally:
            conn.close()

    def add_trade(self, trade_data):
        """Record an executed trade."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                """
                INSERT INTO trades (
                    market_id, signal_id, timestamp, side, amount_usd,
                    entry_price, tx_hash, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    trade_data["market_id"],
                    trade_data.get("signal_id"),
                    datetime.now().isoformat(),
                    trade_data["side"],
                    trade_data["amount_usd"],
                    trade_data["entry_price"],
                    trade_data.get("tx_hash"),
                    trade_data.get("status", "pending"),
                    trade_data.get("error_message"),
                ),
            )
            conn.commit()
            return c.lastrowid
        except Exception as e:
            print(f"[DB ERROR] Failed to add trade: {e}")
            return None
        finally:
            conn.close()

    def get_open_positions(self):
        """Fetch all currently open positions."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM positions WHERE status='open'")
        rows = c.fetchall()
        conn.close()
        return rows

    def get_recent_trades(self, limit=10):
        """Fetch recent trades."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return rows

    def log_event(self, event_type, market_id=None, details=None):
        """Log an agent event for learning."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                """
                INSERT INTO learning_log (timestamp, event_type, market_id, details, model_version)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().isoformat(),
                    event_type,
                    market_id,
                    json.dumps(details) if details else None,
                    "claude-haiku-4-5",
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to log event: {e}")
        finally:
            conn.close()


# Initialize database globally
db = TradingDatabase()
