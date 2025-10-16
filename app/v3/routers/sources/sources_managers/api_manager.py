import io

import pandas as pd
import requests
from oauthlib.oauth2 import LegacyApplicationClient
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from v3.grpc_config.dataflow_to_dataview.proto.data_carrier_pb2 import (
    DataRequest,
)
from v3.routers.sources.sources_managers.api_manager_utils.custom_authentications import (
    HTTPTokenAuth,
    HTTPAPIkeyAuth,
    HTTPMultiAPIkeysAuth,
)
from v3.routers.sources.sources_managers.file_manager_utils.utils import (
    get_csv_delimiter_by_one_line,
)
from v3.routers.sources.sources_managers.general import ABCSourceManager
from requests_oauthlib import OAuth2Session
from v3.routers.sources.models.api_model import (
    APIAuthType,
    validate_restapi_auth_data_depending_on_auth_type,
)
from v3.routers.sources.sources_managers.api_manager_utils.utils import (
    RESTAPIResponseTypes,
    get_file_reader_by_ext,
)
from requests import Response
import re

from v3.routers.sources.utils.exceptions import (
    ValidationError,
    SourceConnectionError,
)


class APISourceManager(ABCSourceManager):
    def __init__(self, con_data: dict):
        self.entry_point = con_data.get("entry_point", None)
        self.end_point = con_data.get("end_point", None)
        self.method = con_data.get("method", "get")
        self.query_params = con_data.get("query_params", None)
        self.body_params = con_data.get("body_params", None)
        self.auth_type = con_data.get("auth_type", None)
        self.auth_data = con_data.get("auth_data", None)
        self.obj_name_to_load_from_response = con_data.get(
            "obj_name_from_resp", None
        )
        self.source_data_columns = con_data.get("source_data_columns")

    def get_columns_with_types(self) -> dict[str, str]:
        raise NotImplementedError

    @staticmethod
    def __clear_auth_type(auth_type):
        """Returns cleared auth_type if auth_type in RestAPIAuthType values,
        otherwise raises ValueError"""
        auth_types = [x.value for x in list(APIAuthType)]
        if auth_type not in auth_types:
            raise ValidationError(
                f"Source.auth_type must be one of {auth_types}"
            )
        return auth_type

    @property
    def auth_type(self):
        return self._auth_type

    @auth_type.setter
    def auth_type(self, value):
        self._auth_type = self.__clear_auth_type(value)

    @property
    def auth_data(self):
        return self._auth_data

    @auth_data.setter
    def auth_data(self, auth_data):
        validate_restapi_auth_data_depending_on_auth_type(
            auth_data=auth_data, auth_type=self.auth_type
        )
        self._auth_data = auth_data

    @property
    def obj_name_to_load_from_response(self):
        return self._obj_name_to_load_from_response

    @obj_name_to_load_from_response.setter
    def obj_name_to_load_from_response(self, value):
        if value is not None and isinstance(value, str) is False:
            raise ValidationError(
                "APISourceManager.obj_name_to_load_from_response must be None or str type"
            )
        self._obj_name_to_load_from_response = value

    @property
    def source_data_columns(self):
        return self._source_data_columns

    @source_data_columns.setter
    def source_data_columns(self, value):
        if value is not None and isinstance(value, list) is False:
            raise ValidationError(
                "APISourceManager.source_data_columns must be None or list type"
            )
        self._source_data_columns = value

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, value):
        if not isinstance(value, str):
            value = str(value)
        allowed_methods = ["post", "get"]
        value = value.lower()
        if value in allowed_methods:
            self._method = value
        else:
            raise ValidationError(
                f"method mus be equal to one of the values: {allowed_methods}!"
            )

    @property
    def query_params(self):
        return self._query_params

    @query_params.setter
    def query_params(self, value):
        if isinstance(value, dict) or value is None:
            self._query_params = value
        else:
            raise ValidationError(
                "query_params must be None or be instance of dict"
            )

    @property
    def body_params(self):
        return self._body_params

    @body_params.setter
    def body_params(self, value):
        if isinstance(value, dict) or value is None:
            self._body_params = value
        else:
            raise ValidationError(
                "body_params must be None or be instance of dict"
            )

    def __get_connection_by_auth_type(self):
        config_data = dict()
        if self.query_params:
            config_data["json"] = self.query_params
        if self.body_params:
            config_data["data"] = self.body_params

        def get_resp_for_no_auth():
            request = getattr(requests, self.method)
            return request(self.end_point, **config_data)

        def get_resp_for_api_key_auth():
            request = getattr(requests, self.method)
            auth = HTTPAPIkeyAuth(
                key_name=self.auth_data["key_name"],
                key_value=self.auth_data["key_value"],
            )
            return request(self.end_point, auth=auth, **config_data)

        def get_resp_for_multi_api_key_auth():
            request = getattr(requests, self.method)
            auth = HTTPMultiAPIkeysAuth(api_keys=self.auth_data["api_keys"])
            return request(self.end_point, auth=auth, **config_data)

        def get_resp_for_basic_auth():
            request = getattr(requests, self.method)
            auth = HTTPBasicAuth(
                username=self.auth_data["username"],
                password=self.auth_data["password"],
            )
            return request(self.end_point, auth=auth, **config_data)

        def get_resp_for_digest_auth():
            request = getattr(requests, self.method)
            auth = HTTPDigestAuth(
                username=self.auth_data["username"],
                password=self.auth_data["password"],
            )
            return request(self.end_point, auth=auth, **config_data)

        def get_resp_for_token_auth():
            request = getattr(requests, self.method)
            auth = HTTPTokenAuth(token=self.auth_data["token"])
            return request(self.end_point, auth=auth, **config_data)

        def get_resp_for_openid_auth():
            data_for_session = dict()
            data_for_get_token = dict()

            client_id = self.auth_data.get("client_id")
            if client_id:
                data_for_session["client_id"] = client_id
                data_for_get_token["client_id"] = client_id

            scope = self.auth_data.get("scope")
            if scope:
                data_for_session["scope"] = scope

            client_secret = self.auth_data.get("client_secret")
            if client_secret:
                data_for_get_token["client_secret"] = client_secret

            username = self.auth_data.get("username")
            if username:
                data_for_get_token["username"] = username

            password = self.auth_data.get("password")
            if password:
                data_for_get_token["password"] = password

            data_for_get_token["token_url"] = self.auth_data.get("token_url")

            oauth = OAuth2Session(
                client=LegacyApplicationClient(**data_for_session)
            )
            oauth.fetch_token(**data_for_get_token)
            return oauth.get(self.end_point, **config_data)

        data = {
            APIAuthType.NOAUTH.value: get_resp_for_no_auth,
            APIAuthType.APIKEY.value: get_resp_for_api_key_auth,
            APIAuthType.MULTIAPIKEY.value: get_resp_for_multi_api_key_auth,
            APIAuthType.BASIC.value: get_resp_for_basic_auth,
            APIAuthType.DIGEST.value: get_resp_for_digest_auth,
            APIAuthType.TOKEN.value: get_resp_for_token_auth,
            APIAuthType.OPENID.value: get_resp_for_openid_auth,
        }
        return data.get(self.auth_type, None)

    def __get_response(self):
        """Return response instance if there are connection function otherwise raises error."""
        connection_func = self.__get_connection_by_auth_type()
        res = connection_func()
        if res is None:
            raise NotImplementedError(
                f"No connection function for con_type: {self.auth_type}"
            )
        return res

    def check_connection(self):
        """Returns True if connection is successful or raises error."""
        res = self.__get_response()
        if res.status_code == 401:
            raise SourceConnectionError("Authentication failed!")

        if not res.status_code == 200:
            raise SourceConnectionError(
                f"Service responded with error ({res.status_code})!"
            )

    def get_response_type(self, res_data: Response = None):
        if res_data is None:
            res_data = self.__get_response()

        content_disposition = res_data.headers.get("content-disposition")
        if content_disposition and content_disposition.startswith("attachment"):
            return RESTAPIResponseTypes.FILE.value

        json_data = res_data.json()
        if isinstance(json_data, dict):
            return RESTAPIResponseTypes.OBJECT.value

        elif isinstance(json_data, list):
            first_obj = json_data[0]
            if isinstance(first_obj, dict):
                return RESTAPIResponseTypes.LIST_OF_OBJECTS.value
            return RESTAPIResponseTypes.LIST_OF_VALUES.value
        else:
            raise NotImplementedError(
                f"Not implemented parser for response type = {type(json_data)}"
            )

    def get_pandas_data_frame_based_on_response(
        self, response: Response = None
    ):
        """Returns pandas DataFrame based on response data."""
        if response is None:
            response = self.__get_response()

        res_type = self.get_response_type(response)
        match res_type:
            case RESTAPIResponseTypes.LIST_OF_VALUES.value:
                df = pd.DataFrame(response.json())
            case RESTAPIResponseTypes.LIST_OF_OBJECTS.value:
                df = pd.DataFrame(response.json())
            case RESTAPIResponseTypes.OBJECT.value:
                df = pd.DataFrame([response.json()])
            case RESTAPIResponseTypes.FILE.value:
                content_disposition = response.headers.get(
                    "content-disposition"
                )
                file_name = re.findall('filename="(.+)"', content_disposition)[
                    0
                ]
                file_ext = file_name.split(".")[-1]
                file_reader = get_file_reader_by_ext(file_ext)
                with io.BytesIO(response.content) as file_data:
                    additional_data = {}
                    if file_reader == pd.read_csv:
                        additional_data = dict(
                            delimiter=get_csv_delimiter_by_one_line(
                                file_data.readline()
                            )
                        )
                        file_data.seek(0)

                    df = file_reader(file_data, **additional_data)
            case _:
                raise NotImplementedError(
                    f"Not implemented parser for response type = {res_type}"
                )
        return df

    def get_source_data_columns(self):
        """Returns columns for data from current source."""
        result = list(self.get_pandas_data_frame_based_on_response().columns)
        return result

    def get_cleaned_columns(self):
        """Returns cleaned columns if self.file_columns is not None, otherwise return all columns"""
        if self.source_data_columns is None:
            return self.get_source_data_columns()
        else:
            set_of_columns_from_db = self.get_source_data_columns()
            return [
                x
                for x in self.source_data_columns
                if x in set_of_columns_from_db
            ]

    def get_source_all_data(self):
        """Returns pandas DataFrame with only specified columns in self.source_data_columns"""

        df = self.get_pandas_data_frame_based_on_response()
        columns = self.get_cleaned_columns()
        print(df)
        return df[columns]

    def get_source_data_for_grpc(self, source_id: int):
        """Returns generator of data converted in grpc message DataRequest"""
        df = self.get_source_all_data()
        count = df.shape[0]

        for _, row in df.iterrows():
            data_row = {k: str(v) for k, v in dict(row).items() if v}
            yield DataRequest(
                source_id=source_id, count=count, data_row=data_row
            )
