"""
Main entry point - Start the prediction markets trading bot
Telegram library manages its own asyncio event loop - create one for it.
"""

import sys
import threading
import asyncio
from config import Config
from database import db
from market_scanner import market_scanner
from telegram_bot import setup_bot


def main():
    """
    Main entry point (synchronous):
    Telegram library will create and manage its own event loop.
    1. Initialize database
    2. Load configuration
    3. Start market scanner (background thread)
    4. Start Telegram bot (blocks until Ctrl+C)
    """
    
    print("=" * 60)
    print("🚀 PREDICTION MARKETS BOT (Kalshi + Polymarket)")
    print("=" * 60)
    
    try:
        # 1. Initialize database (SQLite - synchronous)
        print("\n[INIT] Initializing database...")
        db.init()
        print("[INIT] ✅ Database ready")
        
        # 2. Validate config
        print("\n[INIT] Validating configuration...")
        Config.validate()
        print("[INIT] ✅ Configuration valid")
        
        # 3. Start market scanner (background thread - no asyncio)
        print("\n[INIT] Starting market scanner...")
        scanner_thread = threading.Thread(
            target=market_scanner.start_continuous_scan,
            daemon=True
        )
        scanner_thread.start()
        print("[INIT] ✅ Market scanner started (background)")
        
        # 4. Setup Telegram bot
        print("\n[INIT] Setting up Telegram bot...")
        application = setup_bot(Config.TELEGRAM_BOT_TOKEN)
        print("[INIT] ✅ Telegram bot ready")
        
        print("\n" + "=" * 60)
        print("✅ BOT RUNNING")
        print("=" * 60)
        print(f"Database: {Config.DATABASE_URL}")
        print(f"Market Scan Interval: {Config.MARKET_SCAN_INTERVAL_SECONDS}s")
        print("Listening for Telegram messages...")
        print("Press Ctrl+C to stop\n")
        
        # 5. Create an event loop for the telegram library
        # (Python 3.14 doesn't create an implicit one)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 6. Run bot - this is a BLOCKING call
        application.run_polling(allowed_updates=["message", "callback_query"])
    
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Stopping bot...")
        print("[SHUTDOWN] ✅ Cleanup complete")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
