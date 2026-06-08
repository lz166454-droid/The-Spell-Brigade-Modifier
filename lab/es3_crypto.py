
import gzip
import hashlib
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

ES3_PASSWORD = 'vhp*UCETJFwjE*8B!EPE'
PBKDF2_ITERATIONS = 100
KEY_LENGTH = 16
IV_LENGTH = 16

def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), salt, PBKDF2_ITERATIONS, dklen=KEY_LENGTH)

def _is_gzipped(data: bytes) -> bool:
    return len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B

def _aes_cbc_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()

def _aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    padder = PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()

def decrypt_es3(data: bytes, password: str = ES3_PASSWORD) -> bytes:
    if len(data) < IV_LENGTH:
        raise ValueError('ES3 data too short')
    iv = data[:IV_LENGTH]
    ciphertext = data[IV_LENGTH:]
    key = _derive_key(password, iv)
    result = _aes_cbc_decrypt(key, iv, ciphertext)
    if _is_gzipped(result):
        result = gzip.decompress(result)
    return result

def encrypt_es3(data: bytes, password: str = ES3_PASSWORD) -> bytes:
    compressed = gzip.compress(data)
    iv = os.urandom(IV_LENGTH)
    key = _derive_key(password, iv)
    encrypted = _aes_cbc_encrypt(key, iv, compressed)
    return iv + encrypted
