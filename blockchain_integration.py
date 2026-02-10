"""
Blockchain Integration - Multi-chain wallet management (Solana + Polygon).
Handles non-custodial wallets, balance tracking, and transaction execution.
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional
import secrets
import requests
import base64
from datetime import datetime

from solders.keypair import Keypair
from web3 import Web3

from config import (
    SOLANA_RPC_URL,
    SOLANA_COMMITMENT,
    SOLANA_NETWORK,
    POLYGON_RPC_URL,
    POLYGON_CHAIN_ID,
    POLYGON_USDC_CONTRACT,
)


class SolanaWallet:
    """Non-custodial Solana wallet manager for devnet trading."""

    def __init__(self, keypair_path: str = None):
        self.rpc_url = SOLANA_RPC_URL
        self.commitment = SOLANA_COMMITMENT
        self.chain = "solana"
        self.keypair_path = Path(keypair_path) if keypair_path else Path(__file__).parent / "data" / "solana_keypair.json"
        self.keypair = None
        self.public_key = None
        
        self._load_or_create_keypair()

    def _load_or_create_keypair(self):
        """Load existing keypair or create new one."""
        self.keypair_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.keypair_path.exists():
            with open(self.keypair_path, 'r') as f:
                data = json.load(f)
                seed_bytes = bytes(data['seed'])
                self.keypair = Keypair.from_seed(seed_bytes)
        else:
            # Create new keypair with 32-byte seed
            seed_bytes = secrets.token_bytes(32)
            self.keypair = Keypair.from_seed(seed_bytes)
            seed_list = list(seed_bytes)
            with open(self.keypair_path, 'w') as f:
                json.dump({'seed': seed_list}, f)
            print(f"[SOLANA] Created new keypair: {self.keypair.pubkey()}")
        
        self.public_key = str(self.keypair.pubkey())

    def get_address(self) -> str:
        """Get wallet public address."""
        return str(self.public_key)

    def get_balance(self) -> float:
        """Get SOL balance in devnet."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [str(self.public_key)]
            }
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    balance_lamports = result['result']['value']
                    return balance_lamports / 1e9
        except Exception as e:
            print(f"[SOLANA ERROR] Failed to get balance: {e}")
        
        return 0.0

    def request_airdrop(self, amount_sol: float = 2.0) -> Optional[str]:
        """Request airdrop of test SOL on devnet."""
        if SOLANA_NETWORK != "devnet":
            print("[SOLANA] Airdrops only available on devnet")
            return None
        
        try:
            amount_lamports = int(amount_sol * 1e9)
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "requestAirdrop",
                "params": [str(self.public_key), amount_lamports]
            }
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    tx_hash = result['result']
                    print(f"[SOLANA] Airdrop requested: {tx_hash}")
                    return tx_hash
        except Exception as e:
            print(f"[SOLANA ERROR] Airdrop failed: {e}")
        
        return None

    def get_keypair_json(self) -> Dict:
        """Export keypair as JSON for backup."""
        return {
            "public_key": str(self.public_key),
            "chain": "solana",
            "network": SOLANA_NETWORK,
            "created_at": datetime.now().isoformat()
        }


class PolygonWallet:
    """Non-custodial Polygon wallet manager for Mumbai testnet."""

    def __init__(self, keypair_path: str = None):
        self.rpc_url = POLYGON_RPC_URL
        self.chain_id = POLYGON_CHAIN_ID
        self.chain = "polygon"
        self.usdc_contract = POLYGON_USDC_CONTRACT
        self.keypair_path = Path(keypair_path) if keypair_path else Path(__file__).parent / "data" / "polygon_keypair.json"
        self.private_key = None
        self.public_key = None
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        self._load_or_create_keypair()

    def _load_or_create_keypair(self):
        """Load existing keypair or create new one."""
        self.keypair_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.keypair_path.exists():
            with open(self.keypair_path, 'r') as f:
                data = json.load(f)
                self.private_key = data['private_key']
        else:
            # Create new keypair
            account = self.web3.eth.account.create()
            self.private_key = account.key.hex()
            with open(self.keypair_path, 'w') as f:
                json.dump({'private_key': self.private_key}, f)
            print(f"[POLYGON] Created new wallet: {account.address}")
        
        # Derive address from private key
        account = self.web3.eth.account.from_key(self.private_key)
        self.public_key = account.address
        
        # Set file permissions (Unix-like systems)
        try:
            os.chmod(self.keypair_path, 0o600)
        except:
            pass

    def get_address(self) -> str:
        """Get wallet address."""
        return self.public_key

    def get_balance(self) -> float:
        """Get USDC balance on Polygon Mumbai (in USDC units)."""
        try:
            # Simple balance check - in production would call USDC contract
            # For now return mock balance
            return 1000.0  # Mock 1000 USDC
        except Exception as e:
            print(f"[POLYGON ERROR] Failed to get balance: {e}")
        
        return 0.0

    def request_faucet(self, amount_usdc: float = 100.0) -> Optional[str]:
        """Request faucet funds on Polygon Mumbai."""
        print(f"[POLYGON] Faucet request for {amount_usdc} USDC")
        print(f"[POLYGON] Visit: https://faucet.polygon.technology/")
        return "faucet_requested"

    def get_keypair_json(self) -> Dict:
        """Export keypair as JSON for backup."""
        return {
            "public_key": str(self.public_key),
            "chain": "polygon",
            "chain_id": self.chain_id,
            "created_at": datetime.now().isoformat()
        }


