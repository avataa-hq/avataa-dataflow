import os
import pickle
from copy import copy

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from v3.database.database import get_session
from v3.database.schemas import Source
from v3.routers.dags.models import DAG
from v3.routers.dags.utils import raise_error_if_dag_exist

router = APIRouter(prefix="/dags", tags=["Dags"])


@router.post("")
async def create_dag(dag: DAG, session: AsyncSession = Depends(get_session)):
    raise_error_if_dag_exist(dag.dag_id)

    stmt = (
        select(Source)
        .where(Source.id.in_(dag.sources))
        .options(selectinload(Source.group))
    )
    sources = await session.execute(stmt)
    sources = sources.scalars().all()

    sources_managers = {
        "-".join([source.group.name, source.name]): source for source in sources
    }

    base_path = os.getcwd()
    imports = base_path + "/airflow_templates/load/imports.txt"
    start_date = [dag.start_date.year, dag.start_date.month, dag.start_date.day]

    dag_header = (
        f"with DAG(dag_id='{dag.dag_id}', description='{dag.description}', "
        f"schedule='{dag.schedule_interval}', "
        f"start_date=datetime({', '.join(str(x) for x in start_date)}), catchup=False,)"
        " as dag:"
    )

    start_all_task = base_path + "/airflow_templates/load/task_start_all.txt"

    end_all_tasks = (
        base_path + "/airflow_templates/load/task_end_all_loaded.txt"
    )

    template_path = (
        base_path + "/airflow_templates/load/tasks_for_one_source.txt"
    )
    deletes_db_if_load_fails_path = (
        base_path + "/airflow_templates/load/if_load_fails_delete_dbs.txt"
    )

    data = []

    with open(imports) as imports_file:
        data.append(imports_file.read())

    data.append(dag_header)

    with open(start_all_task) as start_all_task_file:
        data.append("\n" + start_all_task_file.read())

    with open(end_all_tasks) as end_all_tasks_file:
        data.append("\n" + end_all_tasks_file.read())
        data.append("\n")

    start_order = []
    middle_order = []
    end_order = []
    create_db_task_ids = []
    load_data_task_ids = []
    template = ""
    with open(template_path) as template_file:
        template = template_file.read()

    for key, source in sources_managers.items():
        key_without_spaces = key.replace(" ", "").replace("-", "_")

        manager_name = "manager_for" + key_without_spaces

        source = source.__dict__
        source["con_data"] = source["_con_data"]
        del source["_con_data"]
        del source["_sa_instance_state"]
        del source["group"]

        pickled_source_instance = pickle.dumps(source).hex()
        check_connection_task_name = key_without_spaces + "_check_connection"
        load_data_task_name = key_without_spaces + "_load_data"
        check_connection_task_id = key_without_spaces + "_Check_connection"
        load_data_task_id = key_without_spaces + "_Load_data"
        create_db_task = key_without_spaces + "_create_db"
        create_db_task_id = create_db_task + "_create_database"
        create_db_task_ids.append(create_db_task_id)
        load_data_task_ids.append(load_data_task_id)

        start_order.append(f"\n    start_load >> {check_connection_task_name}")
        middle_order.append(
            f"\n    {check_connection_task_name} >> {create_db_task}"
        )
        middle_order.append(f"\n    {create_db_task} >> {load_data_task_name}")
        end_order.append(f"\n    {load_data_task_name} >> end_load")
        end_order.append(
            f"\n    {load_data_task_name} >> delete_db_tables_if_load_fails"
        )

        source_template = copy(template)

        source_template = source_template.replace(
            "$manager_name$", manager_name
        )
        source_template = source_template.replace(
            "$pickled_source_instance$", pickled_source_instance
        )
        source_template = source_template.replace(
            "$check_connection_task_name$", check_connection_task_name
        )
        source_template = source_template.replace(
            "$check_connection_task_id$", check_connection_task_id
        )
        source_template = source_template.replace(
            "$load_data_task_name$", load_data_task_name
        )
        source_template = source_template.replace(
            "$load_data_task_id$", load_data_task_id
        )
        source_template = source_template.replace(
            "$create_db_task$", create_db_task
        )
        source_template = source_template.replace(
            "$create_db_task_id$", create_db_task_id
        )
        source_template = source_template.replace("$dag_id$", dag.dag_id)
        source_template = source_template.replace(
            "$source_id$", str(source["id"])
        )

        data.append(source_template)
        data.append("\n")

    with open(deletes_db_if_load_fails_path) as deletes_db_if_load_fails_task:
        temp_data = deletes_db_if_load_fails_task.read().replace(
            "$create_db_tasks_ids$", str(create_db_task_ids)
        )
        temp_data = temp_data.replace(
            "$load_data_task_ids$", str(load_data_task_ids)
        )
        data.append("\n" + temp_data)
        data.append("\n")

    data.extend(start_order)
    data.extend(middle_order)
    data.extend(end_order)

    with open(base_path + "/dags/" + dag.dag_id + ".py", mode="w") as f:
        f.writelines(data)
    return {"created": "ok"}
