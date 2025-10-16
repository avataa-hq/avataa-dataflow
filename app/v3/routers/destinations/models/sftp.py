from typing import Literal

from pydantic import BaseModel, Field


class SFTPConnectionData(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=0)


class SFTPDestinationModel(BaseModel):
    name: str = Field(min_length=1)
    con_type: Literal["SFTP"] = Field(default="SFTP")
    con_data: SFTPConnectionData
