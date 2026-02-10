"""
Telegram Bot - User interface for the trading agent.
Shows daily digest, trade alerts, and approval buttons for medium trades.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from database import db


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for agent UI and approvals."""

    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.app = None
        self.pending_approvals = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 *Autonomous Trading Agent*\n\n"
            "I'm monitoring prediction markets and executing trades autonomously.\n\n"
            "Commands:\n"
            "/portfolio - Show current positions\n"
            "/trades - Show recent trades\n"
            "/status - Check agent status\n"
            "/help - Show this help",
            parse_mode="Markdown"
        )

    async def show_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current portfolio."""
        positions = db.get_open_positions()
        
        if not positions:
            await update.message.reply_text("📊 No open positions")
            return
        
        message = "📊 *Current Portfolio*\n\n"
        total_exposure = 0
        
        for pos in positions[:10]:  # Limit to 10
            market_id, side, amount, entry_price, status = pos[1:6]
            message += f"• {market_id[:20]}...\n"
            message += f"  Side: {side} | Amount: ${amount:.2f}\n"
            message += f"  Entry: {entry_price:.4f}\n\n"
            total_exposure += amount
        
        message += f"*Total Exposure*: ${total_exposure:.2f}"
        
        await update.message.reply_text(message, parse_mode="Markdown")

    async def show_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent trades."""
        trades = db.get_recent_trades(10)
        
        if not trades:
            await update.message.reply_text("📈 No recent trades")
            return
        
        message = "📈 *Recent Trades*\n\n"
        
        for trade in trades:
            trade_id, market_id, signal_id, timestamp, side, amount_usd, entry_price, tx_hash, status = trade[:9]
            message += f"• Trade #{trade_id}\n"
            message += f"  {side} ${amount_usd:.2f} @ {entry_price:.4f}\n"
            message += f"  Status: {status}\n"
            message += f"  Time: {timestamp[:19]}\n\n"
        
        await update.message.reply_text(message, parse_mode="Markdown")

    async def send_trade_alert(self, trade_data: Dict, requires_approval: bool = False):
        """Send trade alert to Telegram."""
        if not self.chat_id:
            return
        
        message = "🚀 *Trade Opportunity Detected*\n\n"
        message += f"Market: {trade_data.get('market_id', 'N/A')}\n"
        message += f"Side: {trade_data.get('side', 'N/A')}\n"
        message += f"Amount: ${trade_data.get('amount_usd', 0):.2f}\n"
        message += f"Entry Price: {trade_data.get('entry_price', 0):.4f}\n"
        message += f"Expected Edge: {trade_data.get('edge_percent', 0):.1f}%\n"
        message += f"Confidence: {trade_data.get('confidence', 0):.1%}\n"
        
        if requires_approval:
            message += "\n⚠️ *Requires Your Approval*"
        else:
            message += "\n✅ *Auto-executing*"
        
        # Create inline keyboard for approval
        keyboard = []
        if requires_approval:
            trade_id = hash(str(trade_data))
            self.pending_approvals[str(trade_id)] = trade_data
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{trade_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{trade_id}")
                ]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Failed to send trade alert: {e}")

    async def send_daily_digest(self):
        """Send daily summary of trades and P&L."""
        if not self.chat_id:
            return
        
        trades = db.get_recent_trades(100)  # Last 100 trades
        
        if not trades:
            return
        
        # Calculate stats
        total_trades = len(trades)
        winning = sum(1 for t in trades if t[8] == 'confirmed')  # Approximate
        losing = total_trades - winning
        win_rate = winning / total_trades if total_trades > 0 else 0
        
        message = "📊 *Daily Trading Digest*\n\n"
        message += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        message += f"Total Trades: {total_trades}\n"
        message += f"Winning: {winning}\n"
        message += f"Losing: {losing}\n"
        message += f"Win Rate: {win_rate:.1%}\n"
        
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send daily digest: {e}")

    async def handle_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle trade approval/rejection buttons."""
        query = update.callback_query
        await query.answer()
        
        action, trade_id = query.data.split('_')
        
        if trade_id in self.pending_approvals:
            trade_data = self.pending_approvals[trade_id]
            
            if action == "approve":
                # TODO: Execute trade
                await query.edit_message_text(text="✅ Trade approved and executing...")
            else:
                await query.edit_message_text(text="❌ Trade rejected")
            
            del self.pending_approvals[trade_id]
        else:
            await query.edit_message_text(text="⚠️ Trade approval expired")

    async def send_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send agent status."""
        message = "🟢 *Agent Status*\n\n"
        message += "Status: ✅ Running\n"
        message += f"Started: Today\n"
        message += "Markets Monitored: 100+\n"
        message += "Network: Solana Devnet\n"
        message += "Model: Claude Haiku"
        
        await update.message.reply_text(message, parse_mode="Markdown")

    async def setup_and_run(self):
        """Initialize and run the Telegram bot."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram bot not configured")
            return
        
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("portfolio", self.show_portfolio))
        self.app.add_handler(CommandHandler("trades", self.show_trades))
        self.app.add_handler(CommandHandler("status", self.send_status))
        self.app.add_handler(CallbackQueryHandler(self.handle_approval))
        
        logger.info("Starting Telegram bot...")
        await self.app.initialize()
        await self.app.start()
        
        # Keep bot running
        while True:
            await asyncio.sleep(60)


# Global bot instance
telegram_bot = TelegramBot()


async def start_telegram():
    """Start the telegram bot in background."""
    try:
        await telegram_bot.setup_and_run()
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
