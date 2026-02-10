"""
Test suite for Wormhole bridge integration.
Tests bridge initialization, cost estimation, and cross-chain flow.
"""
import unittest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wormhole_bridge import WormholeBridge
from blockchain_integration import SolanaWallet, PolygonWallet


class TestWormholeBridge(unittest.TestCase):
    """Test Wormhole bridge functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WormholeBridge()

    def test_bridge_init(self):
        """Test Wormhole bridge initialization."""
        self.assertIsNotNone(self.bridge)
        self.assertIsNotNone(self.bridge.solana_rpc)
        self.assertIsNotNone(self.bridge.polygon_rpc)
        self.assertEqual(self.bridge.bridge_timeout, 300)
        self.assertIsNotNone(self.bridge.bridge_fees)
        
        print(f"✓ Wormhole bridge initialized")

    def test_bridge_fee_structure(self):
        """Test bridge fee calculation structure."""
        fees = self.bridge.bridge_fees
        
        # Should have fee definitions
        self.assertIn("solana_to_polygon", fees)
        self.assertIn("polygon_to_solana", fees)
        
        # Fees should be reasonable (0.5-1%)
        for fee in fees.values():
            self.assertGreaterEqual(fee, 0.5)
            self.assertLessEqual(fee, 1.0)
        
        print(f"✓ Bridge fee structure valid")

    def test_estimate_bridge_cost(self):
        """Test bridge cost estimation."""
        cost = self.bridge.estimate_bridge_cost(100.0, "solana", "polygon")
        
        # Cost should be a float
        self.assertIsInstance(cost, float)
        self.assertGreaterEqual(cost, 0)
        
        # Should be roughly 0.75% fee + $0.50 gas
        expected_min = 100.0 * 0.0075 + 0.5
        expected_max = 100.0 * 0.0075 + 2.0
        self.assertGreaterEqual(cost, expected_min - 0.1)
        
        print(f"✓ Bridge cost estimation: 100 USD → ${cost:.2f}")

    def test_estimate_bridge_cost_same_chain(self):
        """Test cost estimation for same-chain transfer (should be 0)."""
        cost = self.bridge.estimate_bridge_cost(100.0, "solana", "solana")
        
        self.assertEqual(cost, 0.0)
        print(f"✓ Same-chain bridge cost: $0 (as expected)")

    def test_bridge_initialization_params(self):
        """Test bridge is initialized with correct parameters from config."""
        self.assertIsNotNone(self.bridge.solana_rpc)
        self.assertIsNotNone(self.bridge.polygon_rpc)
        self.assertEqual(self.bridge.bridge_timeout, 300)
        self.assertEqual(self.bridge.retry_attempts, 3)
        
        print(f"✓ Bridge initialization params correct")


class TestBridgeExecution(unittest.TestCase):
    """Test bridge execution flows."""

    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WormholeBridge()
        self.solana_wallet = SolanaWallet()
        self.polygon_wallet = PolygonWallet()

    @patch('wormhole_bridge.WormholeBridge._submit_bridge_transaction')
    def test_execute_bridge_same_chain(self, mock_submit):
        """Test that bridge rejects same-chain transfers."""
        result = self.bridge.execute_bridge(
            self.solana_wallet,
            self.polygon_wallet.get_address(),
            100.0,
            "solana",
            "solana"
        )
        
        # Should return None for same-chain
        self.assertIsNone(result)
        print(f"✓ Same-chain bridge rejected")

    def test_bridge_liquidity_check(self):
        """Test bridge liquidity validation."""
        # Within limits
        has_liquidity = self.bridge._check_bridge_liquidity("solana", "polygon", 1000.0)
        self.assertTrue(has_liquidity)
        
        # Exceeds devnet limit
        has_liquidity = self.bridge._check_bridge_liquidity("solana", "polygon", 50000.0)
        self.assertFalse(has_liquidity)
        
        print(f"✓ Bridge liquidity check working")

    def test_bridge_transaction_signing(self):
        """Test bridge transaction signing."""
        bridge_tx = {
            "from_address": self.solana_wallet.get_address(),
            "to_address": self.polygon_wallet.get_address(),
            "amount_usd": 100.0
        }
        
        tx_hash = self.bridge._sign_bridge_transaction(bridge_tx, self.solana_wallet, "solana")
        
        # Should return a hash string
        self.assertIsNotNone(tx_hash)
        self.assertIsInstance(tx_hash, str)
        self.assertTrue(tx_hash.startswith("solana_bridge"))
        
        print(f"✓ Bridge transaction signing: {tx_hash[:30]}...")

    def test_bridge_submission(self):
        """Test bridge transaction submission."""
        bridge_tx = {
            "from_address": self.solana_wallet.get_address(),
            "to_address": self.polygon_wallet.get_address(),
            "amount_usd": 100.0,
            "tx_hash": "test_tx_hash"
        }
        
        success = self.bridge._submit_bridge_transaction(bridge_tx, "solana")
        
        # Devnet submission should succeed
        self.assertTrue(success)
        print(f"✓ Bridge submission successful")


class TestBridgeConfirmation(unittest.TestCase):
    """Test bridge confirmation and timeout handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WormholeBridge()
        self.solana_wallet = SolanaWallet()

    def test_wait_for_confirmation_timeout(self):
        """Test confirmation timeout handling."""
        # Create a fake bridge transaction
        fake_tx_hash = "solana_bridge_test123"
        self.bridge.active_bridges[fake_tx_hash] = {
            "status": "submitted",
            "from_chain": "solana",
            "poll_count": 0
        }
        
        # Wait with short timeout
        confirmed = self.bridge.wait_for_confirmation(fake_tx_hash, "solana", timeout=2)
        
        # Should timeout
        self.assertFalse(confirmed)
        self.assertEqual(self.bridge.active_bridges[fake_tx_hash]["status"], "timeout")
        
        print(f"✓ Confirmation timeout handling works")

    def test_check_confirmation_on_chain(self):
        """Test on-chain confirmation checking."""
        # Create fake bridge transaction
        fake_tx_hash = "solana_bridge_confirm"
        self.bridge.active_bridges[fake_tx_hash] = {
            "status": "submitted",
            "poll_count": 0
        }
        
        # First poll - no confirmation
        confirmed = self.bridge._check_confirmation_on_chain(fake_tx_hash, "solana")
        self.assertFalse(confirmed)
        
        # Second poll - still no
        confirmed = self.bridge._check_confirmation_on_chain(fake_tx_hash, "solana")
        self.assertFalse(confirmed)
        
        # Third poll - should confirm
        confirmed = self.bridge._check_confirmation_on_chain(fake_tx_hash, "solana")
        self.assertTrue(confirmed)
        
        print(f"✓ On-chain confirmation polling works")

    def test_handle_timeout_with_retry(self):
        """Test timeout handler with retry logic."""
        fake_tx_hash = "solana_bridge_retry"
        self.bridge.active_bridges[fake_tx_hash] = {
            "status": "timeout",
            "from_chain": "solana",
            "to_chain": "polygon",
            "amount_usd": 100.0,
            "retry_count": 0
        }
        
        # Mock submission
        with patch.object(self.bridge, '_submit_bridge_transaction', return_value=True):
            result = self.bridge.handle_timeout(fake_tx_hash, lambda tx: None)
        
        # Should attempt retry
        self.assertEqual(self.bridge.active_bridges[fake_tx_hash]["retry_count"], 1)
        print(f"✓ Timeout retry logic works")

    def test_handle_timeout_max_retries(self):
        """Test timeout handler respects max retries."""
        fake_tx_hash = "solana_bridge_max_retry"
        self.bridge.active_bridges[fake_tx_hash] = {
            "status": "timeout",
            "from_chain": "solana",
            "to_chain": "polygon",
            "amount_usd": 100.0,
            "retry_count": 3  # Already at max
        }
        
        # Mock submission
        with patch.object(self.bridge, '_submit_bridge_transaction', return_value=False):
            result = self.bridge.handle_timeout(fake_tx_hash, lambda tx: None)
        
        # Should fall back since max retries reached
        self.assertEqual(self.bridge.active_bridges[fake_tx_hash]["status"], "fallback_executed")
        print(f"✓ Max retry limit respected")


class TestBridgeStateManagement(unittest.TestCase):
    """Test bridge state and tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WormholeBridge()

    def test_active_bridges_tracking(self):
        """Test active bridge transactions are tracked."""
        # Add a fake active bridge
        test_tx = {
            "tx_hash": "test_hash_123",
            "status": "pending",
            "from_chain": "solana",
            "to_chain": "polygon"
        }
        self.bridge.active_bridges["test_hash_123"] = test_tx
        
        # Should be retrievable
        status = self.bridge.get_bridge_status("test_hash_123")
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "pending")
        
        print(f"✓ Active bridge tracking works")

    def test_get_all_active_bridges(self):
        """Test retrieving all active bridges."""
        # Add multiple bridges
        for i in range(3):
            tx_hash = f"bridge_{i}"
            self.bridge.active_bridges[tx_hash] = {
                "status": "pending",
                "amount_usd": 100.0 * (i + 1)
            }
        
        all_bridges = self.bridge.get_all_active_bridges()
        self.assertEqual(len(all_bridges), 3)
        
        print(f"✓ Retrieved {len(all_bridges)} active bridges")


if __name__ == "__main__":
    unittest.main(verbosity=2)
