"""RESTAPI Source validation models"""

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, validator, AnyUrl

from airflow_functions.airflow_source_managers.routers.sources.models.general_model import (
    SourceType,
    SourceModelBaseInfo,
    SourceModelBaseCreate,
    SourceConDataBaseModel,
)


class ApiMethods(Enum):
    POST = "post"
    GET = "get"


class APIAuthType(Enum):
    NOAUTH = "No authentication"
    APIKEY = "APIKey"
    MULTIAPIKEY = "MultiAPIkeys"
    BASIC = "Basic Authentication"
    DIGEST = "Digest Authentication"
    TOKEN = "Token"  # noqa
    OPENID = "OpenID"


class APIBaseAuthModel(BaseModel):
    username: str = Field(...)
    password: str = Field(...)


class APITokenAuthModel(BaseModel):
    token: str = Field(...)


class APIKeyAuthModel(BaseModel):
    key_name: str = Field(...)
    key_value: str = Field(...)


class APIMultiKeyModel(BaseModel):
    api_keys: List[APIKeyAuthModel] = Field(...)


class APIOpenIDAuthModel(BaseModel):
    client_id: str = Field(...)  # required
    client_secret: Optional[str]
    token_url: AnyUrl = Field(...)  # required
    refresh_token_url: Optional[AnyUrl]
    scope: Optional[List[str]]
    username: Optional[str]
    password: Optional[str]


def validate_restapi_auth_data_depending_on_auth_type(auth_type, auth_data):
    if auth_type == APIAuthType.APIKEY.value:
        APITokenAuthModel.validate(auth_data)
    elif auth_type == APIAuthType.MULTIAPIKEY.value:
        APIMultiKeyModel.validate(auth_data)
    elif auth_type == APIAuthType.BASIC.value:
        APIBaseAuthModel.validate(auth_data)
    elif auth_type == APIAuthType.DIGEST.value:
        APIBaseAuthModel.validate(auth_data)
    elif auth_type == APIAuthType.TOKEN.value:
        APITokenAuthModel.validate(auth_data)
    elif auth_type == APIAuthType.OPENID.value:
        APIOpenIDAuthModel.validate(auth_data)
    elif auth_type == APIAuthType.NOAUTH.value:
        pass
    else:
        raise NotImplementedError(f"{auth_type} not implemented!.")


class APIConnectionBaseModel(BaseModel):
    end_point: str = Field(min_length=1)
    method: Optional[ApiMethods] = Field(default=ApiMethods.GET.value)
    query_params: Optional[dict]
    body_params: Optional[dict]
    auth_type: APIAuthType = Field(...)
    auth_data: dict = Field(...)

    class Config:
        use_enum_values = True


class APIConnectionModel(SourceConDataBaseModel, APIConnectionBaseModel):
    class Config:
        use_enum_values = True

    @validator("auth_data")
    def check_auth_data_depending_on_auth_type(cls, auth_data, values):
        auth_type = values.get("auth_type")

        validate_restapi_auth_data_depending_on_auth_type(
            auth_type=auth_type, auth_data=auth_data
        )

        return auth_data


class APIConnectionConfig(BaseModel):
    entry_point: str = Field(min_length=1)
    url_to_open_api_json: AnyUrl = Field(...)


class APIModelBase(BaseModel):
    con_type: Optional[str] = Field(
        default=SourceType.RESTAPI.value, regex=rf"^{SourceType.RESTAPI.value}$"
    )
    # con_config: APIConnectionConfig
    con_data: APIConnectionModel = Field(...)

    class Config:
        use_enum_values = True


class APIModelInfo(APIModelBase, SourceModelBaseInfo):
    pass


class APIModelCreate(APIModelBase, SourceModelBaseCreate):
    pass


AUTH_TYPE_MODEL_DICT = {
    APIAuthType.NOAUTH.value: BaseModel,
    APIAuthType.APIKEY.value: APIKeyAuthModel,
    APIAuthType.MULTIAPIKEY.value: APIMultiKeyModel,
    APIAuthType.BASIC.value: APIBaseAuthModel,
    APIAuthType.DIGEST.value: APIBaseAuthModel,
    APIAuthType.TOKEN.value: APITokenAuthModel,
    APIAuthType.OPENID.value: APIOpenIDAuthModel,
}
