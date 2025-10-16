import json

from cryptography.fernet import Fernet
from airflow_functions.airflow_source_managers.config import CRYPTO_KEY


def encrypt_data(data: str):
    """Returns  encrypted data"""
    fernet = Fernet(CRYPTO_KEY)
    res = fernet.encrypt(bytes(data, "utf-8"))
    return res.decode("utf-8")


def decrypt_data(data: str):
    """Returns decrypted data
    Parameters:
                data (str): string representation of bytes obtained by bytes_data.decode('utf-8')
    """
    fernet = Fernet(CRYPTO_KEY)
    res = fernet.decrypt(data)
    return json.loads(res)
