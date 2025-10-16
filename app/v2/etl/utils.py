import json
from enum import Enum

import requests
from fastapi import HTTPException
from requests.auth import HTTPBasicAuth
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from v2.config import (
    AIRFLOW_API_URL,
    INVENTORY_DB_URL,
    INVENTORY_DB_TABLE,
    KPI_DB_URL,
    KPI_DB_TABLE,
)
from v2.database.database import execute
from v2.database.schemas import Operation, DataSourceDB
from v2.models import Storage


def create_connection(storage: Storage):
    response = requests.post(
        f"{AIRFLOW_API_URL}/connections",
        json={
            "connection_id": f"{storage.name}_con",
            "conn_type": storage.conn_type,
            # 'description': 'string',
            "host": storage.host,
            "port": int(storage.port),
            "login": storage.user,
            # 'schema': 'string',
            "password": storage.password,
            # 'extra': 'string'
        },
        auth=HTTPBasicAuth("airflow", "airflow"),
        timeout=60,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail=response.json()["detail"]
        )


def update_connection(old_con: str, storage: Storage):
    response = requests.patch(
        f"{AIRFLOW_API_URL}/connections/{old_con}_con",
        json={
            "connection_id": f"{storage.name}_con",
            "conn_type": storage.conn_type,
            # 'description': 'string',
            "host": storage.host,
            "port": int(storage.port),
            "login": storage.user,
            # 'schema': 'string',
            "password": storage.password,
            # 'extra': 'string'
        },
        auth=HTTPBasicAuth("airflow", "airflow"),
        timeout=60,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail=response.json()["detail"]
        )


def delete_connection(conn_id: str):
    response = requests.delete(
        f"{AIRFLOW_API_URL}/connections/{conn_id}_con",
        auth=HTTPBasicAuth("airflow", "airflow"),
        timeout=60,
    )

    if response.status_code != 204:
        raise HTTPException(
            status_code=response.status_code, detail=response.json()["detail"]
        )


def read_file(file) -> dict:
    """Remake file representation into Dataframe
    :param file: file representation wrapped into FastAPI's `UploadFile~
    :return: Dataframe with table of values
    """
    content = file.file
    data = json.load(content)
    file.file.close()

    return data


def get_destination(destination: str):
    match destination:
        case Destination.OBJECT.value:
            url = INVENTORY_DB_URL
            table = INVENTORY_DB_TABLE
        case Destination.PM.value:
            url = KPI_DB_URL
            table = KPI_DB_TABLE
        case _:
            raise HTTPException(400, detail="Wrong destination!")

    return url, table


def clear_redundant_keys(target: dict, keys: list[str]) -> dict:
    for key in keys:
        if key in target.keys():
            target.pop(key)

    return target


def format_openapi(data: dict):
    result = []
    paths = data["paths"]
    schemas = data["components"]["schemas"]

    for path, data in paths.items():
        # print(path)
        # print(data)
        # print(methods)
        endpoints = cccc(data, path, schemas)
        result.extend(endpoints)
        # result.append(cccc(data, path, methods, endpoint, schemas))

    return result


def cccc(data: dict, path: str, schemas: dict) -> list:
    result = []
    for method, data in data.items():
        endpoint = {
            "path": path,
            "method": method,
            "title": data.pop("summary"),
            "parameters": [],
            "requestBody": {},
        }
        if "parameters" in data.keys():
            endpoint["parameters"].extend(get_parameters(data))
        if "requestBody" in data.keys():
            endpoint["requestBody"] = get_request_body(data, schemas)
        result.append(endpoint)

    return result


def get_parameters(data: dict) -> list:
    result = []
    for param in data["parameters"]:
        param["type"] = param["schema"]["type"]
        param.pop("schema")
        result.append(param)

    return result


def get_body_parameters(schemas: dict, ref: str) -> list:
    body_params = []
    ref = schemas[ref.split("/")[-1]]
    for param, properties in ref["properties"].items():
        body_params.append({"name": param, "type": properties["type"]})
    for body_param in body_params:
        body_param["required"] = body_param["name"] in ref["required"]

    return body_params


def get_request_body(data: dict, schemas: dict) -> dict:
    data = data["requestBody"]["content"]
    request_body = {"contentType": list(data.keys())[0]}
    data = data[request_body["contentType"]]["schema"]
    if "$ref" in data.keys():
        request_body["parameters"] = get_body_parameters(schemas, data["$ref"])
        request_body = clear_redundant_keys(
            request_body, ["$ref", "title", "type", "description"]
        )
        request_body["parameters"] = request_body["parameters"]
    else:
        request_body["parameters"] = data
    return request_body


def clear_dag_info(dag: dict) -> dict:
    dag.pop("default_view")
    dag.pop("file_token")
    dag.pop("fileloc")
    dag.pop("has_task_concurrency_limits")
    dag.pop("max_active_runs")
    dag.pop("max_active_tasks")
    dag.pop("next_dagrun_create_after")
    dag.pop("next_dagrun_data_interval_end")
    dag.pop("next_dagrun_data_interval_start")
    dag.pop("last_expired")
    dag.pop("last_pickled")
    dag.pop("pickle_id")
    dag.pop("root_dag_id")
    dag.pop("tags")
    dag.pop("is_subdag")
    dag.pop("last_parsed_time")
    dag.pop("timetable_description")
    dag.pop("scheduler_lock")

    return dag


def clear_dag_runs_info(dag_runs_info: list[dict]):
    last_run = None
    for dag_run in dag_runs_info:
        last_run = {
            "run_type": dag_run["run_type"],
            "state": dag_run["state"],
            "start_date": dag_run["start_date"],
            "end_date": dag_run["end_date"],
        }
        break

    return last_run


def define_dag_status(dag_info: dict):
    """
    statuses:
    New - doesn't have dagRuns
    Updated - done
    Warning,
    Off - is_active or is_paused is False
    Error - has_import_errors or dagRun status 'failed'

    :param dag_info:
    :return: correct status for this dag
    """
    if dag_info["has_import_errors"]:
        return "Error"
    if not dag_info["is_active"] or dag_info["is_paused"]:
        return "Off"
    if not dag_info["last_run"]:
        return "New"
    elif dag_info["last_run"]["state"] == "success":
        return "Updated"
    elif dag_info["last_run"]["state"] == "running":
        return "Running"

    return "Error"


async def create_extract_operation(
    session: AsyncSession, source_id: int, operation_name: str
):
    params = {
        "name": operation_name,
        "operation_type": "extract",
        "source_id": source_id,
    }
    await execute(session, insert(Operation), params=params)
    operation = await execute(
        session, select(Operation.id).where(Operation.name == params["name"])
    )
    return operation[0]["id"]


async def create_data_source(
    session: AsyncSession, name: str, group_id: int
) -> int:
    params = {"name": name, "group_id": group_id}
    await execute(session, insert(DataSourceDB), params)
    query = select(DataSourceDB.id).where(
        DataSourceDB.name == name and DataSourceDB.group_id == group_id
    )
    response = await execute(session, query)
    return response[0]["id"]


class MimeTypes(Enum):
    CSV = "text/csv"
    JSON = "application/json"


class Destination(Enum):
    OBJECT = "object"
    PM = "PM"
