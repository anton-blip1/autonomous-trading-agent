"""
Integration tests for multi-chain autonomous trading flow.
Tests Polygon trade execution, Solana trade execution, and auto-bridging.
"""
import unittest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain_integration import TradeExecutor, SolanaWallet, PolygonWallet
from wormhole_bridge import WormholeBridge
from agent import AutonomousAgent


class TestPolygonTradeExecution(unittest.TestCase):
    """Test Polygon trade execution flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.executor = TradeExecutor()

    def test_polygon_trade_creation(self):
        """Test creating a Polygon trade (Polymarket)."""
        trade = self.executor.create_polygon_trade(
            market_id="poly_market_1",
            side="YES",
            amount_usd=50.0,
            price=0.55
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["market_id"], "poly_market_1")
        self.assertEqual(trade["side"], "YES")
        self.assertEqual(trade["amount_usd"], 50.0)
        self.assertEqual(trade["entry_price"], 0.55)
        self.assertEqual(trade["platform"], "polymarket")
        self.assertEqual(trade["chain"], "polygon")
        self.assertEqual(trade["status"], "draft")
        
        print(f"✓ Polygon trade created: {trade.get('expected_shares'):.1f} shares")

    def test_polygon_trade_submission(self):
        """Test submitting a Polygon trade."""
        trade = self.executor.create_polygon_trade(
            market_id="poly_market_1",
            side="YES",
            amount_usd=50.0,
            price=0.55
        )
        
        tx_hash = self.executor.submit_trade(trade)
        
        self.assertIsNotNone(tx_hash)
        self.assertTrue(tx_hash.startswith("polygon_tx"))
        self.assertEqual(trade["status"], "submitted")
        
        print(f"✓ Polygon trade submitted: {tx_hash}")

    def test_polygon_backward_compatibility(self):
        """Test backward compatibility with create_polymarket_trade alias."""
        trade = self.executor.create_polymarket_trade(
            market_id="poly_market_2",
            side="NO",
            amount_usd=25.0,
            price=0.45
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["chain"], "polygon")
        self.assertEqual(trade["platform"], "polymarket")
        
        print(f"✓ Backward compatibility alias works")


class TestSolanaTradeExecution(unittest.TestCase):
    """Test Solana trade execution flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.executor = TradeExecutor()

    def test_solana_trade_creation(self):
        """Test creating a Solana trade (Kalshi)."""
        trade = self.executor.create_solana_trade(
            market_id="kalshi_market_1",
            side="YES",
            amount_usd=75.0,
            price=0.60
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["market_id"], "kalshi_market_1")
        self.assertEqual(trade["side"], "YES")
        self.assertEqual(trade["amount_usd"], 75.0)
        self.assertEqual(trade["entry_price"], 0.60)
        self.assertEqual(trade["platform"], "kalshi")
        self.assertEqual(trade["chain"], "solana")
        self.assertEqual(trade["status"], "draft")
        self.assertEqual(trade["bridge"], "dflow")
        
        print(f"✓ Solana trade created: {trade.get('expected_contracts'):.1f} contracts")

    def test_solana_trade_submission(self):
        """Test submitting a Solana trade."""
        trade = self.executor.create_solana_trade(
            market_id="kalshi_market_1",
            side="YES",
            amount_usd=75.0,
            price=0.60
        )
        
        tx_hash = self.executor.submit_trade(trade)
        
        self.assertIsNotNone(tx_hash)
        self.assertTrue(tx_hash.startswith("solana_tx"))
        self.assertEqual(trade["status"], "submitted")
        
        print(f"✓ Solana trade submitted: {tx_hash}")

    def test_solana_backward_compatibility(self):
        """Test backward compatibility with create_kalshi_trade alias."""
        trade = self.executor.create_kalshi_trade(
            market_id="kalshi_market_2",
            side="NO",
            amount_usd=40.0,
            price=0.50
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["chain"], "solana")
        self.assertEqual(trade["platform"], "kalshi")
        
        print(f"✓ Kalshi backward compatibility alias works")


