from enum import Enum

from typing import Optional

from pydantic import BaseModel, Field

from airflow_functions.airflow_source_managers.routers.sources.models.general_model import (
    SourceModelBaseInfo,
    SourceModelBaseCreate,
    SourceType,
    SourceConDataBaseModel,
)


class FileExtension(Enum):
    CSV = "csv"
    EXCEL = "xlsx"
    OlD_EXCEL = "xls"


class FileImportType(Enum):
    SFTP = "SFTP"
    FTP = "FTP"
    MANUAL = "Manual"


class FileBaseModel(BaseModel):
    con_type: Optional[str] = Field(
        default=SourceType.FILE.value, regex=rf"^{SourceType.FILE.value}$"
    )


class SFTPConnectionModelCheck(BaseModel):
    host: str = Field(...)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    file_path: Optional[str] = Field(default="/")
    file_name: Optional[str] = None


class SFTPConnectionModelCheckPath(BaseModel):
    host: str = Field(...)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    file_path: Optional[str] = Field(default="/")


class SFTPConnectionModel(SourceConDataBaseModel, BaseModel):
    import_type: Optional[str] = Field(
        default=FileImportType.SFTP.value,
        regex=rf"^{FileImportType.SFTP.value}$",
    )
    host: str = Field(...)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    file_path: Optional[str] = Field(default="/")
    file_name: str = Field(min_length=1)


class SFTPModel(FileBaseModel):
    con_data: SFTPConnectionModel = Field(...)


class SFTPModelInfo(SFTPModel, SourceModelBaseInfo):
    pass


class SFTPModelCreate(SFTPModel, SourceModelBaseCreate):
    pass


class ManualConnectionModelInfo(SourceConDataBaseModel, BaseModel):
    import_type: Optional[str] = Field(
        default=FileImportType.MANUAL.value,
        regex=rf"^{FileImportType.MANUAL.value}$",
    )
    file_name: str


class ManualModelInfo(FileBaseModel, SourceModelBaseInfo):
    con_data: ManualConnectionModelInfo = Field(...)
