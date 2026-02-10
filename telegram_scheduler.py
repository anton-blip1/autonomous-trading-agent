"""
Telegram Daily Digest Scheduler

Sends daily market digest and performance summaries at configured times.
Supports multiple users with different timezone preferences.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, time, timedelta
from typing import Optional, Dict, List
from pathlib import Path
import pytz

from config import DB_PATH
from telegram_handlers import MessageBuilder


logger = logging.getLogger(__name__)


class DigestScheduler:
    """Schedules and sends daily digest messages."""
    
    def __init__(self, telegram_bot):
        self.bot = telegram_bot
        self.running = False
        self.tasks: Dict[int, asyncio.Task] = {}  # user_id -> task
    
    async def start(self) -> None:
        """Start the digest scheduler."""
        if not self.bot or not self.bot.app:
            logger.warning("Telegram bot not initialized, skipping scheduler")
            return
        
        self.running = True
        logger.info("📅 Daily digest scheduler started")
        
        # Start background task
        try:
            await self._scheduler_loop()
        except asyncio.CancelledError:
            logger.info("Digest scheduler stopped")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            self.running = False
    
    async def stop(self) -> None:
        """Stop the scheduler and cancel all tasks."""
        self.running = False
        
        for task in self.tasks.values():
            task.cancel()
        
        logger.info("📅 Daily digest scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self.running:
            try:
                # Check every minute if it's time to send digest
                now = datetime.now()
                
                # Get all users with daily digest enabled
                users = self._get_digest_users()
                
                for user_id, digest_time, timezone in users:
                    await self._check_and_send_digest(user_id, digest_time, timezone, now)
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    def _get_digest_users(self) -> List[tuple]:
        """Get all users with daily digest enabled."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            c.execute("""
                SELECT user_id, digest_time, timezone
                FROM telegram_users
                WHERE daily_digest_enabled = 1
            """)
            
            users = c.fetchall()
            return users
        finally:
            conn.close()
    
    def _should_send_digest(self, digest_time: str, timezone: str, now: datetime) -> bool:
        """Check if it's time to send digest for this user."""
        try:
            # Parse digest time (HH:MM format)
            hour, minute = map(int, digest_time.split(':'))
            
            # Get user's local time
            tz = pytz.timezone(timezone) if timezone != 'UTC' else pytz.UTC
            user_now = now.astimezone(tz)
            
            # Check if current time matches digest time (within 1 minute window)
            digest_hour = hour
            digest_minute = minute
            
            if (user_now.hour == digest_hour and 
                user_now.minute == digest_minute):
                return True
            
            return False
        except Exception as e:
            logger.error(f"Time check error: {e}")
            return False
    
    async def _check_and_send_digest(self, user_id: int, digest_time: str, timezone: str, now: datetime) -> None:
        """Check if it's time to send digest and send it."""
        try:
            if not self._should_send_digest(digest_time, timezone, now):
                return
            
            # Check if already sent today for this user
            if self._already_sent_today(user_id):
                return
            
            # Build and send digest
            digest_message = MessageBuilder.daily_digest()
            
            # Get user's chat ID (same as main chat_id for now)
            if self.bot.chat_id:
                await self.bot.app.bot.send_message(
                    chat_id=self.bot.chat_id,
                    text=digest_message,
                    parse_mode="Markdown"
                )
                
                # Record that we sent it
                self._record_digest_sent(user_id)
                
                logger.info(f"✅ Daily digest sent to user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to send digest to user {user_id}: {e}")
    
    def _already_sent_today(self, user_id: int) -> bool:
        """Check if digest was already sent to this user today."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            today = datetime.now().date().isoformat()
            
            c.execute("""
                SELECT COUNT(*) FROM telegram_messages
                WHERE user_id = ? 
                AND content_type = 'digest'
                AND DATE(created_at) = DATE(?)
            """, (user_id, today))
            
            count = c.fetchone()[0]
            conn.close()
            
            return count > 0
        except Exception as e:
            logger.error(f"Check sent error: {e}")
            return False
    
    def _record_digest_sent(self, user_id: int) -> bool:
        """Record that digest was sent."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO telegram_messages
                (user_id, chat_id, content_type, created_at)
                VALUES (?, ?, 'digest', CURRENT_TIMESTAMP)
            """, (user_id, self.bot.chat_id))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Record sent error: {e}")
            return False


class PerformanceSummaryScheduler:
    """Sends end-of-day and weekly performance summaries."""
    
    def __init__(self, telegram_bot):
        self.bot = telegram_bot
        self.running = False
    
    async def start(self) -> None:
        """Start the performance summary scheduler."""
        if not self.bot or not self.bot.app:
            logger.warning("Telegram bot not initialized, skipping performance scheduler")
            return
        
        self.running = True
        logger.info("📊 Performance summary scheduler started")
        
        try:
            await self._scheduler_loop()
        except asyncio.CancelledError:
            logger.info("Performance scheduler stopped")
        except Exception as e:
            logger.error(f"Performance scheduler error: {e}")
            self.running = False
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        logger.info("📊 Performance summary scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        last_eod_send = None
        last_weekly_send = None
        
        while self.running:
            try:
                now = datetime.now()
                
                # Send end-of-day summary at 17:00 UTC
                if (now.hour == 17 and now.minute == 0 and 
                    (last_eod_send is None or (now.date() > last_eod_send.date()))):
                    
                    await self._send_eod_summary()
                    last_eod_send = now
                
                # Send weekly summary every Monday at 09:00 UTC
                if (now.weekday() == 0 and now.hour == 9 and now.minute == 0 and
                    (last_weekly_send is None or (now.date() - last_weekly_send.date()).days >= 7)):
                    
                    await self._send_weekly_summary()
                    last_weekly_send = now
                
                # Check every minute
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _send_eod_summary(self) -> None:
        """Send end-of-day summary."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            today = datetime.now().date().isoformat()
            
            # Get today's stats
            c.execute("""
                SELECT COUNT(*), SUM(amount_usd), 
                       COUNT(CASE WHEN status='confirmed' THEN 1 END)
                FROM trades
                WHERE DATE(timestamp) = DATE(?)
            """, (today,))
            
            trade_data = c.fetchone()
            trade_count = trade_data[0] or 0
            trade_volume = trade_data[1] or 0
            wins = trade_data[2] or 0
            
            # Get current portfolio P&L
            c.execute("""
                SELECT SUM(pnl_usd) FROM positions
                WHERE status = 'open' AND pnl_usd IS NOT NULL
            """)
            
            pnl = c.fetchone()[0] or 0
            
            conn.close()
            
            message = "📊 *End of Day Summary*\n\n"
            message += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            message += f"*Today's Activity:*\n"
            message += f"Trades Executed: {trade_count}\n"
            message += f"Total Volume: ${trade_volume:.2f}\n"
            
            if trade_count > 0:
                win_rate = (wins / trade_count) * 100
                message += f"Win Rate: {win_rate:.0f}%\n"
            
            message += f"\n*Portfolio Status:*\n"
            emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
            message += f"{emoji} Unrealized P&L: ${pnl:+.2f}\n"
            
            message += f"\n_Summary sent at {datetime.now().strftime('%H:%M UTC')}_"
            
            if self.bot.chat_id:
                await self.bot.app.bot.send_message(
                    chat_id=self.bot.chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
            
            logger.info("✅ End-of-day summary sent")
        
        except Exception as e:
            logger.error(f"Failed to send EOD summary: {e}")
    
    async def _send_weekly_summary(self) -> None:
        """Send weekly performance summary."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            one_week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
            
            # Get weekly stats
            c.execute("""
                SELECT COUNT(*), SUM(amount_usd),
                       COUNT(CASE WHEN status='confirmed' THEN 1 END),
                       AVG(amount_usd)
                FROM trades
                WHERE DATE(timestamp) > DATE(?)
            """, (one_week_ago,))
            
            stats = c.fetchone()
            trade_count = stats[0] or 0
            total_volume = stats[1] or 0
            wins = stats[2] or 0
            avg_trade = stats[3] or 0
            
            # Get best performing market
            c.execute("""
                SELECT market_id, COUNT(*), SUM(CASE WHEN status='confirmed' THEN 1 ELSE 0 END)
                FROM trades
                WHERE DATE(timestamp) > DATE(?)
                GROUP BY market_id
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """, (one_week_ago,))
            
            best_market = c.fetchone()
            
            conn.close()
            
            message = "📈 *Weekly Performance Summary*\n\n"
            message += f"Period: {one_week_ago} to {datetime.now().date()}\n\n"
            
            message += f"*Activity:*\n"
            message += f"Total Trades: {trade_count}\n"
            message += f"Total Volume: ${total_volume:.2f}\n"
            
            if trade_count > 0:
                win_rate = (wins / trade_count) * 100
                message += f"Win Rate: {win_rate:.0f}%\n"
                message += f"Avg Trade Size: ${avg_trade:.2f}\n"
            
            if best_market:
                market_id, count, wins = best_market
                market_display = market_id.replace('_', ' ')[:30].title()
                message += f"\n*Top Market:*\n"
                message += f"{market_display}\n"
                message += f"Trades: {count}\n"
            
            message += f"\n_Summary sent at {datetime.now().strftime('%H:%M UTC')}_"
            
            if self.bot.chat_id:
                await self.bot.app.bot.send_message(
                    chat_id=self.bot.chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
            
            logger.info("✅ Weekly summary sent")
        
        except Exception as e:
            logger.error(f"Failed to send weekly summary: {e}")


async def start_all_schedulers(telegram_bot):
    """Start all schedulers concurrently."""
    digest_scheduler = DigestScheduler(telegram_bot)
    perf_scheduler = PerformanceSummaryScheduler(telegram_bot)
    
    try:
        # Run both schedulers concurrently
        await asyncio.gather(
            digest_scheduler.start(),
            perf_scheduler.start()
        )
    except asyncio.CancelledError:
        await digest_scheduler.stop()
        await perf_scheduler.stop()
    except Exception as e:
        logger.error(f"Scheduler startup error: {e}")
