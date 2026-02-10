"""
DFlow Kalshi Bridge - Non-custodial Solana → Kalshi trading
Bridges Solana funds to Kalshi via DFlow
Allows trading Kalshi markets with Solana wallets
"""

import asyncio
import aiohttp
from typing import Dict, Optional, Tuple
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer
from solders.rpc.responses import GetLatestBlockhashResp

from config import Config


class DFlowKalshiBridge:
    """
    DFlow bridge for Solana ↔ Kalshi trading.
    
    Flow:
    1. User wants to trade Kalshi market
    2. Bot gets user's Solana keypair
    3. Sign transfer to DFlow (USDC or SOL)
    4. DFlow bridges to Kalshi
    5. User can trade on Kalshi
    6. Winnings bridge back to Solana
    """
    
    def __init__(self):
        self.solana_rpc = Config.SOLANA_RPC_URL
        self.dflow_api = "https://api.dflow.trade"  # DFlow API endpoint
        self.dflow_contract = "DFlow11111111111111111111111111111111111111"  # Placeholder
    
    async def get_solana_balance(self, public_key: str) -> float:
        """Get Solana balance in SOL."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [public_key]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.solana_rpc, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if 'result' in data:
                        balance_lamports = data['result']['value']
                        return balance_lamports / 1e9  # Convert to SOL
        except Exception as e:
            print(f"[DFLOW] Error getting balance: {e}")
        
        return 0.0
    
    async def get_latest_blockhash(self) -> Tuple[str, int]:
        """Get latest blockhash for transaction signing."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "processed"}]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.solana_rpc, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if 'result' in data:
                        blockhash = data['result']['value']['blockhash']
                        last_valid_block_height = data['result']['value']['lastValidBlockHeight']
                        return blockhash, last_valid_block_height
        except Exception as e:
            print(f"[DFLOW] Error getting blockhash: {e}")
        
        return None, None
    
    async def create_bridge_transaction(
        self,
        keypair: Keypair,
        amount_sol: float,
        destination: str = "dflow"
    ) -> Optional[str]:
        """
        Create transaction to bridge SOL to DFlow.
        
        Args:
            keypair: User's Solana keypair
            amount_sol: Amount in SOL to bridge
            destination: "dflow" for DFlow bridge
        
        Returns:
            Signed transaction (serialized)
        """
        
        try:
            # Get latest blockhash
            blockhash, _ = await self.get_latest_blockhash()
            if not blockhash:
                print("[DFLOW] Failed to get blockhash")
                return None
            
            # For real implementation, would use:
            # 1. DFlow program ID
            # 2. Create instruction to call DFlow bridge
            # 3. Set amount + destination
            # 4. Sign with user's keypair
            
            print(f"[DFLOW] Would create bridge transaction:")
            print(f"  From: {keypair.pubkey()}")
            print(f"  Amount: {amount_sol} SOL")
            print(f"  To: {destination}")
            print(f"  Blockhash: {blockhash[:10]}...")
            
            # Mock response (real would serialize transaction)
            return f"tx_bridge_{int(amount_sol * 1e9)}"
        
        except Exception as e:
            print(f"[DFLOW] Error creating transaction: {e}")
            return None
    
    async def broadcast_transaction(self, tx_serialized: str) -> Optional[str]:
        """
        Broadcast transaction to Solana blockchain.
        
        Args:
            tx_serialized: Signed transaction
        
        Returns:
            Transaction hash
        """
        
        try:
            # In production: would use:
            # connection.send_transaction(tx)
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    tx_serialized,
                    {"encoding": "base64", "preflightCommitment": "processed"}
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.solana_rpc, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if 'result' in data:
                        tx_hash = data['result']
                        print(f"[DFLOW] Transaction broadcast: {tx_hash}")
                        return tx_hash
                    elif 'error' in data:
                        print(f"[DFLOW] RPC error: {data['error']}")
        
        except Exception as e:
            print(f"[DFLOW] Error broadcasting: {e}")
        
        return None
    
    async def bridge_to_kalshi(
        self,
        keypair: Keypair,
        amount_sol: float
    ) -> Dict:
        """
        Bridge SOL to Kalshi via DFlow.
        
        Full flow:
        1. Check balance
        2. Create bridge transaction
        3. Sign with user keypair
        4. Broadcast to Solana
        5. Wait for confirmation
        6. Return bridge address
        """
        
        print(f"[DFLOW] Starting bridge: {amount_sol} SOL → Kalshi")
        
        # 1. Check balance
        balance = await self.get_solana_balance(str(keypair.pubkey()))
        if balance < amount_sol:
            print(f"[DFLOW] Insufficient balance: {balance} SOL < {amount_sol} SOL")
            return {'error': f'Insufficient balance: {balance} SOL', 'success': False}
        
        print(f"[DFLOW] Balance check: {balance} SOL ✓")
        
        # 2. Create transaction
        tx = await self.create_bridge_transaction(keypair, amount_sol)
        if not tx:
            return {'error': 'Failed to create transaction', 'success': False}
        
        print(f"[DFLOW] Transaction created ✓")
        
        # 3. Broadcast (already signed with user's keypair)
        tx_hash = await self.broadcast_transaction(tx)
        if not tx_hash:
            return {'error': 'Failed to broadcast transaction', 'success': False}
        
        print(f"[DFLOW] Transaction broadcast: {tx_hash} ✓")
        
        # 4. Return bridge info
        return {
            'success': True,
            'tx_hash': tx_hash,
            'amount_sol': amount_sol,
            'kalshi_address': f"kalshi_{keypair.pubkey()}_bridge",
            'status': 'bridged'
        }
    
    async def get_kalshi_markets_via_dflow(self) -> list:
        """Fetch Kalshi markets through DFlow API."""
        try:
            url = f"{self.dflow_api}/markets?exchange=kalshi"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        markets = data.get('markets', [])
                        print(f"[DFLOW] Fetched {len(markets)} Kalshi markets via DFlow")
                        return markets
                    else:
                        print(f"[DFLOW] API error: {resp.status}")
        
        except Exception as e:
            print(f"[DFLOW] Error fetching markets: {e}")
        
        return []
    
    async def place_kalshi_trade(
        self,
        keypair: Keypair,
        market_id: str,
        amount_usdc: float,
        position: str  # "YES" or "NO"
    ) -> Dict:
        """
        Place trade on Kalshi via DFlow.
        
        Args:
            keypair: User's Solana keypair
            market_id: Kalshi market ID
            amount_usdc: Amount in USDC
            position: "YES" or "NO"
        
        Returns:
            Trade result
        """
        
        print(f"[DFLOW] Placing Kalshi trade: {market_id}, {amount_usdc} USDC, {position}")
        
        # 1. Check user has bridge balance (in Kalshi account via DFlow)
        # 2. Create trade instruction
        # 3. Sign with user keypair
        # 4. Broadcast via DFlow
        # 5. Return trade confirmation
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "trade",
                "params": {
                    "market_id": market_id,
                    "amount": amount_usdc,
                    "position": position,
                    "signer": str(keypair.pubkey())
                }
            }
            
            async with aiohttp.ClientSession() as session:
                # In production, would sign this with keypair first
                async with session.post(f"{self.dflow_api}/trade", json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"[DFLOW] Trade executed: {result.get('trade_id')}")
                        return {
                            'success': True,
                            'trade_id': result.get('trade_id'),
                            'market_id': market_id,
                            'amount': amount_usdc,
                            'position': position,
                            'tx_hash': result.get('tx_hash')
                        }
        
        except Exception as e:
            print(f"[DFLOW] Error placing trade: {e}")
        
        return {'success': False, 'error': 'Trade execution failed'}


# Global instance
dflow_bridge = DFlowKalshiBridge()
