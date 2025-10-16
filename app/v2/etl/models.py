from enum import Enum

from pydantic import BaseModel, validator, Field


class DB(BaseModel):
    driver: str | None = Field(min_length=1)
    db_name: str | None = Field(alias="dbName", min_length=1)
    host: str | None = Field(min_length=1)
    port: int | str | None
    user: str | None = Field(min_length=1)
    password: str | None = Field(min_length=1)
    table: str | None = Field(min_length=1)

    def get_link(self):
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"

    @validator("port")
    def check_port(cls, port):
        if port:
            raise ValueError("Port must be defined!")

        port = int(port)
        if port <= 0:
            raise ValueError("Port must be greater than 0")

        return str(port)


class AuthType(Enum):
    CREDENTIALS = "credentials"
    TOKEN = "token"  # noqa
    CLIENT = "client"


class Authentication(BaseModel):
    user: str | None = Field(min_length=1)
    password: str | None = Field(min_length=1)
    token: str | None = Field(min_length=1)
    client_id: str | None = Field(min_length=1, alias="clientId")
    client_secret: str | None = Field(min_length=1, alias="clientSecret")


class API(BaseModel):
    entry_point: str = Field(min_length=1, alias="entryPoint")
    end_point: str = Field(min_length=1, alias="endPoint")
    method: str = Field(min_length=1)
    openapi_url: str = Field(min_length=1, alias="openapiUrl")
    path_parameters: dict = Field(alias="pathParameters")
    query_parameters: dict = Field(alias="queryParameters")
    body_parameters: dict = Field(alias="bodyParameters")
    authentication: Authentication

    @validator("method")
    def check_method(cls, method):
        if method.upper() not in ["GET", "POST"]:
            raise ValueError(f"Method {method} forbidden!")
        return method.upper()


class SFTPConnection(BaseModel):
    host: str | None
    port: str | int | None
    login: str | None
    password: str | None
    file_path: str | None = Field(alias="filePath")


class File(BaseModel):
    content: str
    file_type: str = Field(
        alias="fileType", description="File's extension (json, csv, xlsx)"
    )


class Condition(BaseModel):
    field: str
    operation: str
    value: str | int | float


class Join(BaseModel):
    join_rule: str = Field(alias="joinRule", min_length=1)
    target_columns: dict[str, list[str]] = Field(
        alias="targetColumns", min_items=1
    )
    join_columns: dict[str, list[str]] = Field(alias="joinColumns", min_items=1)
    conditions: dict[str, list[Condition]] | None

    @validator("join_rule")
    def check_join_rule(cls, join_rule):
        rules = ["inner", "outer", "left", "right"]

        join_rule = join_rule.strip().lower()
        if join_rule in rules:
            return join_rule

        raise ValueError("Wrong join rule!")

    def as_dict(self):
        obj = self.copy()
        obj.conditions = {
            key: [v.__dict__ for v in value]
            for key, value in self.conditions.items()
        }
        return obj
