"""
Drop-in encrypted read/write helpers for outputs/ files.
Key is derived from a passphrase (env var) — never stored on disk.
"""
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

SALT = b"shaheen-eye-pfis-salt-v1"  # fixed salt is OK here since key also depends on secret passphrase

def _get_fernet():
    passphrase = os.getenv("PFIS_ENCRYPTION_KEY")
    if not passphrase:
        raise RuntimeError("PFIS_ENCRYPTION_KEY not set in environment/.env")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=200_000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return Fernet(key)

def write_encrypted(path, data: bytes):
    f = _get_fernet()
    with open(path, "wb") as fh:
        fh.write(f.encrypt(data))

def read_encrypted(path) -> bytes:
    f = _get_fernet()
    with open(path, "rb") as fh:
        return f.decrypt(fh.read())

# Convenience wrappers for common cases
def write_text(path, text: str):
    write_encrypted(path, text.encode("utf-8"))

def read_text(path) -> str:
    return read_encrypted(path).decode("utf-8")