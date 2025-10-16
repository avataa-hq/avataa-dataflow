from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, validator


class DBLocalHost(Enum):
    HOST = "localhost"


class SourceType(Enum):
    RESTAPI = "RestAPI"
    DB = "DB"
    FILE = "File"


class SourceConDataBaseModel(BaseModel):
    source_data_columns: Optional[Union[list, None]] = None

    @validator("source_data_columns")
    def check_source_data_columns_not_empty(cls, source_data_columns, values):
        if source_data_columns is not None:
            for x in source_data_columns:
                if not x:
                    raise ValueError(
                        "source_data_columns can`t have empty column names"
                    )

        return source_data_columns


class SourceModelBase(BaseModel):
    id: int = Field(...)


class SourceModelBaseCreate(BaseModel):
    name: str = Field(min_length=1)
    group_id: int = Field(gt=0)


class SourceModelBaseInfo(SourceModelBaseCreate, SourceModelBase):
    pass
