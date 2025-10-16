from minio import Minio


from airflow_functions.airflow_source_managers.config import (
    MINIO_URL,
    MINIO_USER,
    MINIO_PASSWORD,
    MINIO_SECURE,
)


class MinioClient:
    def __init__(
        self, url: str, user: str, password: str, secure: bool = False
    ):
        self._url = url
        self._user = user
        self._password = password
        self._secure = secure
        self._minio_client = None

    def __call__(self):
        if self._minio_client is None:
            self.init_bucket()
        return self._minio_client

    def init_bucket(self):
        self._minio_client = Minio(
            self._url, self._user, self._password, secure=self._secure
        )


minio_client = MinioClient(
    url=MINIO_URL, user=MINIO_USER, password=MINIO_PASSWORD, secure=MINIO_SECURE
)
