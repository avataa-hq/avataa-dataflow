from sqlalchemy import create_engine
from airflow.exceptions import AirflowSkipException

from airflow_functions.airflow_source_managers.config import (
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASS,
    DB_NAME,
)
from airflow.models import TaskInstance


def delete_db_tables_if_load_fails(
    db_driver="postgresql",
    db_host=DB_HOST,
    db_port=DB_PORT,
    db_user=DB_USER,
    db_pass=DB_PASS,
    db_name=DB_NAME,
    create_db_tasks_ids: list = None,
    load_data_task_ids: list = None,
    force_clear_data: bool = False,
    **kwargs,
):
    table_names = []
    load_data_task_status = []
    if create_db_tasks_ids:
        for create_db_task_id in create_db_tasks_ids:
            table_name = kwargs["ti"].xcom_pull(task_ids=create_db_task_id)
            if table_name:
                table_names.append(table_name)

    if load_data_task_ids:
        dag_instance = kwargs["dag"]
        execution_date = kwargs["execution_date"]
        for task_id in load_data_task_ids:
            operator_instance = dag_instance.get_task(task_id)
            task_status = TaskInstance(
                operator_instance, execution_date
            ).current_state()
            load_data_task_status.append(
                True if task_status == "success" else False
            )

    if not all(load_data_task_status) or force_clear_data:
        database_url = (
            f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        )
        engine = create_engine(
            database_url, echo=False, pool_size=20, max_overflow=100
        )

        sql = []
        for table_name in table_names:
            sql.append(f"DROP TABLE IF EXISTS {table_name}")
        sql = ";".join(sql)
        engine.execute(sql)
    else:
        raise AirflowSkipException
