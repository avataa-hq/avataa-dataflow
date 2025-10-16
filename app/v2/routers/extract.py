import os

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy import create_engine, insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from v2.config import AIRFLOW_API_URL, AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PASS
from v2.database.database import get_session, execute
from v2.database.schemas import DBSettings
from v2.etl.models import DB, API, SFTPConnection, File, Join
from v2.etl.templates import (
    dag_template,
    db_operator_template,
    file_operator_template,
    transform_operator_template,
    load_operator_template,
    api_operator_template,
)
from v2.etl.utils import (
    get_destination,
    read_file,
    format_openapi,
    clear_dag_info,
    define_dag_status,
    clear_dag_runs_info,
    create_extract_operation,
    create_data_source,
)

router = APIRouter(prefix="/etl", tags=["Extract sources"])


@router.post("/extract")
async def extract_source(
    name: str,
    group_id: int,
    description: str,
    dbs: list[DB] | None = None,
    apis: list[API] | None = None,
    sftps: list[SFTPConnection] | None = None,
    files: list[File] | None = None,
    session: AsyncSession = Depends(get_session),
):
    # create data_source
    source_id = await create_data_source(session, name, group_id)

    dag = dag_template(dag_id=name, description=description)

    operations = []
    if dbs is not None:
        for idx, db in enumerate(dbs):
            operation = f"db_{idx}"
            params = db.__dict__
            params["operation_id"] = create_extract_operation(
                session, source_id=source_id, operation_name=operation
            )
            await execute(session, insert(DBSettings), params)
            dag += db_operator_template(
                f"extract_{operation}", db.get_link(), db.table
            )
            operations.append(f"extract_{operation}")

    if apis is not None:
        for idx, api in enumerate(apis):
            operation = f"api_{idx}"
            await create_extract_operation(
                session, source_id=source_id, operation_name=operation
            )
            dag += api_operator_template(
                f"extract_{operation}",
                f"{api.entry_point}{api.end_point}",
                "GET",
                str(api.authentication),
            )
            operations.append(f"extract_{operation}")

    if sftps is not None:
        operations["sftp"] = []
        for sftp in sftps:
            pass

    if files is not None:
        operations["file"] = []
        for idx, file in enumerate(files):
            dag += file_operator_template(idx, file.content, file.file_type)
            operations["file"].append(f"extract_file_op_{idx}")

    op_template = "config_op >> ["
    for key in operations.keys():
        for idx, operation in enumerate(operations[key]):
            op_template += f"{operation}, "
    op_template = op_template[:-2]
    op_template += "]"

    dag += op_template

    with open(f"./dags/{name}.py", "w") as file:
        file.write(dag)

    await session.commit()
    return


@router.post("/test_connection")
def test_connection(
    db: DB | None, api: API | None = None, sftp: SFTPConnection | None = None
):
    if db:
        engine = create_engine(url=db.get_link())

        try:
            engine.begin()
            return {"status": "Success"}
        except OperationalError as exc:
            if len(exc.orig.args) > 0:
                return {"status": exc.orig.args[0]}
            else:
                return {
                    "status": f"Cannot connect with credentials: "
                    f"login-{engine.url.username}, password-{engine.url.password}"
                }

    if api:
        try:
            response = requests.get(api.openapi_url, timeout=60)
        except ConnectionError:
            return {"status": "Failed connect!"}
        if response.status_code == 401:
            return {"status": "Failed authorization!"}
        else:
            return format_openapi(response.json())
    if sftp:
        pass


@router.post("/test_openapi")
def test_openapi(openapi: UploadFile):
    data = read_file(openapi)
    return format_openapi(data)


@router.post("/transform")
def transform_sources(
    name: str,
    target: str,
    join: Join,
):
    try:
        with open(f"./dags/{name}.py", "r") as file:
            dag = file.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="DAG with this name does not exist!"
        )

    dag = dag.split("\n")
    operations = dag[-1]
    dag = "\n".join(dag[:-1])
    dag += transform_operator_template(target, join)
    operations += " >> transform_op"
    dag += f"\n{operations}"
    with open(f"./dags/{name}.py", "w") as file:
        file.write(dag)

    return


@router.post("/load")
def load(name: str, destination: str):
    url, table = get_destination(destination)

    with open(f"./dags/{name}.py", "r") as file:
        dag = file.read()

    dag = dag.split("\n")
    operations = dag[-1]
    dag = "\n".join(dag[:-1])
    dag += load_operator_template(url, table)
    operations += " >> load_op"
    dag += f"\n{operations}"
    with open(f"./dags/{name}.py", "w") as file:
        file.write(dag)

    return


@router.get("/dag_state")
def get_dag_state(name: str):
    response = requests.get(
        f"{AIRFLOW_API_URL}/dags/{name}/dagRuns",
        auth=HTTPBasicAuth(AIRFLOW_USER, AIRFLOW_PASS),
        timeout=60,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail=response.json()["detail"]
        )

    response = response.json()["dag_runs"]
    response = sorted(response, key=lambda x: x["start_date"])[-1]

    return response


@router.get("/dag_state_2")
def get_dag_state_2(name: str):
    response = response = requests.get(
        f"{AIRFLOW_API_URL}/dags/{name}/dagRuns",
        auth=HTTPBasicAuth(AIRFLOW_USER, AIRFLOW_PASS),
        timeout=60,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail=response.json()["detail"]
        )

    dag_runs = response.json()["dag_runs"]

    response = requests.get(
        f"{AIRFLOW_URL}/object/grid_data?dag_id={name}",
        auth=HTTPBasicAuth(AIRFLOW_USER, AIRFLOW_PASS),
        timeout=60,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail=response.json()["detail"]
        )

    response = response.json()
    dag_runs = response["dag_runs"]
    tasks = response["groups"]["children"]
    print(tasks)
    for dag_run in dag_runs:
        pass

    return response


@router.get("/dags")
def get_dags():
    response = requests.get(
        f"{AIRFLOW_API_URL}/dags",
        auth=HTTPBasicAuth(AIRFLOW_USER, AIRFLOW_PASS),
        timeout=60,
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code)

    dags = response.json()["dags"]

    for dag in dags:
        response = requests.get(
            f"{AIRFLOW_API_URL}/dags/{dag['dag_id']}/dagRuns",
            auth=HTTPBasicAuth(AIRFLOW_USER, AIRFLOW_PASS),
            timeout=60,
        )
        runs = sorted(
            response.json()["dag_runs"],
            key=lambda x: x["start_date"],
            reverse=True,
        )
        dag["last_run"] = clear_dag_runs_info(runs)
        dag["status"] = define_dag_status(dag)

        clear_dag_info(dag)

    return dags


@router.get("/dag_result")
def get_dag_result(name: str):
    try:
        files = os.listdir(f"./results/{name}")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="DAG does not exist or did not worked yet!"
        )

    if "result.csv" in files:
        df = pd.read_csv(f"./results/{name}/result.csv").head(15)
        df = df.fillna("")
        df = df.to_dict("records")
    else:
        df = {"log": "err"}

    return df
