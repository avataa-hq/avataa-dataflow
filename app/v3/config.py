import os

# DATABASE
DB_TYPE = os.environ.get("V3_DB_TYPE", "postgresql+asyncpg")
DB_USER = os.environ.get("V3_DB_USER", "dataflow_admin")
DB_PASS = os.environ.get("V3_DB_PASS", None)
DB_HOST = os.environ.get("V3_DB_HOST", "pgbouncer")
DB_PORT = os.environ.get("V3_DB_PORT", "5432")
DB_NAME = os.environ.get("V3_DB_NAME", "dataflow_v3")

DATABASE_URL = f"{DB_TYPE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# AIRFLOW
AIRFLOW_PROTOCOL = os.environ.get("AIRFLOW_PROTOCOL", "http")
AIRFLOW_HOST = os.environ.get("AIRFLOW_HOST", "airflow-webserver")
AIRFLOW_PORT = os.environ.get("AIRFLOW_PORT", "8080")
AIRFLOW_URL = f"{AIRFLOW_PROTOCOL}://{AIRFLOW_HOST}"
if AIRFLOW_PORT:
    AIRFLOW_URL += f":{AIRFLOW_PORT}"
AIRFLOW_API_URL = f"{AIRFLOW_URL}/api/v1"
AIRFLOW_USER = os.environ.get("AIRFLOW_USER", "airflow-user")
AIRFLOW_PASS = os.environ.get("AIRFLOW_PASS", None)

# cryptography.fernet Fernet.generate_key()
CRYPTO_KEY = os.environ.get("CRYPTO_KEY", None)

# MinIO settings
MINIO_URL = os.environ.get("MINIO_URL", "minio:9000")
MINIO_USER = os.environ.get("MINIO_USER", "dataflow")
MINIO_PASSWORD = os.environ.get("MINIO_PASSWORD", None)
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "dataflow")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "False").upper() in (
    "TRUE",
    "Y",
    "YES",
    "1",
)


DATAVIEW_MANAGER_HOST = os.environ.get(
    "DATAVIEW_MANAGER_HOST", "dataview-manager"
)
DATAVIEW_MANAGER_GRPC_PORT = os.environ.get(
    "DATAVIEW_MANAGER_GRPC_PORT", "50051"
)
DATAVIEW_GRPC_URL = f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
