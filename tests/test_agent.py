"""
Unit tests for the autonomous trading agent.
Tests: Claude tool use, position sizing, market analysis.
"""
import unittest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import AutonomousAgent
from market_scanner import MarketScanner
from solana_integration import SolanaWallet, TradeExecutor
from config import KELLY_FRACTION, MIN_EDGE_PERCENT


class TestAgent(unittest.TestCase):
    """Test trading agent functionality."""

    def setUp(self):
        self.agent = AutonomousAgent()

    def test_agent_initialization(self):
        """Test agent initializes with correct bankroll."""
        self.assertEqual(self.agent.bankroll, 1000)
        self.assertEqual(self.agent.trades_executed, 0)

    def test_kelly_calculation(self):
        """Test Kelly Criterion position sizing."""
        tool_input = {
            "bankroll": 1000,
            "win_probability": 0.6,
            "win_payoff": 2.0,
            "loss_payoff": 0.0
        }
        
        result = self.agent._process_tool_call("calculate_kelly_position", tool_input)
        result_data = json.loads(result)
        
        # Kelly = (p*b - (1-p)) / b = (0.6*2 - 0.4) / 2 = 0.2
        # With KELLY_FRACTION=0.25: 0.2 * 0.25 = 0.05
        # Position = 1000 * 0.05 = $50
        self.assertGreater(result_data["position_size_usd"], 0)
        self.assertLess(result_data["position_size_usd"], 100)

    def test_edge_calculation(self):
        """Test edge calculation for trades."""
        tool_input = {
            "market_id": "test_market",
            "fair_value": 0.65,
            "market_price": 0.55,
            "confidence": 0.75
        }
        
        result = self.agent._process_tool_call("evaluate_market_edge", tool_input)
        result_data = json.loads(result)
        
        # Edge = |0.65 - 0.55| * 100 = 10%
        self.assertAlmostEqual(result_data["edge_percent"], 10.0, delta=0.1)
        self.assertTrue(result_data["has_edge"])  # 10% > MIN_EDGE_PERCENT (3%)
        self.assertEqual(result_data["recommendation"], "BUY")

    def test_insufficient_edge(self):
        """Test that trades below min edge are rejected."""
        tool_input = {
            "market_id": "test_market",
            "fair_value": 0.53,
            "market_price": 0.52,
            "confidence": 0.75
        }
        
        result = self.agent._process_tool_call("evaluate_market_edge", tool_input)
        result_data = json.loads(result)
        
        # Edge = 1% < MIN_EDGE_PERCENT (3%)
        self.assertFalse(result_data["has_edge"])


class TestMarketScanner(unittest.TestCase):
    """Test market scanner functionality."""

    def setUp(self):
        self.scanner = MarketScanner()

    def test_spread_calculation(self):
        """Test bid-ask spread calculation."""
        spread = self.scanner.calculate_spread(0.4, 0.6)
        expected = abs(0.4 - 0.6) / ((0.4 + 0.6) / 2)
        self.assertAlmostEqual(spread, expected, delta=0.01)

    def test_market_scoring(self):
        """Test market scoring logic."""
        market = {
            "market_id": "test",
            "platform": "polymarket",
            "title": "Test Market",
            "yes_price": 0.5,
            "no_price": 0.5,
            "volume_usd": 10000,
            "liquidity_usd": 5000,
        }
        
        score = self.scanner.score_market(market)
        
        self.assertGreater(score["overall_score"], 0)
        self.assertLess(score["overall_score"], 100)
        self.assertGreater(score["volume_score"], 0)
        self.assertGreater(score["liquidity_score"], 0)


class TestSolanaIntegration(unittest.TestCase):
    """Test Solana wallet and transaction functionality."""

    def setUp(self):
        self.wallet = SolanaWallet()
        self.executor = TradeExecutor()

    def test_wallet_address_generation(self):
        """Test wallet can generate address."""
        address = self.wallet.get_address()
        self.assertIsNotNone(address)
        self.assertGreater(len(address), 20)  # Solana addresses are ~44 chars

    def test_trade_creation(self):
        """Test creating a trade on Polymarket."""
        trade = self.executor.create_polymarket_trade(
            market_id="test_market",
            side="YES",
            amount_usd=10.0,
            price=0.6
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "YES")
        self.assertEqual(trade["amount_usd"], 10.0)
        self.assertEqual(trade["platform"], "polymarket")

    def test_kalshi_trade_creation(self):
        """Test creating a trade on Kalshi."""
        trade = self.executor.create_kalshi_trade(
            market_id="kalshi_weather",
            side="NO",
            amount_usd=25.0,
            price=0.45
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "NO")
        self.assertEqual(trade["platform"], "kalshi")


class TestPositionSizing(unittest.TestCase):
    """Test position sizing strategies."""

    def setUp(self):
        self.agent = AutonomousAgent()

    def test_kelly_conservative(self):
        """Test that Kelly Criterion is conservative with fractional Kelly."""
        # High edge, high confidence
        tool_input = {
            "bankroll": 1000,
            "win_probability": 0.8,
            "win_payoff": 2.0,
            "loss_payoff": 0.0
        }
        
        result = json.loads(self.agent._process_tool_call("calculate_kelly_position", tool_input))
        position_size = result["position_size_usd"]
        
        # Should never exceed Kelly limit
        self.assertLess(position_size / 1000, 1.0)  # Max 100% of bankroll
        self.assertGreater(position_size, 0)


class TestIntegration(unittest.TestCase):
    """Integration tests: full workflow."""

    def test_scanner_to_agent_workflow(self):
        """Test market data flows from scanner to agent decisions."""
        scanner = MarketScanner()
        market = {
            "market_id": "integration_test",
            "platform": "polymarket",
            "title": "Test Market",
            "yes_price": 0.55,
            "no_price": 0.45,
            "volume_usd": 50000,
            "liquidity_usd": 10000,
        }
        
        scored = scanner.score_market(market)
        
        self.assertIn("overall_score", scored)
        self.assertGreater(scored["overall_score"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
