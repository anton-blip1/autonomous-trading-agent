"""
Configuration - Load settings from environment
Never hardcode secrets in code
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """Configuration loaded from environment variables."""
    
    # ========== REQUIRED ==========
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    # Groq LLM (for market analysis)
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_MODEL = 'mixtral-8x7b-32768'  # Free tier
    
    # Encryption
    ENCRYPTION_MASTER_KEY = os.environ.get('ENCRYPTION_MASTER_KEY')
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///trading_agent.db')
    
    # ========== OPTIONAL (APIs) ==========
    
    # Kalshi (Weather markets)
    KALSHI_API_KEY = os.environ.get('KALSHI_API_KEY', '')
    KALSHI_BASE_URL = 'https://api.kalshi.com/v1'
    
    # Polymarket (Event markets)
    POLYMARKET_API_KEY = os.environ.get('POLYMARKET_API_KEY', '')
    POLYMARKET_BASE_URL = 'https://polymarket.com/api'
    
    # ========== OPTIONAL (Blockchain) ==========
    
    # Solana RPC
    SOLANA_RPC_URL = os.environ.get('SOLANA_RPC_URL', 'https://api.devnet.solana.com')
    SOLANA_NETWORK = 'devnet'  # Use devnet for testing
    
    # ========== OPTIONAL (Settings) ==========
    
    # Market scanning
    MARKET_SCAN_INTERVAL_SECONDS = 60  # Fetch markets every 60 seconds
    INSIGHT_CACHE_TTL_SECONDS = 300    # Cache insights for 5 minutes
    
    # Trading
    MAX_POSITION_USD = 20.0             # Max position size per trade
    AUTO_EXEC_THRESHOLD_USD = 5.0       # Auto-execute trades < $5 (no approval needed)
    APPROVAL_THRESHOLD_USD = 100.0      # Require approval for trades >= $5
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate all required environment variables are set."""
        required = [
            'TELEGRAM_BOT_TOKEN',
            'GROQ_API_KEY',
            'ENCRYPTION_MASTER_KEY',
        ]
        
        missing = []
        for var in required:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Add them to .env file:\n"
                f"TELEGRAM_BOT_TOKEN=your_token\n"
                f"GROQ_API_KEY=your_key\n"
                f"ENCRYPTION_MASTER_KEY=your_key\n"
            )
    
    @classmethod
    def __repr__(cls):
        """Never print config with actual values."""
        return "<Config: loaded from environment>"


# Validate on import
Config.validate()
