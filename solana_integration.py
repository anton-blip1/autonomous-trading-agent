"""
Solana Integration - Non-custodial wallet management and devnet transactions.
Handles keypair generation, transaction signing, and submission.
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from solders.keypair import Keypair
from solders.pubkey import PublicKey
from solders.rpc.requests import GetBalance
from solders.transaction import Transaction
from solders.instruction import Instruction
from solders.system_program import CreateAccountParams, create_account
import requests
import base64

from config import SOLANA_RPC_URL, SOLANA_COMMITMENT, SOLANA_NETWORK


class SolanaWallet:
    """Non-custodial Solana wallet manager for devnet trading."""

    def __init__(self, keypair_path: str = None):
        self.rpc_url = SOLANA_RPC_URL
        self.commitment = SOLANA_COMMITMENT
        self.keypair_path = keypair_path or Path(__file__).parent / "data" / "solana_keypair.json"
        self.keypair = None
        self.public_key = None
        
        self._load_or_create_keypair()

    def _load_or_create_keypair(self):
        """Load existing keypair or create new one."""
        self.keypair_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.keypair_path.exists():
            with open(self.keypair_path, 'r') as f:
                data = json.load(f)
                self.keypair = Keypair.from_secret_key(bytes(data['secret']))
        else:
            # Create new keypair
            self.keypair = Keypair.generate()
            secret_list = list(self.keypair.secret)
            with open(self.keypair_path, 'w') as f:
                json.dump({'secret': secret_list}, f)
            print(f"[WALLET] Created new keypair: {self.keypair.public_key}")
        
        self.public_key = self.keypair.public_key

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
                    # Balance is in lamports, convert to SOL
                    balance_lamports = result['result']['value']
                    return balance_lamports / 1e9  # 1 SOL = 1e9 lamports
        except Exception as e:
            print(f"[WALLET ERROR] Failed to get balance: {e}")
        
        return 0.0

    def request_airdrop(self, amount_sol: float = 2.0) -> Optional[str]:
        """Request airdrop of test SOL on devnet."""
        if SOLANA_NETWORK != "devnet":
            print("[WALLET] Airdrops only available on devnet")
            return None
        
        try:
            # Convert SOL to lamports
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
                    print(f"[WALLET] Airdrop requested: {tx_hash}")
                    return tx_hash
        except Exception as e:
            print(f"[WALLET ERROR] Airdrop failed: {e}")
        
        return None

    def sign_transaction(self, transaction: Transaction) -> Transaction:
        """Sign a transaction with the wallet keypair."""
        transaction.sign([self.keypair], None)
        return transaction

    def submit_transaction(self, transaction_bytes: bytes) -> Optional[str]:
        """Submit signed transaction to Solana RPC."""
        try:
            encoded_tx = base64.b64encode(transaction_bytes).decode('utf-8')
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [encoded_tx, {"encoding": "base64", "preflightCommitment": self.commitment}]
            }
            
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    return result['result']
                elif 'error' in result:
                    print(f"[TX ERROR] {result['error']}")
        except Exception as e:
            print(f"[TX ERROR] Submission failed: {e}")
        
        return None

    def get_transaction_status(self, tx_hash: str) -> Optional[str]:
        """Check transaction status on devnet."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransactionStatus",
                "params": [tx_hash]
            }
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    status = result['result']
                    return status.get('value', {}).get('status')
        except Exception as e:
            print(f"[TX ERROR] Status check failed: {e}")
        
        return None

    def get_keypair_json(self) -> Dict:
        """Export keypair as JSON for backup."""
        return {
            "public_key": str(self.public_key),
            "network": SOLANA_NETWORK,
            "created_at": "2026-02-10"
        }


class TradeExecutor:
    """Execute trades on Solana devnet using the non-custodial wallet."""

    def __init__(self):
        self.wallet = SolanaWallet()
        self.transactions = {}

    def create_polymarket_trade(
        self,
        market_id: str,
        side: str,  # 'YES' or 'NO'
        amount_usd: float,
        price: float
    ) -> Optional[Dict]:
        """Create a trade transaction for Polymarket."""
        try:
            # In real implementation, this would create a USDC transfer to Polymarket contract
            # For devnet simulation, we'll create a mock transaction log
            
            trade = {
                "market_id": market_id,
                "platform": "polymarket",
                "side": side,
                "amount_usd": amount_usd,
                "entry_price": price,
                "expected_shares": amount_usd / price,
                "wallet_address": self.wallet.get_address(),
                "timestamp": "2026-02-10T07:16:00Z",
                "status": "draft"
            }
            
            trade_id = f"trade_{market_id}_{len(self.transactions)}"
            self.transactions[trade_id] = trade
            
            print(f"[TX] Created Polymarket trade: {trade_id}")
            return trade
            
        except Exception as e:
            print(f"[TX ERROR] Failed to create Polymarket trade: {e}")
            return None

    def create_kalshi_trade(
        self,
        market_id: str,
        side: str,  # 'YES' or 'NO'
        amount_usd: float,
        price: float
    ) -> Optional[Dict]:
        """Create a trade transaction for Kalshi via DFlow bridge."""
        try:
            trade = {
                "market_id": market_id,
                "platform": "kalshi",
                "side": side,
                "amount_usd": amount_usd,
                "entry_price": price,
                "expected_contracts": amount_usd / price,
                "wallet_address": self.wallet.get_address(),
                "bridge": "dflow",
                "timestamp": "2026-02-10T07:16:00Z",
                "status": "draft"
            }
            
            trade_id = f"trade_{market_id}_{len(self.transactions)}"
            self.transactions[trade_id] = trade
            
            print(f"[TX] Created Kalshi trade: {trade_id}")
            return trade
            
        except Exception as e:
            print(f"[TX ERROR] Failed to create Kalshi trade: {e}")
            return None

    def submit_trade(self, trade: Dict) -> Optional[str]:
        """Submit a trade transaction to Solana."""
        try:
            # Check wallet balance
            balance = self.wallet.get_balance()
            if balance < 0.1:  # Need SOL for gas
                print("[TX] Insufficient SOL for gas fees. Requesting airdrop...")
                self.wallet.request_airdrop(2.0)
            
            # In real implementation, would sign and submit actual transaction
            # For MVP, we'll generate a mock transaction hash
            
            tx_hash = f"devnet_tx_{hash(str(trade))}"[:44]
            trade['status'] = 'submitted'
            trade['tx_hash'] = tx_hash
            
            print(f"[TX] Submitted trade: {tx_hash}")
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


# Global instances
wallet = SolanaWallet()
executor = TradeExecutor()
