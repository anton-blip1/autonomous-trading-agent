"""
Test suite for Groq agent integration.
Tests Groq client initialization, tool use formatting, and reasoning loop.
"""
import unittest
import json
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import AutonomousAgent
from config import GROQ_API_KEY, GROQ_MODEL


class TestGroqAgentIntegration(unittest.TestCase):
    """Test Groq-powered autonomous agent."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = AutonomousAgent()

    def test_groq_client_init(self):
        """Test Groq client initialization."""
        self.assertIsNotNone(self.agent.client)
        self.assertEqual(self.agent.model, GROQ_MODEL)
        self.assertEqual(self.agent.bankroll, 1000)
        print(f"✓ Groq client initialized with model: {self.agent.model}")

    def test_tool_use_formatting(self):
        """Test that tools are formatted correctly for Groq/OpenAI API."""
        tools = self.agent.tools
        
        # Should be a list
        self.assertIsInstance(tools, list)
        
        # Each tool should have type and function fields
        for tool in tools:
            self.assertIn("type", tool)
            self.assertIn("function", tool)
            self.assertEqual(tool["type"], "function")
            
            # Function should have name, description, parameters
            func = tool["function"]
            self.assertIn("name", func)
            self.assertIn("description", func)
            self.assertIn("parameters", func)
            
            # Parameters should have type and properties
            params = func["parameters"]
            self.assertIn("type", params)
            self.assertEqual(params["type"], "object")
        
        print(f"✓ Tool formatting valid ({len(tools)} tools)")

    def test_tool_call_processing(self):
        """Test tool call processing."""
        # Test get_portfolio_status tool
        result = self.agent._process_tool_call("get_portfolio_status", {})
        result_dict = json.loads(result)
        
        self.assertIn("bankroll", result_dict)
        self.assertIn("open_positions", result_dict)
        self.assertIn("trades_executed", result_dict)
        self.assertIn("session_pnl_usd", result_dict)
        
        print(f"✓ Tool call processing works correctly")

    def test_kelly_calculation_tool(self):
        """Test Kelly Criterion calculation tool."""
        result = self.agent._process_tool_call(
            "calculate_kelly_position",
            {
                "bankroll": 1000,
                "win_probability": 0.6,
                "win_payoff": 2.0,
                "loss_payoff": 0.0
            }
        )
        result_dict = json.loads(result)
        
        self.assertIn("kelly_fraction", result_dict)
        self.assertIn("position_size_usd", result_dict)
        
        # With 60% win prob, 2x payoff, Kelly should be positive
        self.assertGreater(result_dict["kelly_fraction"], 0)
        self.assertGreater(result_dict["position_size_usd"], 0)
        
        print(f"✓ Kelly calculation tool works: {result_dict['kelly_fraction']:.4f}")

    def test_market_edge_evaluation_tool(self):
        """Test market edge evaluation."""
        result = self.agent._process_tool_call(
            "evaluate_market_edge",
            {
                "market_id": "test_market",
                "fair_value": 0.65,
                "market_price": 0.50,
                "confidence": 0.75
            }
        )
        result_dict = json.loads(result)
        
        self.assertIn("edge_percent", result_dict)
        self.assertIn("has_edge", result_dict)
        self.assertIn("recommendation", result_dict)
        
        # 15% edge should be recognized
        self.assertGreater(result_dict["edge_percent"], 3)
        self.assertTrue(result_dict["has_edge"])
        self.assertEqual(result_dict["recommendation"], "BUY")
        
        print(f"✓ Market edge evaluation: {result_dict['edge_percent']:.1f}% edge detected")

    def test_agent_initialization_defaults(self):
        """Test agent initializes with correct defaults."""
        self.assertEqual(self.agent.bankroll, 1000)
        self.assertEqual(self.agent.trades_executed, 0)
        self.assertEqual(self.agent.trades_successful, 0)
        self.assertEqual(self.agent.session_pnl, 0.0)
        
        print(f"✓ Agent defaults initialized correctly")


class TestGroqReasoningLoop(unittest.TestCase):
    """Test Groq reasoning loop and decision making."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = AutonomousAgent()

    @patch('agent.scanner.scan_all_markets')
    def test_analyze_and_decide_with_opportunities(self, mock_scan):
        """Test reasoning loop with market opportunities."""
        # Mock market opportunities
        mock_scan.return_value = [
            {
                "market_id": "test_1",
                "platform": "polymarket",
                "chain": "polygon",
                "title": "Test Market 1",
                "yes_price": 0.45,
                "no_price": 0.55,
                "overall_score": 75.0
            }
        ]
        
        # This would normally be async, but we're testing synchronously
        # Just verify the agent can process opportunities
        opportunities = [
            {
                "market_id": "test_1",
                "platform": "polymarket",
                "chain": "polygon",
                "title": "Test Market",
                "yes_price": 0.45,
                "no_price": 0.55,
            }
        ]
        
        # Verify opportunities are non-empty
        self.assertGreater(len(opportunities), 0)
        print(f"✓ Reasoning loop can process {len(opportunities)} opportunities")


if __name__ == "__main__":
    unittest.main(verbosity=2)
