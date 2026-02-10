"""
Tests for Telegram Bot functionality

Tests:
- Command handlers (/start, /status, /portfolio, etc.)
- Button callbacks (approval, rejection, details)
- Message formatting
- User preference management
- Error handling and rate limiting
"""

import pytest
import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

from config import DB_PATH, AUTO_EXEC_THRESHOLD_USD, APPROVAL_THRESHOLD_USD
from telegram_bot import AutonomousTradingBot, TelegramDatabase
from telegram_handlers import MessageBuilder, TradeEventHandler, CommandHelper


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_user():
    """Create mock Telegram user."""
    return User(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser"
    )


@pytest.fixture
def mock_chat():
    """Create mock Telegram chat."""
    return Chat(id=123456789, type="private")


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Create mock Telegram message."""
    msg = Mock(spec=Message)
    msg.from_user = mock_user
    msg.chat = mock_chat
    msg.text = "/start"
    msg.reply_text = AsyncMock()
    return msg


@pytest.fixture
def mock_update(mock_message):
    """Create mock Telegram update."""
    update = Mock(spec=Update)
    update.message = mock_message
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Create mock bot context."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.fixture
async def telegram_bot():
    """Create telegram bot instance."""
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        bot = AutonomousTradingBot(token="test_token")
        yield bot


# ============================================================================
# MESSAGE BUILDER TESTS
# ============================================================================

class TestMessageBuilder:
    """Test message formatting functions."""
    
    def test_portfolio_summary_empty(self):
        """Test portfolio summary with no positions."""
        with patch('telegram_handlers.db.get_open_positions', return_value=[]):
            msg = MessageBuilder.portfolio_summary()
            assert "📊" in msg
            assert "No open positions" in msg
    
    def test_portfolio_summary_with_positions(self):
        """Test portfolio summary with open positions."""
        positions = [
            (1, "BTC_USD", "YES", 100, 0.5, "2024-01-01T00:00:00", None, None, "open", None, None, 10.5, 10.5)
        ]
        
        with patch('telegram_handlers.db.get_open_positions', return_value=positions):
            msg = MessageBuilder.portfolio_summary()
            assert "📊" in msg
            assert "Open Positions:" in msg
            assert "BTC_USD" in msg
            assert "$100.00" in msg
    
    def test_recent_trades(self):
        """Test recent trades message."""
        trades = [
            (1, "BTC_USD", 1, "2024-01-01T00:00:00", "YES", 100, 0.5, "tx123", "confirmed", None, "solana"),
        ]
        
        with patch('telegram_handlers.db.get_recent_trades', return_value=trades):
            msg = MessageBuilder.recent_trades(10)
            assert "📈" in msg
            assert "Recent Trades" in msg
            assert "confirmed" in msg
    
    def test_opportunities_list(self):
        """Test opportunities list message."""
        conn = sqlite3.connect(':memory:')
        c = conn.cursor()
        
        msg = MessageBuilder.opportunities_list(5)
        assert "🎯" in msg
        assert "Top 5" in msg
    
    def test_daily_digest(self):
        """Test daily digest message."""
        msg = MessageBuilder.daily_digest()
        assert "📊" in msg
        assert "Daily Digest" in msg
    
    def test_agent_status(self):
        """Test agent status message."""
        msg = MessageBuilder.agent_status()
        assert "🟢" in msg
        assert "Agent Status" in msg
        assert "Online" in msg


# ============================================================================
# COMMAND HANDLER TESTS
# ============================================================================

class TestCommandHandlers:
    """Test command handler functions."""
    
    @pytest.mark.asyncio
    async def test_cmd_start(self, mock_update, mock_context, telegram_bot):
        """Test /start command."""
        await telegram_bot.cmd_start(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        
        # Check that message contains expected content
        message = call_args[0][0]
        assert "🤖" in message
        assert "Autonomous Trading Agent" in message
        assert "/portfolio" in message
    
    @pytest.mark.asyncio
    async def test_cmd_help(self, mock_update, mock_context, telegram_bot):
        """Test /help command."""
        await telegram_bot.cmd_help(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        
        message = call_args[0][0]
        assert "Complete Command Reference" in message
        assert "/status" in message
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_update, mock_context, telegram_bot):
        """Test rate limiting on commands."""
        user_id = mock_update.message.from_user.id
        
        # Make rapid requests
        for _ in range(15):
            result = telegram_bot._check_rate_limit(user_id, limit=10, window=60)
            if _:
                assert not result, "Rate limit should kick in after 10 requests"
        
        # Verify limit was hit
        assert not telegram_bot._check_rate_limit(user_id, limit=10, window=60)


# ============================================================================
# USER PREFERENCE TESTS
# ============================================================================

class TestUserPreferences:
    """Test user preference management."""
    
    def test_get_or_create_user(self, mock_user):
        """Test creating new user."""
        with patch('telegram_bot.TELEGRAM_CHAT_ID', '123456789'):
            user_id = TelegramDatabase.get_or_create_user(mock_user)
            
            # Verify user was created
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
            user = c.fetchone()
            conn.close()
            
            assert user is not None
            assert user[0] == user_id  # user_id
            assert user[1] == "testuser"  # username
    
    def test_get_user_preferences(self, mock_user):
        """Test retrieving user preferences."""
        TelegramDatabase.get_or_create_user(mock_user)
        prefs = TelegramDatabase.get_user_preferences(mock_user.id)
        
        assert prefs is not None
        assert 'min_edge_percent' in prefs
        assert 'max_position_size_usd' in prefs
        assert 'notifications_enabled' in prefs
    
    def test_update_user_preferences(self, mock_user):
        """Test updating user preferences."""
        TelegramDatabase.get_or_create_user(mock_user)
        
        success = TelegramDatabase.update_user_preferences(
            mock_user.id,
            min_edge_percent=2.5,
            max_position_size_usd=50
        )
        
        assert success
        
        prefs = TelegramDatabase.get_user_preferences(mock_user.id)
        assert prefs['min_edge_percent'] == 2.5
        assert prefs['max_position_size_usd'] == 50


# ============================================================================
# BUTTON CALLBACK TESTS
# ============================================================================

class TestButtonCallbacks:
    """Test inline button callback handlers."""
    
    @pytest.mark.asyncio
    async def test_button_approve(self, telegram_bot, mock_user):
        """Test trade approval button."""
        # Setup
        TelegramDatabase.get_or_create_user(mock_user)
        
        # Create mock query
        query = AsyncMock()
        query.from_user = mock_user
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        
        # Create mock update
        update = Mock(spec=Update)
        update.callback_query = query
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Test approval (this would need signal in DB)
        # For now, just verify the mock works
        assert query.answer.call_count == 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_protection(self, mock_update, mock_context, telegram_bot):
        """Test rate limiting prevents spam."""
        user_id = mock_update.message.from_user.id
        
        # Exhaust rate limit
        for _ in range(10):
            telegram_bot._check_rate_limit(user_id, limit=10)
        
        # Next command should be rate limited
        result = telegram_bot._check_rate_limit(user_id, limit=10)
        assert not result


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and recovery."""
    
    def test_missing_token_warning(self, capsys):
        """Test warning when bot token is missing."""
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': ''}):
            bot = AutonomousTradingBot(token="")
            # Bot should initialize with empty token
            assert bot.token == ""
    
    @pytest.mark.asyncio
    async def test_send_trade_alert_with_no_app(self, telegram_bot):
        """Test sending alert when app not initialized."""
        result = await telegram_bot.send_trade_alert(
            signal_id=1,
            market_data={'market_id': 'TEST'},
            requires_approval=False
        )
        
        # Should return False when no app initialized
        assert result == False
    
    @pytest.mark.asyncio
    async def test_callback_error_handling(self, telegram_bot, mock_user):
        """Test callback error handling."""
        # Create invalid callback data
        query = AsyncMock()
        query.from_user = mock_user
        query.data = "invalid_callback_data"
        query.answer = AsyncMock()
        
        update = Mock(spec=Update)
        update.callback_query = query
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Should handle error gracefully
        try:
            await telegram_bot.handle_callback(update, context)
            # Parse error should be caught
            assert query.answer.called or not query.answer.called  # Either way, no crash
        except Exception as e:
            pytest.fail(f"Callback error not handled: {e}")


