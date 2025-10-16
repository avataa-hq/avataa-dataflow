# Dataflow

MS stores information about available data sources for generation in future

## Environment variables

```toml
AIRFLOW_HOST=<airflow_webserver_host>
AIRFLOW_PASS=<airflow_password>
AIRFLOW_PORT=<airflow_webserver_port>
AIRFLOW_PROTOCOL=<airflow_webserver_protocol>
AIRFLOW_USER=<airflow_user>
CRYPTO_KEY=<dataflow_crypto_key>
DATAVIEW_MANAGER_GRPC_PORT=<dataview_manager_grpc_port>
DATAVIEW_MANAGER_HOST=<dataview_manager_host>
DEBUG=<True/False>
DOCS_CUSTOM_ENABLED=<True/False>
DOCS_REDOC_JS_URL=<redoc_js_url>
DOCS_SWAGGER_CSS_URL=<swagger_css_url>
DOCS_SWAGGER_JS_URL=<swagger_js_url>
INVENTORY_GRPC_PORT=<inventory_grpc_port>
INVENTORY_HOST=<inventory_host>
KEYCLOAK_HOST=<keycloak_host>
KEYCLOAK_PORT=<keycloak_port>
KEYCLOAK_PROTOCOL=<keycloak_protocol>
KEYCLOAK_REALM=avataa
KEYCLOAK_REDIRECT_HOST=<keycloak_external_host>
KEYCLOAK_REDIRECT_PORT=<keycloak_external_port>
KEYCLOAK_REDIRECT_PROTOCOL=<keycloak_external_protocol>
MINIO_BUCKET=<minio_dataflow_bucket>
MINIO_PASSWORD=<minio_dataflow_password>
MINIO_SECURE=<True/False>
MINIO_URL=<minio_api_host>
MINIO_USER=<minio_dataflow_user>
SECURITY_TYPE=<security_type>
UVICORN_WORKERS=<uvicorn_workers_number>
V2_DB_HOST=<pgbouncer/postgres_host>
V2_DB_NAME=<pgbouncer/postgres_dataflow_db_v2_name>
V2_DB_PASS=<pgbouncer/postgres_dataflow_password>
V2_DB_PORT=<pgbouncer/postgres_port>
V2_DB_TYPE=postgresql+asyncpg
V2_DB_USER=<pgbouncer/postgres_dataflow_user>
V3_DB_HOST=<pgbouncer/postgres_host>
V3_DB_NAME=<pgbouncer/postgres_dataflow_db_v3_name>
V3_DB_PASS=<pgbouncer/postgres_dataflow_password>
V3_DB_PORT=<pgbouncer/postgres_port>
V3_DB_TYPE=postgresql+asyncpg
V3_DB_USER=<pgbouncer/postgres_dataflow_user>
```

## Explanation

- KEYCLOAK_HOST
- KEYCLOAK_PORT
- KEYCLOAK_REALM
- DEBUG - enables debug mode (disabled authorization, enabled CORS for all sources)

## Version 1

### Database
- V1_DB_TYPE - driver for database (must be async)
- V1_DB_HOST
- V1_DB_PORT
- V1_DB_USER
- V1_DB_PASS
- V1_DB_NAME

## Version 2

### Database
- V2_DB_TYPE - driver for database (must be async)
- V2_DB_HOST
- V2_DB_PORT
- V2_DB_USER
- V2_DB_PASS
- V2_DB_NAME

### Airflow
- AIRFLOW_HOST
- AIRFLOW_PORT

### Load destinations
- INVENTORY_DB_URL
- INVENTORY_DB_TABLE
- KPI_DB_URL
- KPI_DB_URL

### Compose

- `REGISTRY_URL` - Docker regitry URL, e.g. `harbor.domain.com`
- `PLATFORM_PROJECT_NAME` - Docker regitry project Docker image can be downloaded from, e.g. `avataa`

# Run command
``alembic upgrade head && uvicorn main:app [options]``
> Note: if running without `alembic upgrade head` MS will start with empty sources

# For develop
1. **DO NOT** track env.py file (create new change list)
2. If running with PyCharm change ``env.py`` file
    - 49 line - replace DATABASE_URL with your URL
    - 76 line - replace DATABASE_URL with your URL
3. In terminal run ``alembic upgrade head``

# Tests
Just run command in terminal: `pytest`