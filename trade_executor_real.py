"""
Trade Executor - Real Transaction Version
Executes real trades on Kalshi (via DFlow) and Polymarket (via Polygon)
"""

import uuid
from typing import Dict, Optional
from datetime import datetime

from wallet_manager import wallet_manager
from database import db
from dflow_kalshi_bridge import dflow_bridge
from polymarket_direct import polymarket


class TradeExecutorReal:
    """Execute real trades on actual markets."""
    
    def __init__(self):
        self.auto_exec_threshold = 5.0  # Auto-execute < $5
        self.approval_threshold = 100.0  # Require approval < $100
    
    async def execute_kalshi_trade(
        self,
        user_id: int,
        market_id: str,
        amount_usdc: float,
        position: str  # "YES" or "NO"
    ) -> Dict:
        """
        Execute real trade on Kalshi via DFlow.
        
        Flow:
        1. Get user's Solana keypair
        2. Bridge USDC to Kalshi via DFlow
        3. Place market order
        4. Log trade
        """
        
        print(f"[EXECUTOR] Kalshi trade: user={user_id}, market={market_id}, amount=${amount_usdc}, pos={position}")
        
        try:
            # 1. Get user's Solana keypair
            user = await db.get_user(user_id)
            if not user:
                return {'error': 'User not found', 'status': 'failed'}
            
            keypair = await wallet_manager.get_user_keypair(user_id)
            
            # 2. Convert USD amount to SOL (rough: $1 ≈ 0.01 SOL on devnet)
            amount_sol = amount_usdc * 0.01
            
            # 3. Bridge to Kalshi via DFlow
            print(f"[EXECUTOR] Bridging {amount_sol} SOL to Kalshi...")
            bridge_result = await dflow_bridge.bridge_to_kalshi(keypair, amount_sol)
            
            if not bridge_result.get('success'):
                print(f"[EXECUTOR] Bridge failed: {bridge_result.get('error')}")
                return {'error': bridge_result.get('error'), 'status': 'failed'}
            
            bridge_tx = bridge_result.get('tx_hash')
            print(f"[EXECUTOR] Bridge successful: {bridge_tx}")
            
            # 4. Place Kalshi trade
            print(f"[EXECUTOR] Placing Kalshi order...")
            trade_result = await dflow_bridge.place_kalshi_trade(
                keypair,
                market_id,
                amount_usdc,
                position
            )
            
            if not trade_result.get('success'):
                print(f"[EXECUTOR] Trade failed: {trade_result.get('error')}")
                return {'error': trade_result.get('error'), 'status': 'failed'}
            
            trade_id = str(uuid.uuid4())
            trade_tx = trade_result.get('tx_hash')
            
            # 5. Log to database
            trade_data = {
                'trade_id': trade_id,
                'telegram_user_id': user_id,
                'market_id': market_id,
                'amount_usd': amount_usdc,
                'entry_price': 0.5,  # Polymarket default
                'status': 'executed',
                'tx_hash': trade_tx
            }
            
            await db.create_trade(trade_data)
            
            # 6. Delete decrypted keypair
            del keypair
            
            print(f"[EXECUTOR] ✅ Kalshi trade executed: {trade_id}")
            
            return {
                'trade_id': trade_id,
                'tx_hash': trade_tx,
                'bridge_tx': bridge_tx,
                'status': 'executed',
                'platform': 'kalshi',
                'market': market_id,
                'amount_usd': amount_usdc,
                'position': position
            }
        
        except Exception as e:
            print(f"[EXECUTOR] ❌ Kalshi trade error: {e}")
            return {'error': str(e), 'status': 'failed'}
    
    async def execute_polymarket_trade(
        self,
        user_id: int,
        market_id: str,
        amount_usdc: float,
        position: str  # "YES" or "NO"
    ) -> Dict:
        """
        Execute real trade on Polymarket (Polygon).
        
        Flow:
        1. Get user's Polygon wallet
        2. Approve USDC
        3. Swap USDC for outcome token
        4. Log trade
        """
        
        print(f"[EXECUTOR] Polymarket trade: user={user_id}, market={market_id}, amount=${amount_usdc}, pos={position}")
        
        try:
            # 1. Get user's Polygon wallet
            user = await db.get_user(user_id)
            if not user:
                return {'error': 'User not found', 'status': 'failed'}
            
            polygon_address = user.get('polygon_public_key')
            if not polygon_address:
                return {'error': 'No Polygon wallet', 'status': 'failed'}
            
            # Get encrypted private key
            encrypted_key = user.get('polygon_private_key_encrypted')
            
            # 2. Place Polymarket trade
            print(f"[EXECUTOR] Placing Polymarket order...")
            trade_result = await polymarket.place_polymarket_trade(
                polygon_address,
                market_id,
                amount_usdc,
                position,
                encrypted_key  # Will be decrypted inside if needed
            )
            
            if not trade_result.get('success'):
                print(f"[EXECUTOR] Trade failed: {trade_result.get('error')}")
                return {'error': trade_result.get('error'), 'status': 'failed'}
            
            trade_id = str(uuid.uuid4())
            trade_tx = trade_result.get('tx_hash')
            
            # 3. Log to database
            trade_data = {
                'trade_id': trade_id,
                'telegram_user_id': user_id,
                'market_id': market_id,
                'amount_usd': amount_usdc,
                'entry_price': 0.5,
                'status': 'executed',
                'tx_hash': trade_tx
            }
            
            await db.create_trade(trade_data)
            
            print(f"[EXECUTOR] ✅ Polymarket trade executed: {trade_id}")
            
            return {
                'trade_id': trade_id,
                'tx_hash': trade_tx,
                'status': 'executed',
                'platform': 'polymarket',
                'market': market_id,
                'amount_usd': amount_usdc,
                'position': position
            }
        
        except Exception as e:
            print(f"[EXECUTOR] ❌ Polymarket trade error: {e}")
            return {'error': str(e), 'status': 'failed'}
    
    async def execute(
        self,
        user_id: int,
        market_id: str,
        amount_usd: float,
        position: str,
        platform: str  # "kalshi" or "polymarket"
    ) -> Dict:
        """
        Execute trade on specified platform.
        
        Args:
            user_id: Telegram user ID
            market_id: Market ID
            amount_usd: Trade amount in USD
            position: "YES" or "NO"
            platform: "kalshi" or "polymarket"
        
        Returns:
            Trade result
        """
        
        if platform == "kalshi":
            return await self.execute_kalshi_trade(user_id, market_id, amount_usd, position)
        elif platform == "polymarket":
            return await self.execute_polymarket_trade(user_id, market_id, amount_usd, position)
        else:
            return {'error': f'Unknown platform: {platform}', 'status': 'failed'}


# Global instance
trade_executor_real = TradeExecutorReal()
