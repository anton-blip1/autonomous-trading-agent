"""
Trade Executor - Execute trades with non-custodial signing
User's keypair signs transactions (user retains control)
"""

import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime

from wallet_manager import wallet_manager
from database import db
from config import Config


class TradeExecutor:
    """Execute trades using user's keypair (non-custodial)."""
    
    def __init__(self):
        self.auto_exec_threshold = Config.AUTO_EXEC_THRESHOLD_USD
        self.approval_threshold = Config.APPROVAL_THRESHOLD_USD
    
    async def execute(
        self,
        user_id: int,
        market_id: str,
        amount_usd: float,
        position: str = 'YES'
    ) -> Dict:
        """
        Execute trade with user's keypair (non-custodial).
        
        Flow:
        1. Get user's encrypted keypair
        2. Decrypt (server-side only, temporary)
        3. Build transaction
        4. Sign with user's key (NOT bot's)
        5. Broadcast to blockchain
        6. Delete decrypted key from memory
        7. Log trade
        
        Args:
            user_id: Telegram user ID
            market_id: Market ID to trade
            amount_usd: Trade amount in USD
            position: 'YES' or 'NO'
        
        Returns:
            Trade result {trade_id, tx_hash, status}
        """
        
        print(f"[EXECUTOR] Trade request: user={user_id}, market={market_id}, amount=${amount_usd}, pos={position}")
        
        try:
            # 1. Validate user
            user = await db.get_user(user_id)
            if not user:
                return {'error': 'User not found', 'status': 'failed'}
            
            # 2. Get market
            market = await db.get_market(market_id)
            if not market:
                return {'error': 'Market not found', 'status': 'failed'}
            
            # 3. Get user's keypair (decrypt)
            print(f"[EXECUTOR] Decrypting user keypair...")
            keypair = await wallet_manager.get_user_keypair(user_id)
            user_public_key = str(keypair.pubkey())
            
            # 4. Build transaction (mock - in reality would use Kalshi/Polymarket SDKs)
            print(f"[EXECUTOR] Building transaction...")
            tx = self._build_transaction(
                market_id=market_id,
                user_public_key=user_public_key,
                amount_usd=amount_usd,
                position=position,
                platform=market['platform']
            )
            
            # 5. Sign transaction with USER's keypair (NOT bot's)
            print(f"[EXECUTOR] Signing with user's keypair (non-custodial)...")
            signed_tx = self._sign_transaction(tx, keypair)
            
            # 6. Broadcast (mock)
            print(f"[EXECUTOR] Broadcasting to {market['platform']}...")
            tx_hash = self._broadcast_transaction(signed_tx, market['platform'])
            
            # 7. CRITICAL: Delete decrypted keypair from memory
            print(f"[EXECUTOR] Cleanup: deleting decrypted keypair...")
            del keypair
            
            # 8. Create trade record
            trade_id = str(uuid.uuid4())
            trade_data = {
                'trade_id': trade_id,
                'telegram_user_id': user_id,
                'market_id': market_id,
                'amount_usd': amount_usd,
                'entry_price': market['current_price'],
                'status': 'executed',
                'tx_hash': tx_hash
            }
            
            await db.create_trade(trade_data)
            
            print(f"[EXECUTOR] ✅ Trade executed: {trade_id}")
            
            return {
                'trade_id': trade_id,
                'tx_hash': tx_hash,
                'status': 'executed',
                'amount_usd': amount_usd,
                'market': market['title'],
                'entry_price': market['current_price']
            }
        
        except Exception as e:
            print(f"[EXECUTOR] ❌ Error: {e}")
            return {'error': str(e), 'status': 'failed'}
    
    def _build_transaction(
        self,
        market_id: str,
        user_public_key: str,
        amount_usd: float,
        position: str,
        platform: str
    ) -> Dict:
        """Build unsigned transaction."""
        
        tx = {
            'market_id': market_id,
            'user': user_public_key,
            'amount': amount_usd,
            'position': position,
            'platform': platform,
            'timestamp': datetime.now().isoformat(),
            'instructions': [
                {
                    'type': 'trade',
                    'market': market_id,
                    'order_type': 'market',
                    'side': position,
                    'size': amount_usd
                }
            ]
        }
        
        return tx
    
    def _sign_transaction(self, tx: Dict, keypair) -> Dict:
        """Sign transaction with user's keypair."""
        
        # In production: use Solana SDK to sign
        # For now: mock signature
        
        import hashlib
        import json
        
        # Create deterministic signature (mock)
        tx_bytes = json.dumps(tx, sort_keys=True).encode()
        signature = hashlib.sha256(tx_bytes).hexdigest()[:64]
        
        signed_tx = tx.copy()
        signed_tx['signature'] = signature
        signed_tx['signer'] = str(keypair.pubkey())
        signed_tx['signed_at'] = datetime.now().isoformat()
        
        return signed_tx
    
    def _broadcast_transaction(self, signed_tx: Dict, platform: str) -> str:
        """Broadcast transaction to blockchain/platform."""
        
        # In production: use Kalshi/Polymarket SDKs to broadcast
        # For now: mock tx hash
        
        import hashlib
        import json
        
        tx_bytes = json.dumps(signed_tx, sort_keys=True).encode()
        tx_hash = hashlib.sha256(tx_bytes).hexdigest()
        
        print(f"[EXECUTOR] Broadcast to {platform}: {tx_hash[:16]}...")
        
        return tx_hash
    
    async def should_auto_execute(self, amount_usd: float) -> bool:
        """Check if trade should auto-execute without approval."""
        return amount_usd < self.auto_exec_threshold
    
    async def requires_approval(self, amount_usd: float) -> bool:
        """Check if trade requires user approval."""
        return amount_usd >= self.auto_exec_threshold and amount_usd < self.approval_threshold


# Global instance
trade_executor = TradeExecutor()
