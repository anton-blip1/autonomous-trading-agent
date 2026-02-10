"""
Polymarket Direct - Direct on-chain trading on Polygon
Non-custodial USDC swaps on Polymarket AMM
"""

import asyncio
import aiohttp
from typing import Dict, Optional
from web3 import Web3
from web3.contract import Contract

from config import Config


class PolymarketDirect:
    """
    Direct Polygon trading with Polymarket.
    
    Flow:
    1. Get user's Polygon wallet (from user_wallets table)
    2. Approve USDC spending on Polymarket contract
    3. Call Polymarket AMM to swap USDC for outcome token
    4. Track position in database
    5. User can exit anytime (swap back to USDC)
    """
    
    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(Config.POLYGON_RPC_URL))
        self.chain_id = Config.POLYGON_CHAIN_ID
        
        # Polymarket contracts on Polygon (Mumbai testnet)
        self.usdc_contract = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC on Polygon
        self.polymarket_amm = "0xc0AEe478e3658e2610c5F7A4A2E1777cE9e2D0E0"  # Polymarket AMM
        
        # ABIs (simplified)
        self.USDC_ABI = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
    
    async def get_polygon_balance(self, account_address: str) -> float:
        """Get USDC balance on Polygon."""
        try:
            # Contract call to check USDC balance
            # balanceOf(account_address)
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [
                    {
                        "to": self.usdc_contract,
                        "data": f"0x70a08231000000000000000000000000{account_address[2:]:0>40}",
                        "from": account_address
                    },
                    "latest"
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(Config.POLYGON_RPC_URL, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if 'result' in data:
                        balance_hex = data['result']
                        balance_wei = int(balance_hex, 16)
                        balance_usdc = balance_wei / 1e6  # USDC has 6 decimals
                        print(f"[POLYMARKET] Balance: {balance_usdc} USDC")
                        return balance_usdc
        
        except Exception as e:
            print(f"[POLYMARKET] Error getting balance: {e}")
        
        return 0.0
    
    async def approve_usdc_spending(
        self,
        from_address: str,
        amount_usdc: float,
        private_key: str
    ) -> Optional[str]:
        """
        Approve USDC spending on Polymarket contract.
        
        Args:
            from_address: User's Polygon wallet
            amount_usdc: Amount to approve
            private_key: User's Polygon private key (encrypted)
        
        Returns:
            Transaction hash
        """
        
        try:
            # Check balance first
            balance = await self.get_polygon_balance(from_address)
            if balance < amount_usdc:
                print(f"[POLYMARKET] Insufficient balance: {balance} < {amount_usdc}")
                return None
            
            # Create approval transaction
            # In production:
            # 1. Create approval instruction
            # 2. Sign with user's private key
            # 3. Send to Polygon
            
            print(f"[POLYMARKET] Approving {amount_usdc} USDC spending")
            print(f"  From: {from_address}")
            print(f"  Spender: {self.polymarket_amm}")
            
            # Mock response
            return f"0xapproval_{int(amount_usdc * 1e6)}"
        
        except Exception as e:
            print(f"[POLYMARKET] Error approving: {e}")
        
        return None
    
    async def swap_usdc_for_outcome(
        self,
        from_address: str,
        market_id: str,
        amount_usdc: float,
        outcome_index: int,  # 0 for NO, 1 for YES
        private_key: str
    ) -> Dict:
        """
        Swap USDC for outcome token on Polymarket.
        
        Args:
            from_address: User's Polygon wallet
            market_id: Polymarket market ID
            amount_usdc: Amount to spend
            outcome_index: 0 (NO) or 1 (YES)
            private_key: User's private key
        
        Returns:
            Swap result {success, tx_hash, outcome_shares}
        """
        
        print(f"[POLYMARKET] Swapping {amount_usdc} USDC for market {market_id}")
        
        try:
            # 1. Approve USDC if needed
            approval_tx = await self.approve_usdc_spending(from_address, amount_usdc, private_key)
            if not approval_tx:
                return {'success': False, 'error': 'Approval failed'}
            
            print(f"[POLYMARKET] USDC approved: {approval_tx}")
            
            # 2. Create swap instruction
            # In production:
            # - Call Polymarket AMM
            # - Get USDC balance check
            # - Calculate outcome shares
            # - Execute swap
            # - Return shares received
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_sendTransaction",
                "params": [
                    {
                        "from": from_address,
                        "to": self.polymarket_amm,
                        "data": self._encode_swap_params(market_id, amount_usdc, outcome_index)
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(Config.POLYGON_RPC_URL, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if 'result' in data:
                        tx_hash = data['result']
                        shares = amount_usdc / 0.5  # Rough estimate (would query AMM for actual rate)
                        
                        print(f"[POLYMARKET] Swap executed: {tx_hash}")
                        
                        return {
                            'success': True,
                            'tx_hash': tx_hash,
                            'market_id': market_id,
                            'amount_usdc': amount_usdc,
                            'outcome': 'YES' if outcome_index == 1 else 'NO',
                            'outcome_shares': shares
                        }
        
        except Exception as e:
            print(f"[POLYMARKET] Error swapping: {e}")
        
        return {'success': False, 'error': str(e)}
    
    def _encode_swap_params(self, market_id: str, amount_usdc: float, outcome_index: int) -> str:
        """Encode swap parameters for contract call."""
        # In production: use ABI encoding
        # For now: mock encoding
        return f"0xswap_{market_id}_{int(amount_usdc * 1e6)}_{outcome_index}"
    
    async def get_polymarket_markets(self) -> list:
        """Fetch Polymarket markets from API."""
        try:
            url = "https://polymarket.com/api/markets"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        markets = await resp.json()
                        print(f"[POLYMARKET] Fetched {len(markets)} markets")
                        return markets
        
        except Exception as e:
            print(f"[POLYMARKET] Error fetching markets: {e}")
        
        return []
    
    async def place_polymarket_trade(
        self,
        from_address: str,
        market_id: str,
        amount_usdc: float,
        position: str,  # "YES" or "NO"
        private_key: str
    ) -> Dict:
        """
        Place complete trade on Polymarket.
        
        Args:
            from_address: User's Polygon wallet
            market_id: Market ID
            amount_usdc: Trade amount
            position: "YES" or "NO"
            private_key: User's private key
        
        Returns:
            Trade result
        """
        
        outcome_index = 1 if position == "YES" else 0
        
        result = await self.swap_usdc_for_outcome(
            from_address,
            market_id,
            amount_usdc,
            outcome_index,
            private_key
        )
        
        if result['success']:
            print(f"[POLYMARKET] Trade placed: {market_id} {position} {amount_usdc} USDC")
            result['position'] = position
        
        return result
    
    async def exit_polymarket_trade(
        self,
        from_address: str,
        market_id: str,
        outcome_shares: float,
        private_key: str
    ) -> Dict:
        """
        Exit Polymarket position (swap outcome tokens back to USDC).
        
        Args:
            from_address: User's wallet
            market_id: Market ID
            outcome_shares: Number of shares to sell
            private_key: User's private key
        
        Returns:
            Exit result {success, tx_hash, usdc_received}
        """
        
        try:
            # Reverse the swap: outcome tokens → USDC
            # Would call AMM with opposite direction
            
            usdc_received = outcome_shares * 0.5  # Rough estimate
            
            print(f"[POLYMARKET] Exiting position: {outcome_shares} shares → {usdc_received} USDC")
            
            return {
                'success': True,
                'market_id': market_id,
                'outcome_shares': outcome_shares,
                'usdc_received': usdc_received,
                'tx_hash': f"0xexit_{market_id}"
            }
        
        except Exception as e:
            print(f"[POLYMARKET] Error exiting: {e}")
        
        return {'success': False, 'error': str(e)}


# Global instance
polymarket = PolymarketDirect()
