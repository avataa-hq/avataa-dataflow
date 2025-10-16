import os

# DATABASE
DB_TYPE = os.environ.get("V3_DB_TYPE", "V3_DB_TYPE")
DB_USER = os.environ.get("V3_DB_USER", "V3_DB_USER")
DB_PASS = os.environ.get("V3_DB_PASS", "V3_DB_PASS")
DB_HOST = os.environ.get("V3_DB_HOST", "V3_DB_HOST")
DB_PORT = os.environ.get("V3_DB_PORT", "V3_DB_PORT")
DB_NAME = os.environ.get("V3_DB_NAME", "V3_DB_NAME")

DATABASE_URL = f"{DB_TYPE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# cryptography.fernet Fernet.generate_key()
CRYPTO_KEY = os.environ.get(
    "CRYPTO_KEY", "7RMBdPjt7oQRsxh-wqs1YVVYxBY-1oVVrrOjzV6-h1U="
)

# MinIO settings
MINIO_URL = os.environ.get("MINIO_URL", "MINIO_URL")
MINIO_USER = os.environ.get("MINIO_USER", "MINIO_USER")
MINIO_PASSWORD = os.environ.get("MINIO_PASSWORD", "MINIO_PASSWORD")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "MINIO_BUCKET")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "True").upper() in (
    "TRUE",
    "Y",
    "YES",
    "1",
)