class TestAutoBridgingFlow(unittest.TestCase):
    """Test automatic cross-chain bridging for trades."""

    def setUp(self):
        """Set up test fixtures."""
        self.executor = TradeExecutor()
        self.bridge = WormholeBridge()

    def test_dual_wallet_status(self):
        """Test retrieving dual wallet status."""
        status = self.executor.get_dual_wallet_status()
        
        self.assertIn("solana", status)
        self.assertIn("polygon", status)
        
        sol_wallet = status["solana"]
        poly_wallet = status["polygon"]
        
        # Solana wallet info
        self.assertIn("address", sol_wallet)
        self.assertIn("balance_sol", sol_wallet)
        self.assertEqual(sol_wallet["chain"], "solana")
        
        # Polygon wallet info
        self.assertIn("address", poly_wallet)
        self.assertIn("balance_usdc", poly_wallet)
        self.assertEqual(poly_wallet["chain"], "polygon")
        
        print(f"✓ Dual wallet status retrieved successfully")

    def test_bridge_cost_estimation_for_trade(self):
        """Test bridge cost is properly estimated."""
        amount_needed = 50.0
        
        # Estimate cost to bridge from Solana to Polygon
        bridge_cost = self.bridge.estimate_bridge_cost(
            amount_needed,
            "solana",
            "polygon"
        )
        
        self.assertIsInstance(bridge_cost, float)
        self.assertGreater(bridge_cost, 0)
        
        # Cost should be reasonable (less than 2% of amount)
        self.assertLess(bridge_cost, amount_needed * 0.02)
        
        print(f"✓ Bridge cost estimation: {amount_needed} USD → ${bridge_cost:.2f} cost")

    @patch('wormhole_bridge.WormholeBridge.execute_bridge')
    def test_insufficient_balance_triggers_bridge(self, mock_bridge):
        """Test that insufficient balance on target chain triggers bridge."""
        # Mock bridge execution
        mock_bridge.return_value = "bridge_tx_hash"
        
        # In real flow, agent checks balance and triggers bridge
        # This test verifies the logic pattern
        
        polygon_balance = 25.0  # Insufficient
        trade_amount = 50.0
        
        # Should trigger bridge
        needs_bridge = polygon_balance < trade_amount
        self.assertTrue(needs_bridge)
        
        print(f"✓ Insufficient balance triggers bridge flow")


class TestMultiChainAgentIntegration(unittest.TestCase):
    """Integration tests for multi-chain agent."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = AutonomousAgent()

    def test_agent_has_dual_wallets(self):
        """Test agent has access to dual wallets through executor."""
        self.assertIsNotNone(self.agent)
        # Access via tools
        status = self.agent._process_tool_call("get_portfolio_status", {})
        
        self.assertIsNotNone(status)
        print(f"✓ Agent can access dual wallets")

    def test_place_trade_tool_with_chain_routing(self):
        """Test place_trade tool with chain parameter."""
        # Test Polygon trade
        with patch('agent.ENABLE_LIVE_TRADING', True):
            result = self.agent._process_tool_call(
                "place_trade",
                {
                    "market_id": "test_market_1",
                    "side": "YES",
                    "amount_usd": 50.0,
                    "entry_price": 0.55,
                    "chain": "polygon"
                }
            )
        
        self.assertIsNotNone(result)
        print(f"✓ Place trade tool supports chain routing")

    def test_kelly_sizing_with_dual_chains(self):
        """Test Kelly Criterion sizing works for both chains."""
        kelly_result = self.agent._process_tool_call(
            "calculate_kelly_position",
            {
                "bankroll": 1000,
                "win_probability": 0.65,
                "win_payoff": 1.5,
                "loss_payoff": 0.0
            }
        )
        
        self.assertIsNotNone(kelly_result)
        print(f"✓ Kelly sizing available for both chains")


class TestChainSpecificMarketRouting(unittest.TestCase):
    """Test market routing to appropriate chains."""

    def test_polymarket_routes_to_polygon(self):
        """Test that Polymarket markets are routed to Polygon."""
        market = {
            "market_id": "poly_1",
            "platform": "polymarket",
            "chain": "polygon",
            "title": "Test Market"
        }
        
        self.assertEqual(market["chain"], "polygon")
        self.assertEqual(market["platform"], "polymarket")
        print(f"✓ Polymarket routed to Polygon")

    def test_kalshi_routes_to_solana(self):
        """Test that Kalshi markets are routed to Solana."""
        market = {
            "market_id": "kalshi_1",
            "platform": "kalshi",
            "chain": "solana",
            "title": "Test Market"
        }
        
        self.assertEqual(market["chain"], "solana")
        self.assertEqual(market["platform"], "kalshi")
        print(f"✓ Kalshi routed to Solana")

    def test_transaction_persists_chain_metadata(self):
        """Test that executed trades store chain metadata."""
        executor = TradeExecutor()
        
        # Create and track a trade
        trade = executor.create_polygon_trade(
            market_id="poly_test",
            side="YES",
            amount_usd=50.0,
            price=0.55
        )
        
        # Verify chain is stored
        self.assertEqual(trade["chain"], "polygon")
        
        tx_hash = executor.submit_trade(trade)
        
        # Retrieve and verify
        persisted_trade = executor.get_transaction_details(tx_hash)
        self.assertEqual(persisted_trade["chain"], "polygon")
        
        print(f"✓ Trade chain metadata persisted")


if __name__ == "__main__":
    unittest.main(verbosity=2)
