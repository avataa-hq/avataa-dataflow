from enum import Enum
import pandas as pd


class RESTAPIResponseTypes(Enum):
    LIST_OF_VALUES = "List of values"
    LIST_OF_OBJECTS = "List of objects"
    OBJECT = "Object"
    FILE = "File"


FILE_EXT_READERS = {
    "csv": pd.read_csv,
    "xlsx": pd.read_excel,
    "xls": pd.read_excel,
    "json": pd.read_json,
}


def get_file_reader_by_ext(ext: str):
    """Returns pandas read file method for particular file ext, otherwise raises error"""
    file_reader = FILE_EXT_READERS.get(ext)
    if file_reader is None:
        raise NotImplementedError(
            f"File reader for file with extension = '{ext}' not implemented."
        )
    return file_reader
