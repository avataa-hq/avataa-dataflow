import requests
from requests.auth import AuthBase


class AllowedRESTMethods:
    POST = "post"
    GET = "get"


class RequestBuilder:
    def __init__(
        self,
        method: str,
        query_params: dict = None,
        body_params: dict = None,
        auth: AuthBase = None,
    ):
        self.method = method
        self.get_params = query_params
        self.body_params = body_params
        self.auth = auth

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, value):
        if not isinstance(value, str):
            raise TypeError("method must be instance of str!")
        allowed_methods = ["post", "get"]
        value = value.lower()
        if value in allowed_methods:
            self._method = value
        else:
            raise ValueError(
                f"method mus be equal to one of the values: {allowed_methods}!"
            )

    @property
    def auth(self):
        return self._auth

    @auth.setter
    def auth(self, value):
        if not isinstance(value, AuthBase):
            raise TypeError("auth must be instance of AuthBase!")
        self._auth = value

    def get_response(self):
        response = getattr(requests, self.method)
        configs = dict()
        if self.query_params:
            configs["json"] = self.query_params
        if self.body_params:
            configs["data"] = self.body_params
        if self.auth:
            configs["auth"] = self.auth
        return response(**configs)
