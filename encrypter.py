import os
import json
import base64
from typing import Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loki_logger import get_logger , log_security_event

from config import get_config



class Encrypter:
    """Simple JSON encryption/decryption tool"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        """Initialize with environment variables"""
        self.enabled = self.config.ENCRYPTION_ENABLED
        self.password = self.config.ENCRYPTION_PASSWORD
        self.algorithm = self.config.ENCRYPTION_ALGORITHM or 'SHA256'
        self.salt = b'config-salt-2024'
        self._fernet = None
    
    @property
    def fernet(self):
        """Get Fernet cipher instance"""
        if self._fernet is None:
            # Map algorithm names to hash functions
            algorithms = {
                'SHA256': hashes.SHA256(),
                'SHA512': hashes.SHA512(),
                'SHA384': hashes.SHA384(),
                'SHA224': hashes.SHA224(),
            }
            
            hash_algorithm = algorithms.get(self.algorithm)
            if not hash_algorithm:
                raise ValueError(f"Unsupported algorithm: {self.algorithm}. Supported: {list(algorithms.keys())}")
            
            kdf = PBKDF2HMAC(
                algorithm=hash_algorithm,
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
            self._fernet = Fernet(key)
        return self._fernet
    
    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt JSON data and return base64 encoded string"""
        log_security_event(self.logger, "Encrypting sensitive data")
        log_security_event(self.logger, f"Encryption enabled: {self.enabled}")
        if not self.enabled:
            return json.dumps(data)
        
        json_str = json.dumps(data, separators=(',', ':'))
        encrypted_bytes = self.fernet.encrypt(json_str.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt base64 encoded data and return JSON dict"""
        log_security_event(self.logger, "Decrypting sensitive data")
        log_security_event(self.logger, f"Encryption enabled: {self.enabled}")
        if not self.enabled:
            return json.loads(encrypted_data)
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            json_str = decrypted_bytes.decode()
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Failed to decrypt: {e}")