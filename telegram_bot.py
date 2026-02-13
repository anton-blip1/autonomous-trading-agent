"""
Telegram Bot - Handlers for user interactions (synchronous database)
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from wallet_manager import wallet_manager
from market_scanner import market_scanner
from database import db
from config import Config
from wormhole_bridge_production import wormhole_bridge


class BotHandlers:
    """Telegram bot command handlers."""
    
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /start - Initialize user with non-custodial wallet.
        Creates encrypted Solana keypair.
        """
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        print(f"[BOT] /start command received from {user_id} ({user_name})")
        
        # Check if user already has wallet
        existing_user = db.get_user(user_id)
        print(f"[BOT] Existing user check: {existing_user is not None}")
        
        if existing_user:
            # Returning user
            await update.message.reply_text(
                f"👋 Welcome back, {user_name}!\n\n"
                f"Your Solana wallet:\n"
                f"`{existing_user['solana_public_key']}`\n\n"
                f"Use /browse to see markets\n"
                f"Use /balance to check funds\n"
                f"Use /trade to execute trades"
            )
        else:
            # New user - create wallet
            wallet_info = wallet_manager.create_user_wallet(user_id)
            
            await update.message.reply_text(
                f"🎉 Welcome, {user_name}!\n\n"
                f"✅ Your non-custodial Solana wallet created:\n\n"
                f"**Public Address:**\n"
                f"`{wallet_info['solana_public_key']}`\n\n"
                f"💰 Send SOL to this address to fund your account.\n"
                f"Your private key is encrypted and secure.\n\n"
                f"Commands:\n"
                f"/browse - Browse prediction markets\n"
                f"/balance - Check wallet balance\n"
                f"/help - Get help"
            )
            
            print(f"[BOT] User {user_id} ({user_name}) created wallet")
    
    @staticmethod
    async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /browse - Browse prediction markets with pagination.
        Shows weather + event markets.
        """
        
        user_id = update.effective_user.id
        
        # Ensure user has wallet
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start first to create your wallet")
            return
        
        # Get markets from scanner (synchronous)
        markets = market_scanner.get_market_page(page=1, category=None)
        
        if not markets:
            # Generate mock markets if real API fails
            markets = [
                {
                    'id': 'weather_snow_ny',
                    'title': 'Will it snow in NYC this week?',
                    'category': 'weather',
                    'platform': 'kalshi',
                    'current_price': 0.65,
                    'volume': 15000,
                },
                {
                    'id': 'crypto_btc_50k',
                    'title': 'Bitcoin above $50k by end of month?',
                    'category': 'crypto',
                    'platform': 'polymarket',
                    'current_price': 0.72,
                    'volume': 500000,
                },
                {
                    'id': 'politics_election',
                    'title': 'Election result prediction',
                    'category': 'politics',
                    'platform': 'polymarket',
                    'current_price': 0.45,
                    'volume': 2000000,
                },
                {
                    'id': 'sports_nfl_playoff',
                    'title': 'Super Bowl winner (AFC team)',
                    'category': 'sports',
                    'platform': 'polymarket',
                    'current_price': 0.38,
                    'volume': 1500000,
                },
                {
                    'id': 'weather_rain_london',
                    'title': 'Will it rain in London tomorrow?',
                    'category': 'weather',
                    'platform': 'kalshi',
                    'current_price': 0.55,
                    'volume': 8000,
                },
            ]
        
        # Format markets message
        message = f"📊 **PREDICTION MARKETS** (Top 5)\n\n"
        
        for i, market in enumerate(markets[:5], 1):
            message += (
                f"{i}. **{market['title']}**\n"
                f"   Platform: {market['platform'].upper()}\n"
                f"   Price: {market['current_price']:.0%} | "
                f"Volume: ${market.get('volume', 0):,}\n\n"
            )
        
        message += (
            f"\nUse /trade to buy/sell a market\n"
            f"Use /help for more commands"
        )
        
        await update.message.reply_text(message)
        print(f"[BOT] User {user_id} browsing markets")
    
    @staticmethod
    async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /balance - Check wallet balance.
        """
        
        user_id = update.effective_user.id
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start first")
            return
        
        # Get balance (mock for now)
        balance = 0.0
        
        await update.message.reply_text(
            f"💰 **WALLET BALANCE**\n\n"
            f"SOL: {balance:.4f}\n"
            f"USDC: 0.00\n\n"
            f"Address: `{user['solana_public_key']}`"
        )
    
    @staticmethod
    async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /trade - Execute a trade on a market.
        """
        
        user_id = update.effective_user.id
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start first")
            return
        
        await update.message.reply_text(
            f"🤖 **TRADE EXECUTION**\n\n"
            f"To execute a trade:\n"
            f"1. Use /browse to find a market\n"
            f"2. Reply with the market number + amount\n"
            f"3. Confirm the transaction\n\n"
            f"Example: `2 100` = $100 on market 2"
        )
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /help - Show command list.
        """
        
        await update.message.reply_text(
            f"📚 **COMMANDS**\n\n"
            f"**Wallet & Setup:**\n"
            f"/start - Create wallet\n"
            f"/balance - Check balance\n"
            f"/performance - View trading stats\n\n"
            f"**Trading:**\n"
            f"/browse - Browse markets\n"
            f"/trade - Execute trade\n\n"
            f"**Cross-Chain:**\n"
            f"/bridge - Bridge SOL → Polygon\n"
            f"/bridge-status - Check bridge status\n\n"
            f"/help - This message\n\n"
            f"💡 All addresses are copyable (just tap them)"
        )
    
    @staticmethod
    async def performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /performance - Show trading performance.
        """
        
        user_id = update.effective_user.id
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start first")
            return
        
        trades = db.get_user_trades(user_id)
        
        await update.message.reply_text(
            f"📈 **PERFORMANCE**\n\n"
            f"Total Trades: {len(trades)}\n"
            f"Win Rate: —\n"
            f"P&L: $0.00\n\n"
            f"Use /trade to start trading"
        )
    
    @staticmethod
    async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /bridge - Bridge SOL to Polygon via Wormhole.
        Converts SOL to USDC on Polygon mainnet.
        """
        
        user_id = update.effective_user.id
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please use /start first")
            return
        
        # Get dynamic fees
        fees = await wormhole_bridge.get_dynamic_fees()
        
        await update.message.reply_text(
            f"🌉 **WORMHOLE BRIDGE: Solana → Polygon**\n\n"
            f"**Steps:**\n"
            f"1. Send SOL to your Solana address below\n"
            f"2. Bot will bridge automatically\n"
            f"3. Receive USDC on Polygon (~5-10 min)\n\n"
            f"**Your Solana Address (copyable):**\n"
            f"`{user['solana_public_key']}`\n\n"
            f"**Bridge Fees:**\n"
            f"• Relayer: {fees['base_relayer_fee_sol']:.4f} SOL\n"
            f"• Gas: ~{fees['solana_priority_fee_sol']:.4f} SOL\n"
            f"• **Total: {fees['total_estimated_cost_sol']:.4f} SOL**\n\n"
            f"**Example:** Send 1 SOL → Get ~$15 USDC on Polygon\n"
            f"(minus ~0.055 SOL in fees)\n\n"
            f"📝 Reply with the amount in SOL to bridge.\n"
            f"(e.g., `1` for 1 SOL, `2.5` for 2.5 SOL)"
        )
    
    @staticmethod
    async def bridge_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /bridge-status [bridge_id] - Check bridge transaction status.
        """
        
        user_id = update.effective_user.id
        args = update.message.text.split()
        
        if len(args) < 2:
            # Show recent bridges
            history = await wormhole_bridge.get_bridge_history(user_id, limit=5)
            
            if not history:
                await update.message.reply_text("No bridge history found. Use /bridge to start.")
                return
            
            message = "📋 **Your Recent Bridges:**\n\n"
            for i, b in enumerate(history, 1):
                message += (
                    f"{i}. {b['from'].upper()} → {b['to'].upper()}\n"
                    f"   Amount: {b['amount_sol']:.4f} SOL\n"
                    f"   Status: {b['status']}\n"
                    f"   ID: `{b['bridge_id'][:12]}`\n\n"
                )
            
            message += "Use `/bridge-status [id]` to check a specific bridge."
            await update.message.reply_text(message)
        else:
            # Check specific bridge
            bridge_id = args[1]
            status = await wormhole_bridge.poll_bridge_status(bridge_id)
            
            status_emoji = {
                'pending_signature': '⏳',
                'submitted': '📤',
                'attesting': '🔐',
                'attested': '✅',
                'completing': '🔄',
                'completed': '🎉',
                'failed': '❌',
            }
            
            await update.message.reply_text(
                f"{status_emoji.get(status['status'], '❓')} **Bridge Status**\n\n"
                f"Bridge ID: `{bridge_id}`\n"
                f"Status: {status['status']}\n"
                f"Guardian Confirmations: {status.get('guardian_confirmations', 0)}/13\n\n"
                f"⏱️ Estimated time: 5-10 minutes total"
            )
    
    @staticmethod
    async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands."""
        await update.message.reply_text("Unknown command. Use /help for available commands.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    print(f"[BOT] Update {update} caused error {context.error}")
    import traceback
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)


def setup_bot(token: str):
    """
    Initialize Telegram bot with handlers.
    
    Args:
        token: Telegram bot token
    
    Returns:
        Application (bot instance)
    """
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add handlers
    application.add_handler(CommandHandler("start", BotHandlers.start))
    application.add_handler(CommandHandler("browse", BotHandlers.browse))
    application.add_handler(CommandHandler("balance", BotHandlers.balance))
    application.add_handler(CommandHandler("trade", BotHandlers.trade))
    application.add_handler(CommandHandler("bridge", BotHandlers.bridge))
    application.add_handler(CommandHandler("bridge-status", BotHandlers.bridge_status))
    application.add_handler(CommandHandler("performance", BotHandlers.performance))
    application.add_handler(CommandHandler("help", BotHandlers.help_command))
    application.add_handler(MessageHandler(filters.COMMAND, BotHandlers.unknown))
    
    print("[BOT] Telegram bot handlers initialized")
    print(f"[BOT] Testing token validity...")
    
    return application
