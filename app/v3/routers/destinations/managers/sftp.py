import pysftp
from paramiko.ssh_exception import SSHException, AuthenticationException
from pysftp.exceptions import ConnectionException

from v3.routers.destinations.managers.base import ABCManager
from v3.routers.sources.utils.exceptions import (
    ValidationError,
    SourceConnectionError,
)


class SFTPManager(ABCManager):
    def __init__(self, con_data: dict):
        # connection config
        self.host = con_data.get("host", None)
        self.port = con_data.get("port", None)
        self.user = con_data.get("login", None)
        self.password = con_data.get("password", None)

        # remote file config
        self.path = con_data.get("path")

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        if isinstance(value, str):
            self._host = value
        else:
            raise ValidationError("Host value must be string!")

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        if isinstance(value, int):
            self._port = value
        else:
            raise ValidationError("Port value must be integer!")

    def __connection_data_dict(self):
        conn_data = dict()
        if self._host:
            conn_data["host"] = self._host

        if self.user:
            conn_data["username"] = self.user

        if self.password:
            conn_data["password"] = self.password

        if self.port:
            conn_data["port"] = self.port

        if self.path:
            conn_data["default_path"] = self.path

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        conn_data["cnopts"] = cnopts

        return conn_data

    def check_connection(self):
        """
        Raises error if the connection failed.
        :raises SourceConnectionError: Connection failed!
        """
        try:
            with pysftp.Connection(**self.__connection_data_dict()):
                pass
        except (
            ConnectionException,
            SSHException,
            AuthenticationException,
        ) as exc:
            raise SourceConnectionError(str(exc))

    def listdir(self):
        with pysftp.Connection(**self.__connection_data_dict()) as connection:
            results = connection.listdir(self.path)
        return results
