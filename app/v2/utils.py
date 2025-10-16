from io import BytesIO
from itertools import groupby

import pandas as pd
from fastapi import HTTPException


def define_group_key(row) -> dict:
    return {"id": row.pop("group_id"), "name": row.pop("group_name")}


def define_source_key(row) -> dict:
    return {
        "id": row.pop("source_id"),
        "name": row.pop("source_name"),
        "has_preview": row.pop("has_preview"),
    }


def group_sources(data) -> list[dict]:
    data = [item._asdict() for item in data]
    group_iterator = groupby(data, key=define_group_key)

    result = []
    for group_key, group in group_iterator:
        source_iterator = groupby(list(group), key=define_source_key)
        for source_key, source in source_iterator:
            source_key["child"] = list(source)
            group_key["child"] = source_key
        result.append(group_key)

    return result


def group_previews(data: list) -> list:
    """Format preview's data
    :param data: list of raw preview values
    :return: grouped preview's data
    """
    data = [preview._asdict() for preview in data]
    data = sorted(data, key=lambda x: x["row"])

    iterator = groupby(data, lambda x: x.pop("row"))

    result = []
    for key, group in iterator:
        tmp = [{dct["name"]: dct["value"]} for dct in list(group)]
        result.append({k: v for dct in tmp for k, v in dct.items()})

    return result


def read_file(file) -> pd.DataFrame:
    """Remake file representation into Dataframe
    :param file: file representation wrapped into FastAPI's `UploadFile~
    :return: Dataframe with table of values
    """
    contents = file.file.read()
    data = BytesIO(contents)
    df: pd.DataFrame = pd.read_excel(data)
    data.close()
    file.file.close()

    return df


def build_preview_data(df: pd.DataFrame, source_id: int) -> list[dict]:
    """Function split input dataframe to list with preview parameters for each row
    :param df: dataframe with preview data in table format
    :param source_id: id of sources' group preview will be added to
    :return list with separate preview object (row-column intersection)
    """
    df: list[dict] = df.head(10).to_dict(orient="records")

    result = []
    for idx, row in enumerate(df):
        for key, value in row.items():
            result.append(
                {
                    "name": str(key),
                    "value": str(value),
                    "row": idx + 1,
                    "source": source_id,
                }
            )

    return result


def check_input_file(file) -> None:
    """Function checks if file is defined and has correct extension
    :param file: file representation wrapped with FastAPI's `UploadFile`
    :raises HTTPException: File not provided
    :raises HTTPException: File has extension other than .xlsx
    """
    if file is None:
        raise HTTPException(status_code=400, detail="Provide file, please!")

    if (
        file.content_type
        != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        raise HTTPException(
            status_code=400, detail="Wrong extension! Please, provide .xlsx"
        )