class TradeExecutor:
    """Execute trades on Solana and Polygon devnets."""

    def __init__(self):
        self.solana_wallet = SolanaWallet()
        self.polygon_wallet = PolygonWallet()
        self.transactions = {}

    def create_solana_trade(
        self,
        market_id: str,
        side: str,
        amount_usd: float,
        price: float
    ) -> Optional[Dict]:
        """Create a trade transaction for Solana (Kalshi via DFlow)."""
        try:
            trade = {
                "market_id": market_id,
                "platform": "kalshi",
                "chain": "solana",
                "side": side,
                "amount_usd": amount_usd,
                "entry_price": price,
                "expected_contracts": amount_usd / price if price > 0 else 0,
                "wallet_address": self.solana_wallet.get_address(),
                "bridge": "dflow",
                "timestamp": datetime.now().isoformat(),
                "status": "draft"
            }
            
            trade_id = f"trade_{market_id}_{len(self.transactions)}"
            self.transactions[trade_id] = trade
            
            print(f"[TX] Created Solana trade (Kalshi): {trade_id}")
            return trade
            
        except Exception as e:
            print(f"[TX ERROR] Failed to create Solana trade: {e}")
            return None

    def create_polygon_trade(
        self,
        market_id: str,
        side: str,
        amount_usd: float,
        price: float
    ) -> Optional[Dict]:
        """Create a trade transaction for Polygon (Polymarket)."""
        try:
            trade = {
                "market_id": market_id,
                "platform": "polymarket",
                "chain": "polygon",
                "side": side,
                "amount_usd": amount_usd,
                "entry_price": price,
                "expected_shares": amount_usd / price if price > 0 else 0,
                "wallet_address": self.polygon_wallet.get_address(),
                "usdc_contract": self.polygon_wallet.usdc_contract,
                "timestamp": datetime.now().isoformat(),
                "status": "draft"
            }
            
            trade_id = f"trade_{market_id}_{len(self.transactions)}"
            self.transactions[trade_id] = trade
            
            print(f"[TX] Created Polygon trade (Polymarket): {trade_id}")
            return trade
            
        except Exception as e:
            print(f"[TX ERROR] Failed to create Polygon trade: {e}")
            return None

    def create_polymarket_trade(
        self,
        market_id: str,
        side: str,
        amount_usd: float,
        price: float
    ) -> Optional[Dict]:
        """Alias for create_polygon_trade for backward compatibility."""
        return self.create_polygon_trade(market_id, side, amount_usd, price)

    def create_kalshi_trade(
        self,
        market_id: str,
        side: str,
        amount_usd: float,
        price: float
    ) -> Optional[Dict]:
        """Alias for create_solana_trade for backward compatibility."""
        return self.create_solana_trade(market_id, side, amount_usd, price)

    def submit_trade(self, trade: Dict) -> Optional[str]:
        """Submit a trade transaction."""
        try:
            chain = trade.get('chain', 'solana')
            
            if chain == 'polygon':
                # Check Polygon balance
                balance = self.polygon_wallet.get_balance()
                if balance < trade['amount_usd']:
                    print(f"[TX] Insufficient USDC balance on Polygon: {balance}")
                    return None
            else:
                # Check Solana balance
                balance = self.solana_wallet.get_balance()
                if balance < 0.1:
                    print("[TX] Insufficient SOL for gas. Requesting airdrop...")
                    self.solana_wallet.request_airdrop(2.0)
            
            # Generate mock transaction hash
            tx_hash = f"{chain}_tx_{hash(str(trade))}"[:50]
            trade['status'] = 'submitted'
            trade['tx_hash'] = tx_hash
            trade['submitted_at'] = datetime.now().isoformat()
            
            print(f"[TX] Submitted {chain} trade: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            print(f"[TX ERROR] Failed to submit trade: {e}")
            trade['status'] = 'failed'
            trade['error'] = str(e)
            return None

    def get_transaction_details(self, tx_hash: str) -> Optional[Dict]:
        """Get details of a submitted transaction."""
        for trade_id, trade in self.transactions.items():
            if trade.get('tx_hash') == tx_hash:
                return trade
        return None

    def get_dual_wallet_status(self) -> Dict:
        """Get status of both wallets."""
        return {
            "solana": {
                "address": self.solana_wallet.get_address(),
                "balance_sol": self.solana_wallet.get_balance(),
                "chain": "solana",
                "network": SOLANA_NETWORK
            },
            "polygon": {
                "address": self.polygon_wallet.get_address(),
                "balance_usdc": self.polygon_wallet.get_balance(),
                "chain": "polygon",
                "chain_id": POLYGON_CHAIN_ID,
                "network": "mumbai"
            }
        }


# Global instances
wallet = SolanaWallet()  # For backward compatibility
executor = TradeExecutor()
