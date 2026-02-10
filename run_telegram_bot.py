#!/usr/bin/env python3
"""
Main entry point for Telegram Bot

Runs the bot in polling mode (development) or webhook mode (production).

Usage:
    # Development (polling)
    python run_telegram_bot.py

    # Production (webhook)
    python run_telegram_bot.py --webhook --url https://example.com

    # With logging
    python run_telegram_bot.py --log-level DEBUG

    # With custom port
    python run_telegram_bot.py --webhook --port 8443
"""

import asyncio
import logging
import argparse
import sys
from pathlib import Path

# Setup logging before imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from config import TELEGRAM_BOT_TOKEN, ENABLE_TELEGRAM
from telegram_bot import telegram_bot
from telegram_scheduler import DigestScheduler, PerformanceSummaryScheduler


async def run_polling_mode():
    """Run bot in polling mode (development)."""
    logger.info("=" * 60)
    logger.info("🤖 AUTONOMOUS TRADING AGENT - TELEGRAM BOT")
    logger.info("=" * 60)
    logger.info("Mode: POLLING (development)")
    logger.info("=" * 60 + "\n")
    
    try:
        # Initialize bot
        logger.info("Initializing Telegram bot...")
        await telegram_bot.initialize()
        
        # Start polling
        logger.info("Starting polling...")
        logger.info("Bot is now listening for messages!")
        logger.info("\nAvailable commands:")
        logger.info("  /start - Welcome message")
        logger.info("  /status - Agent status")
        logger.info("  /portfolio - View positions")
        logger.info("  /trades - Recent trades")
        logger.info("  /opportunities - Top opportunities")
        logger.info("  /settings - User preferences")
        logger.info("  /help - Help and commands\n")
        
        # Start schedulers
        logger.info("Starting daily digest scheduler...")
        digest_scheduler = DigestScheduler(telegram_bot)
        perf_scheduler = PerformanceSummaryScheduler(telegram_bot)
        
        # Run all tasks concurrently
        try:
            await asyncio.gather(
                telegram_bot.start_polling(),
                digest_scheduler.start(),
                perf_scheduler.start()
            )
        except KeyboardInterrupt:
            logger.info("\n✋ Shutting down gracefully...")
            await telegram_bot.stop()
            await digest_scheduler.stop()
            await perf_scheduler.stop()
    
    except Exception as e:
        logger.error(f"Error in polling mode: {e}", exc_info=True)
        sys.exit(1)


async def run_webhook_mode(webhook_url: str, port: int = 8443, cert_path: str = None):
    """Run bot in webhook mode (production)."""
    logger.info("=" * 60)
    logger.info("🤖 AUTONOMOUS TRADING AGENT - TELEGRAM BOT")
    logger.info("=" * 60)
    logger.info("Mode: WEBHOOK (production)")
    logger.info(f"URL: {webhook_url}")
    logger.info(f"Port: {port}")
    logger.info("=" * 60 + "\n")
    
    try:
        # Try to import FastAPI
        try:
            from fastapi import FastAPI, Request
            from fastapi.responses import JSONResponse
            import uvicorn
            from telegram import Update
        except ImportError:
            logger.error("FastAPI required for webhook mode: pip install fastapi uvicorn")
            sys.exit(1)
        
        # Initialize bot
        logger.info("Initializing Telegram bot...")
        await telegram_bot.initialize()
        
        # Register webhook
        logger.info(f"Registering webhook: {webhook_url}")
        
        if cert_path and Path(cert_path).exists():
            with open(cert_path, 'rb') as f:
                await telegram_bot.app.bot.set_webhook(
                    url=webhook_url,
                    certificate=f,
                    drop_pending_updates=True
                )
        else:
            await telegram_bot.app.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )
        
        # Verify webhook
        info = await telegram_bot.app.bot.get_webhook_info()
        logger.info(f"✅ Webhook registered: {info.get('url', 'N/A')}")
        logger.info(f"Pending updates: {info.get('pending_update_count', 0)}\n")
        
        # Create FastAPI app
        app = FastAPI(title="Trading Agent Telegram Webhook")
        
        @app.post("/webhook")
        async def webhook_handler(request: Request):
            """Handle incoming Telegram updates."""
            try:
                data = await request.json()
                update = Update.de_json(data, telegram_bot.app.bot)
                await telegram_bot.app.process_update(update)
                return {"ok": True}
            except Exception as e:
                logger.error(f"Webhook error: {e}", exc_info=True)
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "bot": "running"}
        
        # Start schedulers
        logger.info("Starting daily digest scheduler...")
        digest_scheduler = DigestScheduler(telegram_bot)
        perf_scheduler = PerformanceSummaryScheduler(telegram_bot)
        
        # Create config for uvicorn
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=port,
            ssl_keyfile="key.pem" if cert_path else None,
            ssl_certfile=cert_path if cert_path else None,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        # Run all tasks
        logger.info(f"Starting webhook server on port {port}...\n")
        
        try:
            await asyncio.gather(
                server.serve(),
                digest_scheduler.start(),
                perf_scheduler.start()
            )
        except KeyboardInterrupt:
            logger.info("\n✋ Shutting down gracefully...")
            server.should_exit = True
            await digest_scheduler.stop()
            await perf_scheduler.stop()
            await telegram_bot.stop()
    
    except Exception as e:
        logger.error(f"Error in webhook mode: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Autonomous Trading Agent Telegram Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Development (polling)
  %(prog)s

  # Production (webhook)
  %(prog)s --webhook --url https://example.com

  # With SSL certificate
  %(prog)s --webhook --url https://example.com --cert /path/to/cert.pem

  # Custom port
  %(prog)s --webhook --url https://example.com --port 8443

  # Debug logging
  %(prog)s --log-level DEBUG
        """
    )
    
    parser.add_argument(
        '--webhook',
        action='store_true',
        help='Run in webhook mode (production) instead of polling'
    )
    
    parser.add_argument(
        '--url',
        help='Webhook URL (required for webhook mode)',
        default=None
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8443,
        help='Port for webhook server (default: 8443)'
    )
    
    parser.add_argument(
        '--cert',
        help='Path to SSL certificate file',
        default=None
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Check prerequisites
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)
    
    if not ENABLE_TELEGRAM:
        logger.error("❌ Telegram bot disabled in config (ENABLE_TELEGRAM=False)")
        sys.exit(1)
    
    # Run appropriate mode
    try:
        if args.webhook:
            if not args.url:
                logger.error("❌ --url required for webhook mode")
                sys.exit(1)
            
            asyncio.run(run_webhook_mode(args.url, args.port, args.cert))
        else:
            asyncio.run(run_polling_mode())
    
    except KeyboardInterrupt:
        logger.info("\n✋ Bot stopped")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
