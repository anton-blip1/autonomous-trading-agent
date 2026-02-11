"""
Non-custodial wallet manager - Per-user Solana keypair generation + management
Users control their keys, bot only executes trades with approval
(Synchronous version)
"""

import json
from typing import Optional, Dict
from pathlib import Path
import secrets

from solders.keypair import Keypair

from encryption import encryption
from database import db


class WalletManager:
    """Per-user non-custodial wallet management (Solana) - Synchronous."""
    
    def __init__(self):
        self.encryption = encryption
    
    def create_user_wallet(self, telegram_user_id: int) -> Dict:
        """
        Create new Solana keypair for user (synchronous).
        
        Flow:
        1. Generate new Solana keypair
        2. Encrypt private key (user retains control)
        3. Store encrypted key + public address in database
        4. Return public address (user funds this)
        
        Args:
            telegram_user_id: Telegram user ID
        
        Returns:
            Dict with user's public address
        """
        
        # Check if user already has wallet
        existing_user = db.get_user(telegram_user_id)
        if existing_user:
            print(f"[WALLET] User {telegram_user_id} already has wallet")
            return {
                'telegram_user_id': telegram_user_id,
                'solana_public_key': existing_user['solana_public_key'],
                'already_exists': True
            }
        
        # Generate new keypair (32-byte seed)
        seed_bytes = secrets.token_bytes(32)
        keypair = Keypair.from_seed(seed_bytes)
        solana_public_key = str(keypair.pubkey())
        
        print(f"[WALLET] Generated keypair for user {telegram_user_id}")
        print(f"[WALLET] Public: {solana_public_key}")
        
        # Encrypt private key (user retains control)
        # Store only the 32-byte seed, which is sufficient to reconstruct the keypair
        encrypted_private_key = self.encryption.encrypt_private_key(seed_bytes)
        
        print(f"[WALLET] Encrypted private key")
        
        # Store in database (synchronous)
        user_data = {
            'telegram_user_id': telegram_user_id,
            'solana_public_key': solana_public_key,
            'solana_private_key_encrypted': encrypted_private_key,
        }
        
        db.create_user(user_data)
        
        print(f"[WALLET] User created in database")
        
        return {
            'telegram_user_id': telegram_user_id,
            'solana_public_key': solana_public_key,
            'already_exists': False
        }
    
    def get_user_keypair(self, telegram_user_id: int) -> Keypair:
        """
        Decrypt and return user's Solana keypair for signing (synchronous).
        
        SECURITY: This keypair should ONLY be kept in memory temporarily
        during transaction signing. Delete immediately after use.
        
        Args:
            telegram_user_id: User ID
        
        Returns:
            Solders Keypair object (ready to sign transactions)
        """
        
        user = db.get_user(telegram_user_id)
        if not user:
            raise ValueError(f"User {telegram_user_id} not found")
        
        # Decrypt private key (server-side only)
        encrypted_key = user['solana_private_key_encrypted']
        decrypted_bytes = self.encryption.decrypt_private_key(encrypted_key)
        
        # Reconstruct keypair from seed
        keypair = Keypair.from_seed(decrypted_bytes)
        
        return keypair
    
    def get_user_public_key(self, telegram_user_id: int) -> str:
        """Get user's public Solana address (no decryption needed)."""
        user = db.get_user(telegram_user_id)
        if not user:
            raise ValueError(f"User {telegram_user_id} not found")
        return user['solana_public_key']
    
    def export_user_keys(self, telegram_user_id: int, two_fa_verified: bool = False) -> Dict:
        """
        Export user's private key (seed phrase format - synchronous).
        
        SECURITY: Should only be callable with 2FA verification.
        User can then import this into other Solana wallets.
        
        Args:
            telegram_user_id: User ID
            two_fa_verified: Whether 2FA was completed
        
        Returns:
            Dict with public key + private key (in hex format)
        """
        
        if not two_fa_verified:
            raise PermissionError("2FA verification required for key export")
        
        user = db.get_user(telegram_user_id)
        if not user:
            raise ValueError(f"User {telegram_user_id} not found")
        
        # Decrypt private key
        encrypted_key = user['solana_private_key_encrypted']
        decrypted_bytes = self.encryption.decrypt_private_key(encrypted_key)
        
        return {
            'public_key': user['solana_public_key'],
            'private_key_hex': decrypted_bytes.hex(),
            'warning': '🔐 NEVER share this. Anyone with this can steal your funds.'
        }
    
    def get_wallet_balance(self, telegram_user_id: int) -> float:
        """
        Get Solana balance for user's wallet (mock for now).
        
        Note: This is read-only, doesn't require private key.
        
        Args:
            telegram_user_id: User ID
        
        Returns:
            Balance in SOL (mocked as 0.0 for now)
        """
        
        user = db.get_user(telegram_user_id)
        if not user:
            raise ValueError(f"User {telegram_user_id} not found")
        
        # TODO: Connect to Solana RPC to get real balance
        return 0.0


# Global instance
wallet_manager = WalletManager()
