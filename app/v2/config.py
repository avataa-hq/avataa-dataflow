import os

# DATABASE
DB_TYPE = os.environ.get("V2_DB_TYPE", "postgresql+asyncpg")
DB_USER = os.environ.get("V2_DB_USER", "dataflow_admin")
DB_PASS = os.environ.get("V2_DB_PASS", None)
DB_HOST = os.environ.get("V2_DB_HOST", "pgbouncer")
DB_PORT = os.environ.get("V2_DB_PORT", "5432")
DB_NAME = os.environ.get("V2_DB_NAME", "dataflow_v2")

DATABASE_URL = f"{DB_TYPE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# AIRFLOW
AIRFLOW_PROTOCOL = os.environ.get("AIRFLOW_PROTOCOL", "http")
AIRFLOW_HOST = os.environ.get("AIRFLOW_HOST", "localhost")
AIRFLOW_PORT = os.environ.get("AIRFLOW_PORT")
AIRFLOW_URL = f"{AIRFLOW_PROTOCOL}://{AIRFLOW_HOST}"
if AIRFLOW_PORT:
    AIRFLOW_URL += f":{AIRFLOW_PORT}"
AIRFLOW_API_URL = f"{AIRFLOW_URL}/api/v1"
AIRFLOW_USER = os.environ.get("AIRFLOW_USER", "airflow")
AIRFLOW_PASS = os.environ.get("AIRFLOW_PASS", "airflow")

# LOAD DESTINATIONS
INVENTORY_DB_URL = os.environ.get("INVENTORY_DB_URL")
INVENTORY_DB_TABLE = os.environ.get("INVENTORY_DB_TABLE")

KPI_DB_URL = os.environ.get("KPI_DB_URL")
KPI_DB_TABLE = os.environ.get("KPI_DB_TABLE")
