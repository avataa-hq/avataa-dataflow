from pydantic import BaseModel, Field


class SFTPConnectionModel(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(gt=0)
    login: str = Field(min_length=1)
    password: str = Field(min_length=0)
    path: str = Field(default="/", min_length=1)
