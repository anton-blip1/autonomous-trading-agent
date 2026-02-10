"""
Test suite for Polygon wallet integration.
Tests wallet generation, balance checking, and address format.
"""
import unittest
import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blockchain_integration import PolygonWallet
from config import POLYGON_CHAIN_ID


class TestPolygonWallet(unittest.TestCase):
    """Test Polygon wallet functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test keypairs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.keypair_path = Path(self.temp_dir.name) / "test_polygon_keypair.json"

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_polygon_wallet_generation(self):
        """Test Polygon wallet generation."""
        wallet = PolygonWallet(keypair_path=str(self.keypair_path))
        
        # Verify wallet is created
        self.assertIsNotNone(wallet)
        self.assertIsNotNone(wallet.private_key)
        self.assertIsNotNone(wallet.public_key)
        self.assertEqual(wallet.chain, "polygon")
        self.assertEqual(wallet.chain_id, POLYGON_CHAIN_ID)
        
        print(f"✓ Polygon wallet created: {wallet.public_key[:10]}...")

    def test_polygon_address_format(self):
        """Test that Polygon address is in correct format."""
        wallet = PolygonWallet(keypair_path=str(self.keypair_path))
        address = wallet.get_address()
        
        # Polygon addresses are 40 hex characters (20 bytes) prefixed with 0x
        self.assertTrue(address.startswith("0x"))
        self.assertEqual(len(address), 42)  # 0x + 40 hex chars
        
        # Should be valid hex
        try:
            int(address, 16)
            valid_hex = True
        except ValueError:
            valid_hex = False
        
        self.assertTrue(valid_hex)
        print(f"✓ Polygon address format valid: {address}")

    def test_polygon_keypair_persistence(self):
        """Test that keypair is persisted and reloaded."""
        # Create wallet
        wallet1 = PolygonWallet(keypair_path=str(self.keypair_path))
        address1 = wallet1.get_address()
        
        # Load same wallet
        wallet2 = PolygonWallet(keypair_path=str(self.keypair_path))
        address2 = wallet2.get_address()
        
        # Should be the same
        self.assertEqual(address1, address2)
        print(f"✓ Keypair persistence works: {address1} == {address2}")

    def test_polygon_balance_check(self):
        """Test Polygon balance checking."""
        wallet = PolygonWallet(keypair_path=str(self.keypair_path))
        balance = wallet.get_balance()
        
        # Should return a number
        self.assertIsInstance(balance, float)
        self.assertGreaterEqual(balance, 0)
        
        # For mock, should return 1000 USDC
        self.assertEqual(balance, 1000.0)
        print(f"✓ Polygon balance check: {balance} USDC")

    def test_polygon_faucet_request(self):
        """Test faucet request."""
        wallet = PolygonWallet(keypair_path=str(self.keypair_path))
        result = wallet.request_faucet(100.0)
        
        # Should return a status string
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        print(f"✓ Polygon faucet request: {result}")

    def test_polygon_keypair_json_export(self):
        """Test keypair JSON export for backup."""
        wallet = PolygonWallet(keypair_path=str(self.keypair_path))
        keypair_json = wallet.get_keypair_json()
        
        # Verify export format
        self.assertIn("public_key", keypair_json)
        self.assertIn("chain", keypair_json)
        self.assertIn("chain_id", keypair_json)
        self.assertIn("created_at", keypair_json)
        
        self.assertEqual(keypair_json["chain"], "polygon")
        self.assertEqual(keypair_json["chain_id"], POLYGON_CHAIN_ID)
        self.assertEqual(keypair_json["public_key"], wallet.get_address())
        
        print(f"✓ Keypair JSON export valid")

    def test_multiple_wallets(self):
        """Test creating multiple independent wallets."""
        temp_dir1 = tempfile.TemporaryDirectory()
        temp_dir2 = tempfile.TemporaryDirectory()
        
        try:
            wallet1 = PolygonWallet(keypair_path=str(Path(temp_dir1.name) / "wallet1.json"))
            wallet2 = PolygonWallet(keypair_path=str(Path(temp_dir2.name) / "wallet2.json"))
            
            # Should have different addresses
            self.assertNotEqual(wallet1.get_address(), wallet2.get_address())
            print(f"✓ Multiple wallets created independently")
        finally:
            temp_dir1.cleanup()
            temp_dir2.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
