from typing import List

from requests.auth import AuthBase


class HTTPAPIkeyAuth(AuthBase):
    """Attaches HTTP APIkey Authentication to a given Request object."""

    def __init__(self, key_name, key_value):
        self.key_name = key_name
        self.key_value = key_value

    def __call__(self, r):
        r.headers[self.key_name] = self.key_value
        return r


class HTTPMultiAPIkeysAuth(AuthBase):
    """Attaches HTTP Multiple API keys Authentication to a given Request object."""

    def __init__(self, api_keys: List[dict]):
        self.api_keys = api_keys

    def __call__(self, r):
        for item in self.api_keys:
            for k, v in item.items():
                r.headers[k] = v
        return r


class HTTPTokenAuth(AuthBase):
    """Attaches HTTP Multiple API keys Authentication to a given Request object."""

    def __init__(self, token: str):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f"Bearer {self.token}"
        return r
