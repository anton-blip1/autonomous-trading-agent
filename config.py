"""
Configuration management for the autonomous trading agent.
Handles API keys, database paths, and runtime settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== API KEYS & CREDENTIALS =====
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY", "")

# ===== POLYMARKET CONFIG =====
POLYMARKET_API_BASE = "https://clob.polymarket.com"
POLYMARKET_WS_URL = "wss://ws-clob.polymarket.com/ws"

# ===== KALSHI CONFIG =====
KALSHI_API_BASE = "https://api.kalshi.com/trade-api/v2"
KALSHI_USERNAME = os.getenv("KALSHI_USERNAME", "")
KALSHI_PASSWORD = os.getenv("KALSHI_PASSWORD", "")

# ===== SOLANA CONFIG =====
SOLANA_RPC_URL = "https://api.devnet.solana.com"
SOLANA_COMMITMENT = "confirmed"
SOLANA_NETWORK = "devnet"

# ===== DATABASE CONFIG =====
DB_PATH = Path(__file__).parent / "data" / "trading.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ===== TRADING PARAMETERS =====
SCAN_INTERVAL_SECONDS = 5  # Scan markets every 5 seconds
DECISION_INTERVAL_MINUTES = 5  # Make decisions every 5 minutes
MIN_EDGE_PERCENT = 3.0  # Minimum 3% edge to trade
MIN_CONFIDENCE = 0.65  # Minimum 65% confidence
MAX_POSITION_SIZE_USD = 100  # Max position: $100
MIN_POSITION_SIZE_USD = 1  # Min position: $1
AUTO_EXEC_THRESHOLD_USD = 5  # Auto-execute trades under $5
APPROVAL_THRESHOLD_USD = 50  # Require approval for trades $5-50
MAX_POSITIONS = 20  # Max concurrent positions
KELLY_FRACTION = 0.25  # Kelly Criterion (Kelly / 4 for safety)

# ===== RISK PARAMETERS =====
MAX_PORTFOLIO_CONCENTRATION = 0.5  # Max 50% in one outcome
MAX_PORTFOLIO_HEAT = 0.3  # Max 30% of bankroll at risk
STOP_LOSS_PERCENT = 10  # Stop loss at 10% loss
PROFIT_TARGET_PERCENT = 50  # Take profit at 50% gain
MAX_DRAWDOWN_PERCENT = 20  # Circuit breaker at 20% drawdown

# ===== LOGGING CONFIG =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = Path(__file__).parent / "logs" / "agent.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ===== DATA SOURCES =====
NOAA_API_BASE = "https://api.weather.gov"
SENTIMENT_API_BASE = "https://newsapi.org/v2"

# ===== TELEGRAM CONFIG =====
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_UPDATE_INTERVAL_SECONDS = 30

# ===== MARKET FILTERS =====
MIN_VOLUME_USD = 100  # Only markets with $100+ volume
MIN_LIQUIDITY_USD = 50  # Only markets with $50+ liquidity on both sides
MARKET_CATEGORIES = ["crypto", "weather", "sports", "politics", "economics"]

# ===== FEATURE FLAGS =====
ENABLE_TELEGRAM = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
ENABLE_LIVE_TRADING = True  # Set False for testing
ENABLE_LEARNING = True  # Track outcomes and improve
VERBOSE_LOGGING = True

# ===== INITIAL BANKROLL =====
INITIAL_BANKROLL_USD = 1000  # Starting with $1000 in devnet USDC
STARTING_SOLANA_BALANCE = 5  # 5 SOL on devnet for gas fees

print(f"[CONFIG] Loaded configuration:")
print(f"  - Solana Network: {SOLANA_NETWORK}")
print(f"  - Scan Interval: {SCAN_INTERVAL_SECONDS}s")
print(f"  - Min Edge: {MIN_EDGE_PERCENT}%")
print(f"  - Telegram Enabled: {ENABLE_TELEGRAM}")
print(f"  - Database: {DB_PATH}")
