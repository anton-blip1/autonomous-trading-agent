"""
Telegram Bot Handlers - Modular command and event handlers

Provides:
- Command handlers for all trading agent commands
- Message builders for formatted output
- Event handlers for trade notifications
- User preference handlers
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import DB_PATH, AUTO_EXEC_THRESHOLD_USD, APPROVAL_THRESHOLD_USD
from database import db


logger = logging.getLogger(__name__)


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================

class MessageBuilder:
    """Builds formatted Telegram messages for various events."""
    
    @staticmethod
    def portfolio_summary() -> str:
        """Build portfolio summary message."""
        positions = db.get_open_positions()
        
        message = "📊 *Portfolio Summary*\n\n"
        
        if not positions:
            message += "No open positions\n"
            return message
        
        # Calculate stats
        total_exposure = 0
        total_pnl = 0
        winning_positions = 0
        
        message += "*Open Positions:*\n"
        
        for pos in positions[:15]:
            pos_id, market_id, side, amount, entry_price, entry_time, sl, pt, status, exit_price, exit_time, pnl, pnl_pct = pos
            
            market_display = market_id[:25].replace('_', ' ').title()
            message += f"• {market_display[:20]}\n"
            message += f"  {side:3} | ${amount:7.2f} | {entry_price:.4f}\n"
            
            total_exposure += amount
            
            if pnl is not None and pnl > 0:
                winning_positions += 1
                total_pnl += pnl
                message += f"  ✅ +${pnl:.2f} ({pnl_pct:+.1f}%)\n"
            elif pnl is not None:
                total_pnl += pnl
                message += f"  🔴 ${pnl:.2f} ({pnl_pct:+.1f}%)\n"
        
        if len(positions) > 15:
            message += f"\n... and {len(positions) - 15} more positions\n"
        
        message += f"\n*Exposure:* ${total_exposure:.2f}\n"
        message += f"*P&L:* ${total_pnl:+.2f}\n"
        message += f"*Winning:* {winning_positions}/{len(positions)}\n"
        
        return message
    
    @staticmethod
    def recent_trades(limit: int = 10) -> str:
        """Build recent trades message."""
        trades = db.get_recent_trades(limit)
        
        message = f"📈 *Recent Trades (Last {limit})*\n\n"
        
        if not trades:
            message += "No trades executed yet\n"
            return message
        
        # Calculate stats
        wins = 0
        losses = 0
        total_pnl = 0
        
        for i, trade in enumerate(trades, 1):
            trade_id, market_id, signal_id, timestamp, side, amount_usd, entry_price, tx_hash, status, error_msg, chain = trade
            
            market_display = market_id.replace('_', ' ')[:20]
            
            message += f"{i}. {market_display} | {side:3} ${amount_usd:6.2f}\n"
            message += f"   Price: {entry_price:.4f} | {timestamp[:10]}\n"
            message += f"   Status: {status}\n\n"
            
            if status == 'confirmed':
                wins += 1
            else:
                losses += 1
        
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        message += f"*Summary:*\n"
        message += f"Wins: {wins} | Losses: {losses} | Rate: {win_rate:.0f}%\n"
        
        return message
    
    @staticmethod
    def performance_stats() -> str:
        """Build performance statistics message."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get stats
        c.execute("SELECT COUNT(*) FROM trades WHERE status = 'confirmed'")
        confirmed_trades = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM trades WHERE status = 'failed'")
        failed_trades = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM positions WHERE status = 'open'")
        open_positions = c.fetchone()[0]
        
        c.execute("SELECT SUM(pnl_usd) FROM positions WHERE pnl_usd IS NOT NULL")
        total_pnl = c.fetchone()[0] or 0
        
        # Today's stats
        c.execute("""
            SELECT COUNT(*) FROM trades 
            WHERE DATE(timestamp) = DATE('now')
        """)
        today_trades = c.fetchone()[0]
        
        c.execute("""
            SELECT SUM(amount_usd) FROM trades 
            WHERE DATE(timestamp) = DATE('now')
        """)
        today_volume = c.fetchone()[0] or 0
        
        conn.close()
        
        message = "📊 *Performance Statistics*\n\n"
        message += f"*All-Time:*\n"
        message += f"Confirmed Trades: {confirmed_trades}\n"
        message += f"Failed Trades: {failed_trades}\n"
        message += f"Win Rate: {(confirmed_trades/(confirmed_trades+failed_trades)*100 if confirmed_trades+failed_trades > 0 else 0):.0f}%\n"
        message += f"Total P&L: ${total_pnl:+.2f}\n\n"
        
        message += f"*Today:*\n"
        message += f"Trades: {today_trades}\n"
        message += f"Volume: ${today_volume:.2f}\n\n"
        
        message += f"*Current:*\n"
        message += f"Open Positions: {open_positions}\n"
        
        return message
    
    @staticmethod
    def opportunities_list(limit: int = 5) -> str:
        """Build list of current opportunities."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT signal_id, market_id, edge_percent, confidence, decision, suggested_position_size
            FROM signals
            WHERE executed = 0 AND decision != 'PASS'
            ORDER BY (edge_percent * confidence) DESC
            LIMIT ?
        """, (limit,))
        
        signals = c.fetchall()
        conn.close()
        
        message = f"🎯 *Top {limit} Opportunities*\n\n"
        
        if not signals:
            message += "No immediate opportunities detected.\n"
            message += "Agent is monitoring markets...\n"
            return message
        
        for i, sig in enumerate(signals, 1):
            sig_id, market_id, edge, confidence, decision, size = sig
            
            # Format market name
            market_display = market_id.replace('_', ' ')[:30].title()
            
            # Color code by size
            if size <= AUTO_EXEC_THRESHOLD_USD:
                size_emoji = "🟢"
            elif size <= APPROVAL_THRESHOLD_USD:
                size_emoji = "🟡"
            else:
                size_emoji = "🔴"
            
            message += f"{i}. {market_display}\n"
            message += f"   Edge: {edge:+.1f}% | Conf: {confidence:.0%}\n"
            message += f"   Signal: {decision} | {size_emoji} ${size:.2f}\n\n"
        
        return message
    
    @staticmethod
    def agent_status() -> str:
        """Build agent status message."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM positions WHERE status = 'open'")
        open_pos = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM trades WHERE status = 'pending'")
        pending_trades = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM signals WHERE executed = 0")
        pending_signals = c.fetchone()[0]
        
        # Get latest market scan time
        c.execute("SELECT MAX(last_updated) FROM markets")
        last_scan = c.fetchone()[0]
        
        conn.close()
        
        message = "🟢 *Agent Status - Online*\n\n"
        message += "Status: ✅ Running normally\n"
        message += f"Open Positions: {open_pos}\n"
        message += f"Pending Trades: {pending_trades}\n"
        message += f"Pending Signals: {pending_signals}\n"
        message += f"Last Scan: {last_scan if last_scan else 'Just now'}\n\n"
        message += "Network: Solana Devnet\n"
        message += "Model: Claude Haiku\n"
        message += "Scan Interval: 5 seconds\n"
        
        return message
    
    @staticmethod
    def daily_digest() -> str:
        """Build comprehensive daily digest."""
        today = datetime.now().date()
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get today's top opportunities
        c.execute("""
            SELECT signal_id, market_id, edge_percent, confidence, decision, suggested_position_size
            FROM signals
            WHERE DATE(timestamp) = DATE(?)
            AND decision != 'PASS'
            ORDER BY (edge_percent * confidence) DESC
            LIMIT 5
        """, (today.isoformat(),))
        
        signals = c.fetchall()
        
        # Get today's trades
        c.execute("""
            SELECT COUNT(*), SUM(amount_usd), COUNT(CASE WHEN status='confirmed' THEN 1 END)
            FROM trades
            WHERE DATE(timestamp) = DATE(?)
        """, (today.isoformat(),))
        
        trades_today = c.fetchone()
        trade_count, trade_volume, winning_trades = trades_today
        trade_count = trade_count or 0
        trade_volume = trade_volume or 0
        winning_trades = winning_trades or 0
        
        # Get yesterday's performance
        yesterday = today - timedelta(days=1)
        c.execute("""
            SELECT COUNT(*), COUNT(CASE WHEN status='confirmed' THEN 1 END)
            FROM trades
            WHERE DATE(timestamp) = DATE(?)
        """, (yesterday.isoformat(),))
        
        yesterday_trades = c.fetchone()
        yesterday_count, yesterday_wins = yesterday_trades
        yesterday_count = yesterday_count or 0
        yesterday_wins = yesterday_wins or 0
        
        # Get current portfolio P&L
        c.execute("""
            SELECT SUM(pnl_usd), COUNT(*) FROM positions
            WHERE status = 'open' AND pnl_usd IS NOT NULL
        """)
        
        current_pnl = c.fetchone()
        current_pnl_usd, open_pos_count = current_pnl
        current_pnl_usd = current_pnl_usd or 0
        
        conn.close()
        
        message = f"📊 *Daily Digest - {today.strftime('%B %d')}*\n\n"
        
        # Top opportunities
        if signals:
            message += "🎯 *Top Opportunities Today:*\n"
            for i, sig in enumerate(signals, 1):
                sig_id, market_id, edge, confidence, decision, size = sig
                market_display = market_id.replace('_', ' ')[:25].title()
                message += f"{i}. {market_display}\n"
                message += f"   {edge:+.1f}% edge | {confidence:.0%} confidence\n"
                message += f"   {decision} ${size:.2f}\n\n"
        
        # Today's performance
        message += "*📈 Today's Performance:*\n"
        message += f"Trades: {trade_count}\n"
        message += f"Volume: ${trade_volume:.2f}\n"
        if trade_count > 0:
            win_rate = (winning_trades / trade_count) * 100
            message += f"Win Rate: {win_rate:.0f}%\n"
        
        # Yesterday's summary
        if yesterday_count > 0:
            message += f"\n*Yesterday:*\n"
            message += f"Trades: {yesterday_count}\n"
            message += f"Wins: {yesterday_wins}\n"
        
        # Current portfolio
        message += f"\n*Portfolio Status:*\n"
        message += f"Open Positions: {open_pos_count}\n"
        if current_pnl_usd != 0:
            emoji = "🟢" if current_pnl_usd > 0 else "🔴"
            message += f"{emoji} Unrealized P&L: ${current_pnl_usd:+.2f}\n"
        
        message += f"\n_Updated: {datetime.now().strftime('%H:%M UTC')}_"
        
        return message
    
    @staticmethod
    def trade_notification(trade_id: int) -> str:
        """Build notification for executed trade."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT market_id, side, amount_usd, entry_price, status, timestamp
            FROM trades
            WHERE trade_id = ?
        """, (trade_id,))
        
        trade = c.fetchone()
        conn.close()
        
        if not trade:
            return "⚠️ Trade not found"
        
        market_id, side, amount_usd, entry_price, status, timestamp = trade
        
        emoji = "✅" if status == "confirmed" else "⏳"
        
        message = f"{emoji} *Trade {'Confirmed' if status == 'confirmed' else 'Pending'}*\n\n"
        message += f"Market: `{market_id[:35]}`\n"
        message += f"Side: {side}\n"
        message += f"Size: ${amount_usd:.2f}\n"
        message += f"Price: {entry_price:.4f}\n"
        message += f"Time: {timestamp[:19]}\n"
        
        return message
    
    @staticmethod
    def position_closed_notification(position_id: int) -> str:
        """Build notification for closed position."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT market_id, side, amount_usd, entry_price, exit_price, pnl_usd, pnl_percent
            FROM positions
            WHERE position_id = ?
        """, (position_id,))
        
        pos = c.fetchone()
        conn.close()
        
        if not pos:
            return "⚠️ Position not found"
        
        market_id, side, amount_usd, entry_price, exit_price, pnl_usd, pnl_pct = pos
        
        emoji = "🎉" if pnl_usd > 0 else "⚠️"
        
        message = f"{emoji} *Position Closed*\n\n"
        message += f"Market: {market_id[:30]}\n"
        message += f"Side: {side}\n"
        message += f"Entry: ${amount_usd:.2f} @ {entry_price:.4f}\n"
        if exit_price:
            message += f"Exit: {exit_price:.4f}\n"
        if pnl_usd is not None:
            message += f"P&L: ${pnl_usd:+.2f} ({pnl_pct:+.1f}%)\n"
        
        return message


# ============================================================================
# EVENT HANDLERS
# ============================================================================

class TradeEventHandler:
    """Handles trade-related events and notifications."""
    
    @staticmethod
    async def on_trade_opportunity(bot, signal_id: int, market_data: Dict) -> bool:
        """Handle new trade opportunity."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("""
                SELECT suggested_position_size FROM signals WHERE signal_id = ?
            """, (signal_id,))
            
            size_result = c.fetchone()
            conn.close()
            
            if not size_result:
                return False
            
            size = size_result[0]
            
            # Determine if approval is needed
            requires_approval = (
                AUTO_EXEC_THRESHOLD_USD < size <= APPROVAL_THRESHOLD_USD
            )
            
            # Send alert
            return await bot.send_trade_alert(signal_id, market_data, requires_approval)
        
        except Exception as e:
            logger.error(f"Trade opportunity handler error: {e}")
            return False
    
    @staticmethod
    async def on_trade_executed(bot, trade_id: int) -> bool:
        """Handle trade execution."""
        try:
            message = MessageBuilder.trade_notification(trade_id)
            
            if bot.app and bot.chat_id:
                await bot.app.bot.send_message(
                    chat_id=bot.chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
            return True
        except Exception as e:
            logger.error(f"Trade execution handler error: {e}")
            return False
    
    @staticmethod
    async def on_position_closed(bot, position_id: int) -> bool:
        """Handle position closure."""
        try:
            message = MessageBuilder.position_closed_notification(position_id)
            
            if bot.app and bot.chat_id:
                await bot.app.bot.send_message(
                    chat_id=bot.chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
            return True
        except Exception as e:
            logger.error(f"Position closed handler error: {e}")
            return False


# ============================================================================
# COMMAND HELPERS
# ============================================================================

class CommandHelper:
    """Helper functions for command handlers."""
    
    @staticmethod
    def parse_float_argument(args: List[str], index: int = 0) -> Optional[float]:
        """Parse float from command arguments."""
        if len(args) > index:
            try:
                return float(args[index])
            except ValueError:
                return None
        return None
    
    @staticmethod
    def parse_time_argument(args: List[str], index: int = 0) -> Optional[str]:
        """Parse HH:MM time from command arguments."""
        if len(args) > index:
            time_str = args[index]
            if len(time_str) == 5 and time_str[2] == ':':
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if 0 <= hour < 24 and 0 <= minute < 60:
                        return time_str
                except ValueError:
                    return None
        return None


# ============================================================================
# USER PREFERENCE HANDLERS
# ============================================================================

class PreferenceHandler:
    """Handles user preference updates."""
    
    @staticmethod
    async def set_min_edge(bot_instance, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set minimum edge requirement."""
        if not update.message:
            return
        
        try:
            from telegram_bot import TelegramDatabase
            
            args = update.message.text.split()[1:]
            edge = CommandHelper.parse_float_argument(args)
            
            if edge is None or edge < 0 or edge > 100:
                await update.message.reply_text("❌ Invalid edge. Use: /set_min_edge 2.5")
                return
            
            user_id = TelegramDatabase.get_or_create_user(update.message.from_user)
            
            if TelegramDatabase.update_user_preferences(user_id, min_edge_percent=edge):
                await update.message.reply_text(
                    f"✅ Minimum edge set to {edge:.1f}%\n\n"
                    f"Now only trading opportunities with {edge:.1f}%+ edge will be considered."
                )
            else:
                await update.message.reply_text("❌ Failed to update preference")
        
        except Exception as e:
            logger.error(f"Set min edge error: {e}")
            await update.message.reply_text("❌ Error updating preference")
    
    @staticmethod
    async def set_max_position_size(bot_instance, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set maximum position size."""
        if not update.message:
            return
        
        try:
            from telegram_bot import TelegramDatabase
            
            args = update.message.text.split()[1:]
            size = CommandHelper.parse_float_argument(args)
            
            if size is None or size <= 0:
                await update.message.reply_text("❌ Invalid size. Use: /set_max_size 100")
                return
            
            user_id = TelegramDatabase.get_or_create_user(update.message.from_user)
            
            if TelegramDatabase.update_user_preferences(user_id, max_position_size_usd=size):
                await update.message.reply_text(
                    f"✅ Max position size set to ${size:.2f}\n\n"
                    f"No individual trade will exceed this amount."
                )
            else:
                await update.message.reply_text("❌ Failed to update preference")
        
        except Exception as e:
            logger.error(f"Set max size error: {e}")
            await update.message.reply_text("❌ Error updating preference")
    
    @staticmethod
    async def toggle_daily_digest(bot_instance, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Toggle daily digest on/off."""
        if not update.message:
            return
        
        try:
            from telegram_bot import TelegramDatabase
            
            user_id = TelegramDatabase.get_or_create_user(update.message.from_user)
            prefs = TelegramDatabase.get_user_preferences(user_id)
            
            if prefs:
                new_state = not prefs['daily_digest_enabled']
                
                if TelegramDatabase.update_user_preferences(user_id, daily_digest_enabled=new_state):
                    state_text = "✅ Enabled" if new_state else "❌ Disabled"
                    await update.message.reply_text(
                        f"Daily digest {state_text}\n\n"
                        f"You will {'receive' if new_state else 'not receive'} morning digests."
                    )
                else:
                    await update.message.reply_text("❌ Failed to update preference")
            else:
                await update.message.reply_text("❌ User not found")
        
        except Exception as e:
            logger.error(f"Toggle digest error: {e}")
            await update.message.reply_text("❌ Error updating preference")
