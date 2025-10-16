from v2.etl.models import Join


def dag_template(dag_id: str, description: str):
    return f"""
import base64
import json
import os.path
import shutil
import pandas as pd

from io import BytesIO
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def delete_index_column(df: pd.DataFrame):
    if 'Unnamed: 0' in df.columns:
        df.drop(columns=['Unnamed: 0'], inplace=True)

    return df


def save_extracted_file(df: pd.DataFrame, num: int):
    df = delete_index_column(df)
    df.to_csv(f'{{path}}/file_{{num}}.csv', index=False)


def configure_env():
    if os.path.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)


def extract_db(url: str, table: str, num: int):
    engine = create_engine(url=url)
    session_maker = sessionmaker(engine)

    with session_maker() as session:
        response = session.execute(text(f"SELECT * FROM {{table}}"))
        response = [res._asdict() for res in response.fetchall()]

    if len(response) > 0:
        pd.DataFrame(response).to_csv(f'{{path}}/db_{{num}}.csv', index=False)


def extract_api(url: str, method: str, auth: str, num: int):
    request = requests.get
    if method.lower() == 'get':
        request = requests.get
    elif method.lower() == 'post':
        request = requests.post

    response = request(url)
    pd.DataFrame(response.json()).to_csv(f'{{path}}/api_{{num}}.csv')


def extract_file(file: str, file_type: str, num: int):
    file = file.encode('utf-8')
    file = base64.b64decode(file)

    if file_type == 'json':
        df = pd.DataFrame(eval(file))
    elif file_type == 'csv':
        df = pd.read_csv(BytesIO(file))
    elif file_type == 'xlsx':
        df = pd.read_excel(BytesIO(file))
    else:
        raise RuntimeError(f'{{file_type}} not supported!')

    df = delete_index_column(df)
    df.to_csv(f'{{path}}/file_{{num}}.csv', index=False)


def join_dfs(target: pd.DataFrame, dfs: dict, join: dict):
    for key in join['join_columns'].keys():
        target = pd.merge(target,
                          dfs[key],
                          how=join['join_rule'],
                          left_on=join['target_columns'][key],
                          right_on=join['join_columns'][key])

    target.to_csv(f'{{path}}/result.csv')


def transform(target: str, join: dict):
    files = os.listdir(path)

    dfs = {{}}
    for file in files:
        if file.split('.')[0] == target:
            target_df = pd.read_csv(f'{{path}}/{{file}}')
        else:
            dfs[file.split('.')[0]] = pd.read_csv(f'{{path}}/{{file}}')

    join_dfs(target_df, dfs, join)


def load(url: str, table_name: str):
    data = pd.read_csv(f'{{path}}/result.csv')
    engine = create_engine(url)
    data.to_sql(con=engine, name=table_name, index=False)

dag_id = '{dag_id}'
path = f'./results/{{dag_id}}'

dag = DAG(
    dag_id=dag_id,
    start_date=days_ago(0, 0, 0, 0),
    description='desc',
    default_args={{
        'retries': 5,
        'retry_delay': timedelta(minutes=5)
    }}
)

config_op = PythonOperator(
    dag=dag,
    task_id='config_task',
    python_callable=configure_env
)
"""


def extract_db_template(func_num: int, url: str, table: str):
    return f"""
def extract_db_{func_num}():
    engine = create_engine(url={url})
    session_maker = sessionmaker(engine)

    with session_maker() as session:
        response = session.execute(text("SELECT * FROM {table}"))
        response = [res._asdict() for res in response.fetchall()]

"""


def db_operator_template(operator: str, url: str, table: str):
    template = f"""
{operator} = PythonOperator(
    dag=dag,
    task_id='{operator}',
    python_callable=extract_db,
    op_kwargs={{
        'url': '{url}',
        'table': '{table}',
        'num': {operator.split("_")[-1]}
    }}
)

"""

    return template


def api_operator_template(operation: str, url: str, method: str, auth: str):
    template = f"""
{operation} = PythonOperator(
    dag=dag,
    task_id='{operation}',
    python_callable=extract_api,
    op_kwargs={{
        'url': '{url}',
        'method': '{method}',
        'auth': '{auth}',
        'num': {operation.split("_")[-1]},
    }}
)
"""
    return template


def file_operator_template(num: int, file: str, file_type: str):
    template = f"""
extract_file_op_{num} = PythonOperator(
    dag=dag,
    task_id='extract_file_task_{num}',
    python_callable=extract_file,
    op_kwargs={{
        'file': '{file}',
        'file_type': '{file_type}',
        'num': {num}
    }}
)
"""

    return template


def transform_operator_template(target: str, join: Join):
    template = f"""
transform_op = PythonOperator(
    dag=dag,
    task_id='transform_task',
    python_callable=transform,
    op_kwargs={{
        'target': '{target}',
        'join': {join.as_dict()}
    }}
)
"""

    return template


def load_operator_template(url: str, table_name: str):
    template = f"""
load_op = PythonOperator(
    dag=dag,
    task_id='load_task',
    python_callable=load,
    op_kwargs={{
        'url': '{url}',
        'table_name': '{table_name}'
    }}
)
"""

    return template
