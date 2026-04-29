import random
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


def random_string(length: int) -> str:
    aes_chars = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
    return "".join(random.choice(aes_chars) for _ in range(length))


def encrypt_password(password: str, key: str) -> str:
    try:
        if not key:
            return password
        key_bytes = key.strip().encode("utf-8")
        iv = random_string(16)
        iv_bytes = iv.encode("utf-8")
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        text = random_string(64) + password
        padded_text = pad(text.encode("utf-8"), AES.block_size)
        encrypted = cipher.encrypt(padded_text)
        return base64.b64encode(encrypted).decode("utf-8")
    except Exception:
        return password
