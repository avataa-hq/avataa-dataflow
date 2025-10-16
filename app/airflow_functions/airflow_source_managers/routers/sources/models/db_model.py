"""DB Source validation models"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from airflow_functions.airflow_source_managers.routers.sources.models.general_model import (
    SourceModelBaseInfo,
    SourceModelBaseCreate,
    SourceType,
    SourceConDataBaseModel,
)


class DBDriverTypes(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"


class DBConnectionModel(BaseModel):
    db_type: DBDriverTypes = Field(...)
    host: str = Field(min_length=1)
    port: int = Field(gt=0)
    user: str = Field(min_length=1)
    password: str = Field(min_length=1)
    db_name: str = Field(min_length=1)

    class Config:
        use_enum_values = True


class DBConnectionModelCheck(DBConnectionModel):
    db_name: Optional[str]


class DBConnectionModelCheckColumns(DBConnectionModel):
    db_table: str = Field()


class DBConnectionModelCreate(SourceConDataBaseModel, DBConnectionModel):
    db_table: str = Field()


class DBModelBase(BaseModel):
    con_type: Optional[str] = Field(
        default=SourceType.DB.value, regex=rf"^{SourceType.DB.value}$"
    )
    con_data: DBConnectionModelCreate = Field(...)

    class Config:
        use_enum_values = True


class DBModelInfo(DBModelBase, SourceModelBaseInfo):
    pass


class DBModelCreate(DBModelBase, SourceModelBaseCreate):
    pass
