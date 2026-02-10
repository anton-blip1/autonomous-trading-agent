"""
Database client - SQLite operations (synchronous)
Handles user data, markets, insights, trades, strategies
"""

import os
import sqlite3
import json
from typing import Optional, List, Dict
from datetime import datetime


class Database:
    """Database abstraction layer (SQLite - synchronous)."""
    
    def __init__(self):
        self.connection_string = os.environ.get('DATABASE_URL', 'sqlite:///trading_agent.db')
        self.db_path = self.connection_string.replace('sqlite:///', '')
        self.conn = None
    
    def init(self):
        """Initialize database connection (synchronous)."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            
            # Create schema if not exists
            cursor = self.conn.cursor()
            
            # Read schema from file
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema = f.read()
                    cursor.executescript(schema)
            
            self.conn.commit()
            print(f"[DB] SQLite initialized: {self.db_path}")
            return True
        except Exception as e:
            print(f"[DB] Error initializing database: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    # ========== USERS ==========
    
    def create_user(self, user_data: Dict) -> Dict:
        """Create new user with encrypted wallet."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO users 
                   (telegram_user_id, solana_public_key, solana_private_key_encrypted)
                   VALUES (?, ?, ?)""",
                (user_data['telegram_user_id'],
                 user_data['solana_public_key'],
                 user_data['solana_private_key_encrypted'])
            )
            self.conn.commit()
            return user_data
        except Exception as e:
            print(f"[DB] Error creating user: {e}")
            return {}
    
    def get_user(self, telegram_user_id: int) -> Optional[Dict]:
        """Get user by Telegram ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE telegram_user_id = ?",
                (telegram_user_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"[DB] Error getting user: {e}")
            return None
    
    # ========== MARKETS ==========
    
    def store_markets(self, markets: List[Dict]) -> bool:
        """Store/update markets in database."""
        try:
            cursor = self.conn.cursor()
            for market in markets:
                cursor.execute(
                    """INSERT OR REPLACE INTO markets 
                       (market_id, platform, title, category, current_price, volume, expires_at, data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (market.get('market_id'),
                     market.get('platform'),
                     market.get('title'),
                     market.get('category'),
                     market.get('current_price', 0.5),
                     market.get('volume', 0),
                     market.get('expires_at'),
                     json.dumps(market))
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error storing markets: {e}")
            return False
    
    def get_market(self, market_id: str) -> Optional[Dict]:
        """Get specific market by ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT data FROM markets WHERE market_id = ?",
                (market_id,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row['data'])
            return None
        except Exception as e:
            print(f"[DB] Error getting market: {e}")
            return None
    
    def get_all_markets(self) -> List[Dict]:
        """Get all markets."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT data FROM markets")
            rows = cursor.fetchall()
            return [json.loads(row['data']) for row in rows]
        except Exception as e:
            print(f"[DB] Error getting markets: {e}")
            return []
    
    # ========== TRADES ==========
    
    def log_trade(self, user_id: int, trade_data: Dict) -> bool:
        """Log a trade."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO trades 
                   (telegram_user_id, market_id, action, amount, price, status, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id,
                 trade_data.get('market_id'),
                 trade_data.get('action'),
                 trade_data.get('amount', 0),
                 trade_data.get('price', 0),
                 trade_data.get('status', 'pending'),
                 json.dumps(trade_data))
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error logging trade: {e}")
            return False
    
    def get_user_trades(self, user_id: int) -> List[Dict]:
        """Get all trades for a user."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT data FROM trades WHERE telegram_user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [json.loads(row['data']) for row in rows]
        except Exception as e:
            print(f"[DB] Error getting trades: {e}")
            return []


# Global instance
db = Database()