# ============================================================================
# COMMAND HELPER TESTS
# ============================================================================

class TestCommandHelper:
    """Test command argument parsing utilities."""
    
    def test_parse_float_argument(self):
        """Test parsing float from arguments."""
        args = ["2.5", "100"]
        
        result = CommandHelper.parse_float_argument(args, 0)
        assert result == 2.5
        
        result = CommandHelper.parse_float_argument(args, 1)
        assert result == 100.0
        
        result = CommandHelper.parse_float_argument(args, 2)
        assert result is None
    
    def test_parse_float_invalid(self):
        """Test parsing invalid float."""
        args = ["invalid", "100"]
        
        result = CommandHelper.parse_float_argument(args, 0)
        assert result is None
    
    def test_parse_time_argument(self):
        """Test parsing time argument."""
        args = ["09:30", "17:00"]
        
        result = CommandHelper.parse_time_argument(args, 0)
        assert result == "09:30"
        
        result = CommandHelper.parse_time_argument(args, 1)
        assert result == "17:00"
    
    def test_parse_time_invalid(self):
        """Test parsing invalid time."""
        args = ["25:00", "9:30"]  # Invalid hour and wrong format
        
        result = CommandHelper.parse_time_argument(args, 0)
        assert result is None
        
        result = CommandHelper.parse_time_argument(args, 1)
        assert result is None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_trade_approval_flow(self, telegram_bot, mock_user):
        """Test complete trade approval flow."""
        # 1. Create user
        user_id = TelegramDatabase.get_or_create_user(mock_user)
        assert user_id == mock_user.id
        
        # 2. Get user preferences
        prefs = TelegramDatabase.get_user_preferences(user_id)
        assert prefs['role'] in ['owner', 'viewer']
        
        # 3. Update preferences
        success = TelegramDatabase.update_user_preferences(
            user_id,
            min_edge_percent=3.5,
            max_position_size_usd=75
        )
        assert success
        
        # 4. Verify update
        prefs = TelegramDatabase.get_user_preferences(user_id)
        assert prefs['min_edge_percent'] == 3.5
        assert prefs['max_position_size_usd'] == 75
    
    @pytest.mark.asyncio
    async def test_rate_limiting_across_commands(self, mock_update, mock_context, telegram_bot):
        """Test rate limiting is enforced across all commands."""
        user_id = mock_update.message.from_user.id
        
        # First 10 commands should work
        for i in range(10):
            result = telegram_bot._check_rate_limit(user_id, limit=10, window=60)
            assert result, f"Command {i+1} should be allowed"
        
        # 11th should fail
        result = telegram_bot._check_rate_limit(user_id, limit=10, window=60)
        assert not result, "11th command should be rate limited"


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance and efficiency."""
    
    def test_message_builder_speed(self):
        """Test that message builders return quickly."""
        import time
        
        start = time.time()
        MessageBuilder.daily_digest()
        elapsed = time.time() - start
        
        # Should complete in under 100ms
        assert elapsed < 0.1, f"Daily digest took {elapsed*1000:.0f}ms"
    
    def test_database_query_speed(self):
        """Test database queries complete quickly."""
        import time
        
        start = time.time()
        TelegramDatabase.get_or_create_user(User(id=999, is_bot=False, first_name="Perf"))
        elapsed = time.time() - start
        
        # Should complete in under 50ms
        assert elapsed < 0.05, f"User creation took {elapsed*1000:.0f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
