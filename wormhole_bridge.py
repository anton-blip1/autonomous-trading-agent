"""
Wormhole Bridge - Cross-chain liquidity aggregation for autonomous trading.
Handles token bridging between Solana and Polygon with timeout/retry logic.
"""
import json
import time
from typing import Optional, Dict
from datetime import datetime, timedelta
import requests

from config import (
    SOLANA_RPC_URL,
    POLYGON_RPC_URL,
    BRIDGE_TIMEOUT_SECONDS,
    BRIDGE_RETRY_ATTEMPTS,
)


class WormholeBridge:
    """Orchestrates cross-chain token bridging via Wormhole protocol."""

    def __init__(self):
        self.solana_rpc = SOLANA_RPC_URL
        self.polygon_rpc = POLYGON_RPC_URL
        self.bridge_timeout = BRIDGE_TIMEOUT_SECONDS
        self.retry_attempts = BRIDGE_RETRY_ATTEMPTS
        
        # Bridge fee estimates (in percent)
        self.bridge_fees = {
            "solana_to_polygon": 0.75,
            "polygon_to_solana": 0.75,
        }
        
        # Bridge addresses (Wormhole wrapped token addresses)
        self.bridge_addresses = {
            "solana_usdc": "EPjFWaLb3cwQfRLvEsxVfSKdhfxhTv3kNmYWe27SSn1z",  # Native USDC on Solana
            "polygon_usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC on Polygon
            "wrapped_solana_on_polygon": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # Wrapped SOL
            "wrapped_polygon_on_solana": "So11111111111111111111111111111111111111112",  # Wrapped SOL
        }
        
        self.active_bridges = {}  # Track active bridge operations

    def estimate_bridge_cost(
        self,
        amount_usd: float,
        from_chain: str,
        to_chain: str
    ) -> float:
        """Estimate the cost of bridging tokens between chains.
        
        Args:
            amount_usd: Amount to bridge in USD
            from_chain: Source chain ('solana' or 'polygon')
            to_chain: Destination chain ('solana' or 'polygon')
            
        Returns:
            Bridge cost in USD (fee percentage)
        """
        try:
            if from_chain == to_chain:
                return 0.0
            
            bridge_type = f"{from_chain}_to_{to_chain}"
            fee_percent = self.bridge_fees.get(bridge_type, 0.75)
            
            # Fee calculation: amount * (fee_percent / 100)
            base_fee = amount_usd * (fee_percent / 100)
            
            # Add gas cost estimate ($0.50 - $2 depending on network congestion)
            gas_estimate = 0.5  # Conservative estimate
            
            total_cost = base_fee + gas_estimate
            
            print(f"[BRIDGE] Cost estimate for {amount_usd} USD ({from_chain}→{to_chain}): ${total_cost:.2f}")
            return total_cost
            
        except Exception as e:
            print(f"[BRIDGE ERROR] Failed to estimate cost: {e}")
            return amount_usd * 0.01  # Fallback to 1% fee

    def execute_bridge(
        self,
        from_wallet,
        to_address: str,
        amount_usd: float,
        from_chain: str,
        to_chain: str
    ) -> Optional[str]:
        """Execute a cross-chain token bridge.
        
        Args:
            from_wallet: Source wallet object with keypair/private_key
            to_address: Destination wallet address
            amount_usd: Amount to bridge in USD
            from_chain: Source chain ('solana' or 'polygon')
            to_chain: Destination chain ('solana' or 'polygon')
            
        Returns:
            Bridge transaction hash or None
        """
        try:
            if from_chain == to_chain:
                print(f"[BRIDGE] Source and destination chains are the same: {from_chain}")
                return None
            
            # Check bridge liquidity
            has_liquidity = self._check_bridge_liquidity(from_chain, to_chain, amount_usd)
            if not has_liquidity:
                print(f"[BRIDGE] Insufficient liquidity for bridge: {amount_usd} USD")
                return None
            
            # Create bridge transaction payload
            bridge_tx = {
                "from_chain": from_chain,
                "to_chain": to_chain,
                "from_address": from_wallet.get_address(),
                "to_address": to_address,
                "amount_usd": amount_usd,
                "bridge_fee": self.estimate_bridge_cost(amount_usd, from_chain, to_chain),
                "timestamp": datetime.now().isoformat(),
                "status": "created"
            }
            
            # Sign transaction (simulate for devnet)
            tx_hash = self._sign_bridge_transaction(bridge_tx, from_wallet, from_chain)
            bridge_tx["tx_hash"] = tx_hash
            bridge_tx["status"] = "signed"
            
            # Submit to source chain
            success = self._submit_bridge_transaction(bridge_tx, from_chain)
            if success:
                bridge_tx["status"] = "submitted"
                self.active_bridges[tx_hash] = bridge_tx
                print(f"[BRIDGE] Submitted bridge transaction: {tx_hash}")
                return tx_hash
            else:
                print(f"[BRIDGE] Failed to submit bridge transaction")
                return None
                
        except Exception as e:
            print(f"[BRIDGE ERROR] Bridge execution failed: {e}")
            return None

    def _check_bridge_liquidity(self, from_chain: str, to_chain: str, amount_usd: float) -> bool:
        """Check if Wormhole has sufficient liquidity for the bridge.
        
        In production, would query actual Wormhole liquidity pools.
        For devnet, we assume sufficient liquidity up to reasonable amounts.
        """
        try:
            # Devnet limits for testing
            max_bridge_amount = 10000  # $10k per transaction
            
            if amount_usd > max_bridge_amount:
                print(f"[BRIDGE] Amount exceeds max devnet limit: {amount_usd} > {max_bridge_amount}")
                return False
            
            # Check pool state (mock for devnet)
            pool_id = f"{from_chain}_{to_chain}_pool"
            available_liquidity = max_bridge_amount * 2  # Assume 2x liquidity
            
            if amount_usd > available_liquidity:
                return False
            
            return True
            
        except Exception as e:
            print(f"[BRIDGE ERROR] Liquidity check failed: {e}")
            return False

    def _sign_bridge_transaction(self, bridge_tx: Dict, from_wallet, from_chain: str) -> str:
        """Sign the bridge transaction with the source wallet.
        
        Args:
            bridge_tx: Bridge transaction details
            from_wallet: Wallet to sign with
            from_chain: Source chain
            
        Returns:
            Simulated transaction hash
        """
        try:
            # In production, would use solders (Solana) or web3 (Polygon) to sign
            # For devnet testing, generate deterministic mock hash
            
            tx_data = f"{bridge_tx['from_address']}{bridge_tx['to_address']}{bridge_tx['amount_usd']}"
            mock_hash = f"{from_chain}_bridge_{hash(tx_data) & 0xffffffff:08x}"
            
            print(f"[BRIDGE] Signed {from_chain} bridge transaction: {mock_hash}")
            return mock_hash
            
        except Exception as e:
            print(f"[BRIDGE ERROR] Failed to sign bridge transaction: {e}")
            return None

    def _submit_bridge_transaction(self, bridge_tx: Dict, from_chain: str) -> bool:
        """Submit the signed bridge transaction to the source chain RPC.
        
        Args:
            bridge_tx: Signed bridge transaction
            from_chain: Source chain ('solana' or 'polygon')
            
        Returns:
            True if successfully submitted
        """
        try:
            # Select RPC endpoint
            rpc_url = self.solana_rpc if from_chain == "solana" else self.polygon_rpc
            
            # In production, would send actual signed transaction to RPC
            # For devnet, just simulate submission
            
            print(f"[BRIDGE] Submitting to {from_chain} RPC: {rpc_url}")
            # Mock successful submission for devnet
            return True
            
        except Exception as e:
            print(f"[BRIDGE ERROR] Failed to submit to {from_chain} RPC: {e}")
            return False

    def wait_for_confirmation(
        self,
        tx_hash: str,
        from_chain: str,
        timeout: int = None
    ) -> bool:
        """Wait for bridge transaction confirmation.
        
        Args:
            tx_hash: Bridge transaction hash
            from_chain: Source chain
            timeout: Max seconds to wait (uses config default if None)
            
        Returns:
            True if confirmed, False if timeout
        """
        timeout = timeout or self.bridge_timeout
        deadline = datetime.now() + timedelta(seconds=timeout)
        
        try:
            while datetime.now() < deadline:
                # Check transaction status
                bridge_tx = self.active_bridges.get(tx_hash)
                if not bridge_tx:
                    print(f"[BRIDGE] Transaction not found: {tx_hash}")
                    return False
                
                # Poll RPC for confirmation
                confirmed = self._check_confirmation_on_chain(tx_hash, from_chain)
                
                if confirmed:
                    bridge_tx["status"] = "confirmed"
                    bridge_tx["confirmed_at"] = datetime.now().isoformat()
                    print(f"[BRIDGE] Transaction confirmed: {tx_hash}")
                    return True
                
                # Wait 5 seconds before retrying
                print(f"[BRIDGE] Waiting for confirmation... ({tx_hash})")
                time.sleep(5)
            
            # Timeout reached
            print(f"[BRIDGE] Confirmation timeout after {timeout}s: {tx_hash}")
            bridge_tx = self.active_bridges.get(tx_hash)
            if bridge_tx:
                bridge_tx["status"] = "timeout"
            return False
            
        except Exception as e:
            print(f"[BRIDGE ERROR] Confirmation wait failed: {e}")
            return False

    def _check_confirmation_on_chain(self, tx_hash: str, from_chain: str) -> bool:
        """Check if transaction is confirmed on the source chain.
        
        In production, would call RPC getSignatureStatuses (Solana) or 
        eth_getTransactionReceipt (Polygon).
        For devnet, simulate 2-3 polls to confirmation.
        """
        try:
            bridge_tx = self.active_bridges.get(tx_hash)
            if not bridge_tx:
                return False
            
            # Simulate confirmation after 2-3 checks
            poll_count = bridge_tx.get("poll_count", 0)
            bridge_tx["poll_count"] = poll_count + 1
            
            # Devnet: confirm after 2 polls (10 seconds)
            if poll_count >= 2:
                return True
            
            return False
            
        except Exception as e:
            print(f"[BRIDGE ERROR] Confirmation check failed: {e}")
            return False

    def handle_timeout(
        self,
        tx_hash: str,
        fallback_action: callable = None
    ) -> bool:
        """Handle a timed-out bridge transaction with retry/fallback logic.
        
        Args:
            tx_hash: Transaction hash that timed out
            fallback_action: Callable to execute if retry fails
            
        Returns:
            True if recovered (retry succeeded or fallback executed)
        """
        try:
            bridge_tx = self.active_bridges.get(tx_hash)
            if not bridge_tx:
                print(f"[BRIDGE] Timeout handler: Transaction not found: {tx_hash}")
                return False
            
            retry_count = bridge_tx.get("retry_count", 0)
            
            # Retry logic
            if retry_count < self.retry_attempts:
                print(f"[BRIDGE] Retrying timed-out transaction ({retry_count + 1}/{self.retry_attempts})")
                bridge_tx["retry_count"] = retry_count + 1
                bridge_tx["status"] = "retrying"
                
                # Attempt resubmission
                success = self._submit_bridge_transaction(bridge_tx, bridge_tx["from_chain"])
                if success:
                    return self.wait_for_confirmation(tx_hash, bridge_tx["from_chain"], timeout=60)
            
            # Fallback action
            if fallback_action and callable(fallback_action):
                print(f"[BRIDGE] Executing fallback action for {tx_hash}")
                try:
                    fallback_action(bridge_tx)
                    bridge_tx["status"] = "fallback_executed"
                    return True
                except Exception as e:
                    print(f"[BRIDGE ERROR] Fallback action failed: {e}")
                    bridge_tx["status"] = "failed"
                    return False
            
            # No recovery possible
            bridge_tx["status"] = "failed"
            print(f"[BRIDGE] Transaction failed after retries: {tx_hash}")
            return False
            
        except Exception as e:
            print(f"[BRIDGE ERROR] Timeout handler failed: {e}")
            return False

    def get_bridge_status(self, tx_hash: str) -> Optional[Dict]:
        """Get the current status of a bridge transaction.
        
        Args:
            tx_hash: Transaction hash to check
            
        Returns:
            Bridge transaction details or None
        """
        return self.active_bridges.get(tx_hash)

    def get_all_active_bridges(self) -> Dict[str, Dict]:
        """Get all active bridge transactions."""
        return self.active_bridges.copy()


# Global bridge instance
bridge = WormholeBridge()
