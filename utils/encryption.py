import os
import base64
import hashlib
from typing import Optional

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

class CredentialCipher:
    """
    Helper enkripsi dan dekripsi kredensial akun menggunakan Fernet (AES-128-CBC)
    dengan fallback otomatis ke standard library jika paket cryptography belum terpasang.
    """

    def __init__(self, key: Optional[str] = None):
        self.key_str = key or os.getenv("SECRET_KEY", "3vTYPpQgPk0np8fRj8tLuhcLdEDx1rFE3fWYyIyN2bc=")
        if HAS_CRYPTOGRAPHY:
            try:
                raw_bytes = self.key_str.encode('utf-8')
                if len(raw_bytes) != 44:
                    raw_bytes = base64.urlsafe_b64encode(hashlib.sha256(raw_bytes).digest())
                self.fernet = Fernet(raw_bytes)
            except Exception:
                self.fernet = None
        else:
            self.fernet = None

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        if self.fernet:
            return self.fernet.encrypt(plain_text.encode('utf-8')).decode('utf-8')
        
        # Fallback XOR + Base64
        key_bytes = hashlib.sha256(self.key_str.encode('utf-8')).digest()
        data_bytes = plain_text.encode('utf-8')
        xored = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes))
        return "fb:" + base64.urlsafe_b64encode(xored).decode('utf-8')

    def decrypt(self, cipher_text: str) -> str:
        if not cipher_text:
            return ""
        if cipher_text.startswith("fb:"):
            try:
                raw_b64 = cipher_text[3:]
                xored = base64.urlsafe_b64decode(raw_b64.encode('utf-8'))
                key_bytes = hashlib.sha256(self.key_str.encode('utf-8')).digest()
                decrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(xored))
                return decrypted.decode('utf-8')
            except Exception:
                return cipher_text

        if self.fernet:
            try:
                return self.fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
            except Exception:
                return cipher_text
        return cipher_text

_default_cipher = None

def get_cipher() -> CredentialCipher:
    global _default_cipher
    if _default_cipher is None:
        _default_cipher = CredentialCipher()
    return _default_cipher

def encrypt_credential(text: str) -> str:
    return get_cipher().encrypt(text)

def decrypt_credential(text: str) -> str:
    return get_cipher().decrypt(text)
