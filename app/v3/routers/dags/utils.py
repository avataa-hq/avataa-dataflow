import os

from fastapi import HTTPException


def raise_error_if_dag_exist(dag_id: str = None):
    if dag_id + ".py" in os.listdir(os.getcwd() + "/dags"):
        raise HTTPException(
            status_code=422, detail=f"DAG with id = {dag_id} already exists"
        )
