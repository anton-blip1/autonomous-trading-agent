"""
Encryption module - AES-256 private key encryption
For storing user's Solana keypairs securely in database
"""

import os
from cryptography.fernet import Fernet
from typing import Tuple

class KeyEncryption:
    """Encrypt/decrypt private keys for secure storage."""
    
    def __init__(self):
        """Initialize encryption with master key from environment."""
        self.master_key = os.environ.get('ENCRYPTION_MASTER_KEY')
        if not self.master_key:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY not set in environment.\n"
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "Add to .env: ENCRYPTION_MASTER_KEY=<key>"
            )
        
        self.cipher = Fernet(self.master_key.encode() if isinstance(self.master_key, str) else self.master_key)
    
    def encrypt_private_key(self, private_key_bytes: bytes) -> str:
        """
        Encrypt private key for storage in database.
        
        Args:
            private_key_bytes: Raw private key bytes
        
        Returns:
            Encrypted key as string
        """
        encrypted = self.cipher.encrypt(private_key_bytes)
        return encrypted.decode('utf-8')
    
    def decrypt_private_key(self, encrypted_key_str: str) -> bytes:
        """
        Decrypt private key from database.
        
        Args:
            encrypted_key_str: Encrypted key string from database
        
        Returns:
            Decrypted private key bytes
        
        SECURITY: This decrypted key should ONLY be held in memory temporarily
        during transaction signing. Delete immediately after use.
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_key_str.encode() if isinstance(encrypted_key_str, str) else encrypted_key_str)
            return decrypted
        except Exception as e:
            raise ValueError(f"Failed to decrypt private key: {e}")

# Global encryption instance
encryption = KeyEncryption()

# Helper functions
def encrypt_key(private_key_bytes: bytes) -> str:
    """Shorthand for encrypting a key."""
    return encryption.encrypt_private_key(private_key_bytes)

def decrypt_key(encrypted_key_str: str) -> bytes:
    """Shorthand for decrypting a key."""
    return encryption.decrypt_private_key(encrypted_key_str)

# One-time: Generate encryption key
def generate_encryption_key() -> str:
    """Generate a new encryption key. Use this ONCE during setup."""
    key = Fernet.generate_key()
    return key.decode('utf-8')
