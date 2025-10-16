from enum import Enum

from typing import Optional, Literal

from pydantic import BaseModel, Field, validator

from v3.routers.sources.models.general_model import (
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


class DatePatternType(str, Enum):
    DMY = "DDMMYYYY"
    MDY = "MMDDYYYY"
    YMD = "YYYYMMDD"


class FileBaseModel(BaseModel):
    con_type: Optional[str] = Field(
        default=SourceType.FILE.value, regex=rf"^{SourceType.FILE.value}$"
    )


class RemoteFile(BaseModel):
    file_path: str = Field(default="/", min_length=1)
    file_name: str = Field(min_length=1)
    date_pattern: DatePatternType | None = Field(default=None)
    offset: int | None = Field(default=None)

    @validator("offset")
    def check_offset(cls, value, values):
        if value is not None and not values.get("date_pattern"):
            value = None
        if value is None and values.get("date_pattern"):
            value = 0

        return value

    @validator("date_pattern")
    def check_date_pattern(cls, value, values):
        if value is None:
            return

        if value.value not in values["file_name"]:
            raise ValueError("Date pattern must be provided in file name!")

        return value


class RemoteFileCheck(BaseModel):
    file_path: str = Field(default="/", min_length=1)
    file_name: Literal["test.csv"] = Field(default="test.csv")


class SFTPConnectionModelCheck(BaseModel):
    host: str = Field(...)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    file: RemoteFile


class SFTPConnectionModelCheckPath(BaseModel):
    host: str = Field(...)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    file: RemoteFileCheck


class SFTPConnectionModel(SourceConDataBaseModel, BaseModel):
    import_type: Optional[str] = Field(
        default=FileImportType.SFTP.value,
        regex=rf"^{FileImportType.SFTP.value}$",
    )
    host: str = Field(...)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    file: RemoteFile


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
    filename: str


class ManualModelInfo(FileBaseModel, SourceModelBaseInfo):
    con_data: ManualConnectionModelInfo = Field(...)


class FTPConnectionModel(SourceConDataBaseModel, BaseModel):
    import_type: Optional[str] = Field(
        default=FileImportType.FTP.value, regex=rf"^{FileImportType.FTP.value}$"
    )
    host: str = Field(...)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)
    file: RemoteFile


class FTPModel(FileBaseModel):
    con_data: FTPConnectionModel = Field(...)


class FTPModelCreate(FTPModel, SourceModelBaseCreate):
    pass


class FTPModelInfo(FTPModel, SourceModelBaseInfo):
    pass
