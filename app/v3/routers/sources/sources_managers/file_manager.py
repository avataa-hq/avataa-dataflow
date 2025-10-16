import copy
import csv
import datetime
import ftplib
import io
import os
import re

import minio
import numpy as np
import pysftp
from ftputil import FTPHost
from ftputil.error import FTPError
from ftputil.session import session_factory
from minio import Minio
from dateutil.parser import ParserError
from pandas._libs import OutOfBoundsDatetime
from paramiko.sftp_file import SFTPFile
from paramiko.ssh_exception import SSHException, AuthenticationException
from pysftp.exceptions import ConnectionException

from v3.config import MINIO_BUCKET
from v3.grpc_config.dataflow_to_dataview.proto.data_carrier_pb2 import (
    DataRequest,
)
from v3.routers.sources.models.file_model import FileExtension, DatePatternType
from v3.routers.sources.sources_managers.file_manager_utils.file_validator import (
    FileValidator,
)
from v3.routers.sources.sources_managers.file_manager_utils.handlers import (
    FileHandler,
)
from v3.routers.sources.sources_managers.file_manager_utils.utils import (
    get_csv_delimiter_by_one_line,
)
from v3.routers.sources.sources_managers.general import ABCSourceManager
import pandas as pd

from v3.routers.sources.utils.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    InternalError,
    SourceConnectionError,
)

PANDAS_FILE_READER = {
    FileExtension.CSV.value: pd.read_csv,
    FileExtension.EXCEL.value: pd.read_excel,
    FileExtension.OlD_EXCEL.value: pd.read_excel,
}

DATE_PATTERN_FORMAT = {
    DatePatternType.DMY: "%d%m%Y",
    DatePatternType.MDY: "%m%d%Y",
    DatePatternType.YMD: "%Y%m%d",
}


def get_pandas_file_reader(file_name: str):
    """Returns padnas file reader function instance if file there are implemented readers, otherwise
    raises error"""
    file_ext = file_name.split(".")[-1]
    pd_file_reader = PANDAS_FILE_READER.get(file_ext, None)
    if pd_file_reader is None:
        raise ValidationError(
            f"There are no implemented file reader for extension '.{file_ext}'."
        )
    return pd_file_reader


def get_csv_delimiter(file_data: bytes):
    """Returns csv delimiter"""
    with io.StringIO(file_data.decode("utf-8")) as data:
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(data.readline()).delimiter
    return delimiter


class SFTPSourceManager(ABCSourceManager):
    def __init__(self, con_data: dict):
        # connection config
        self.host = con_data.get("host", None)
        self.port = con_data.get("port", None)
        self.user = con_data.get("login", None)
        self.password = con_data.get("password", None)

        # remote file config
        file_info = con_data.get("file")
        self.file_path = file_info.get("file_path", "/")
        self.file_name = file_info.get("file_name", None)
        self.date_pattern = file_info.get("date_pattern", None)
        self.offset = file_info.get("offset", None)

        self.source_data_columns = con_data.get("source_data_columns")
        self.file = None
        self.handler: FileHandler | None = None

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

    @property
    def file_name(self):
        if self.date_pattern:
            file_date = datetime.date.today() - datetime.timedelta(
                days=self.offset
            )
            file_date = file_date.strftime(
                DATE_PATTERN_FORMAT[self.date_pattern]
            )
            return self._file_name.replace(self.date_pattern, file_date)
        return self._file_name

    @file_name.setter
    def file_name(self, value):
        if value:
            extensions = [item.value for item in FileExtension]
            file_ext = value.split(".")[-1]
            if file_ext not in extensions:
                raise ValidationError(
                    f"Wrong file extension - '.{file_ext}'. Supported extensions are: {extensions}"
                )
            self._file_name = value
        else:
            raise ValidationError("con_data must have file_name value")

    @property
    def source_data_columns(self):
        return self._source_data_columns

    @source_data_columns.setter
    def source_data_columns(self, value):
        if value is not None and isinstance(value, list) is False:
            raise InternalError(
                "SFTPSourceManager.source_data_columns must be list type"
            )
        self._source_data_columns = value

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

        if self.file_path:
            conn_data["default_path"] = self.file_path

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

    def get_list_of_files_and_dirs(self):
        with pysftp.Connection(**self.__connection_data_dict()) as connection:
            results = connection.listdir()
        return results

    def get_source_data_columns(self):
        self.get_file()
        df = self.handler.parse_header()
        source_columns = list(df.columns)

        return source_columns

    def get_columns_with_types(self) -> dict[str, str]:
        self.get_file()
        df = self.handler.parse()
        columns = list(df.columns)
        result = {}

        for column in columns:
            dtype = str(df[column].dtype).lower()
            if dtype.__contains__("int"):
                result[column] = "int"
            elif dtype.__contains__("float"):
                result[column] = "float"
            elif dtype.__contains__("bool"):
                result[column] = "bool"
            else:
                try:
                    pd.to_datetime(df[column])
                    result[column] = "datetime"
                except TypeError:
                    result[column] = "str"
                except ParserError:
                    result[column] = "str"
                except OutOfBoundsDatetime:
                    result[column] = "str"

        if self.source_data_columns:
            for col in set(result.keys()).difference(self.source_data_columns):
                result.pop(col)

        # check reserved names
        if "tmo_id" in result.keys():
            result["tmo_id"] = "int"
        if "parent_name" in result.keys():
            result["parent_name"] = "str"

        return result

    def get_cleaned_columns(self):
        """Returns cleaned columns if self.source_data_columns is not None, otherwise return all columns"""
        if not self.source_data_columns:
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
        self.get_file()
        df = self.handler.parse()

        if self.source_data_columns:
            df = df[self.source_data_columns]
        df.replace(np.nan, None, inplace=True)

        return df

    def get_source_data_for_grpc(self, source_id: int):
        """Returns generator of data converted in grpc message DataRequest"""
        df = self.get_source_all_data()
        count = df.shape[0]

        for index, row in df.iterrows():
            data_row = dict(row)
            data_row = {k: str(v) for k, v in data_row.items() if pd.notna(v)}
            yield DataRequest(
                source_id=source_id, count=count, data_row=data_row
            )

    def get_file(self) -> SFTPFile | io.StringIO:
        if self.file:
            self.file.seek(0)
            return self.file

        remote_files = self.get_list_of_files_and_dirs()
        file_pattern = self._file_name
        if self.date_pattern:
            file_pattern = file_pattern.replace(self.date_pattern, "[0-9]{8}")
        remote_files = dict.fromkeys(
            [rf for rf in remote_files if re.search(file_pattern, rf)], None
        )

        with pysftp.Connection(**self.__connection_data_dict()) as connection:
            for rf in remote_files.keys():
                stat = connection.stat(rf)
                file_date = datetime.datetime.fromtimestamp(stat.st_mtime)
                remote_files[rf] = file_date
            remote_files = dict(
                sorted(
                    remote_files.items(), key=lambda item: item[1], reverse=True
                )
            )
            remote_file_name = list(remote_files.keys())[0]

        print(remote_file_name)
        with pysftp.Connection(**self.__connection_data_dict()) as connection:
            connection.get(remote_file_name, f"./temp/{self.file_name}")
            self.file = io.StringIO()
            with open(f"./temp/{self.file_name}") as file:
                for line in file.readlines():
                    self.file.write(line)
                self.file.seek(0)
            self.handler = FileValidator(self.file).get_file_handler()
            os.remove(f"./temp/{self.file_name}")

        return self.file


class ManualFileSourceManager(ABCSourceManager):
    def __init__(
        self, source_id: int, con_data: dict, client: Minio, *args, **kwargs
    ):
        self.source_id = source_id
        self.file_name = con_data.get("filename") or con_data.get("file_name")
        self.source_data_columns = con_data.get("source_data_columns")
        self.client = client

    @property
    def source_id(self):
        return self._source_id

    @source_id.setter
    def source_id(self, value):
        if isinstance(value, int) is False:
            raise ValueError(
                "ManualFileSourceManager.source_id must be int type"
            )
        self._source_id = value

    @property
    def file_name(self):
        return self._file_name

    @file_name.setter
    def file_name(self, value):
        extensions = [item.value for item in FileExtension]
        file_ext = value.split(".")[-1]
        if file_ext not in extensions:
            raise ValidationError(
                f"Wrong file extension - '.{file_ext}'. Supported extensions are: {extensions}"
            )
        self._file_name = value

    @property
    def source_data_columns(self):
        return self._source_data_columns

    @source_data_columns.setter
    def source_data_columns(self, value):
        if value is not None and isinstance(value, list) is False:
            raise ValidationError(
                "ManualFileSourceManager.source_data_columns must be list type"
            )
        self._source_data_columns = value

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value):
        if isinstance(value, Minio) is False:
            raise InternalError(
                "ManualFileSourceManager.client must be Minio type"
            )
        self._client = value

    def check_connection(self):
        """Raises error if the connection failed."""
        try:
            res = self.client.get_object(
                bucket_name=MINIO_BUCKET,
                object_name=f"{self.source_id}/{self.file_name}",
                offset=0,
                length=32,
            )

        except minio.error.S3Error as e:
            if e.code == "NoSuchKey":
                raise ResourceNotFoundError(
                    f"The file named '{self.file_name}' does not exist!"
                )
        finally:
            res.close()

    def get_source_data_columns(self) -> list:
        """
        Returns list of all file columns
        :return: list of source columns
        :raises ValidationError: file extension not supported
        """
        try:
            response = self.client.get_object(
                bucket_name=MINIO_BUCKET,
                object_name=f"{self.source_id}/{self.file_name}",
            )
            pandas_file_reader = get_pandas_file_reader(self.file_name)

            additional_data = {}

            # read_excel cannot read urllib3.response.HTTPResponse object,
            # so it should be extracted
            if pandas_file_reader == pd.read_excel:
                file_object = response.data
            else:
                content = io.BytesIO(response.read())
                file_object = copy.deepcopy(content)
                additional_data = dict(
                    delimiter=get_csv_delimiter_by_one_line(content.readline())
                )
                file_object.seek(0)
            df = pandas_file_reader(file_object, **additional_data)

            columns = list(df.columns)

        except minio.error.S3Error as e:
            if e.code == "NoSuchKey":
                raise ResourceNotFoundError(
                    f"The file named '{self.file_name}' does not exist!"
                )
            columns = []
        finally:
            response.close()
        return columns

    def delete_file_from_minio(self):
        """Deletes file from MinIO if file exists, otherwise raises error"""
        try:
            self.client.remove_object(
                bucket_name=MINIO_BUCKET,
                object_name=f"{self.source_id}/{self.file_name}",
            )
        except minio.error.S3Error as e:
            if e.code != "NoSuchKey":
                raise ResourceNotFoundError(str(e))

    def get_cleaned_columns(self):
        """Returns cleaned columns if self.source_data_columns is not None, otherwise return all columns"""
        if not self.source_data_columns:
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
        self.check_connection()
        try:
            response = self.client.get_object(
                bucket_name=MINIO_BUCKET,
                object_name=f"{self.source_id}/{self.file_name}",
            )
            pandas_file_reader = get_pandas_file_reader(self.file_name)
            additional_data = {}

            # read_excel cannot read urllib3.response.HTTPResponse object,
            # so it should be extracted
            if pandas_file_reader == pd.read_excel:
                file_object = response.data
            else:
                content = io.BytesIO(response.read())
                file_object = copy.deepcopy(content)
                additional_data = dict(
                    delimiter=get_csv_delimiter_by_one_line(content.readline())
                )
                file_object.seek(0)

            df = pandas_file_reader(
                file_object,
                dtype=str,
                usecols=self.get_cleaned_columns(),
                **additional_data,
            )

            df.replace(np.nan, None, inplace=True)
        finally:
            response.close()
        return df

    def get_columns_with_types(self) -> dict[str, str]:
        """Returns key-value pairs of all file columns names and types"""
        result = {}
        try:
            response = self.client.get_object(
                bucket_name=MINIO_BUCKET,
                object_name=f"{self.source_id}/{self.file_name}",
            )
            pandas_file_reader = get_pandas_file_reader(self.file_name)

            additional_data = {}

            # read_excel cannot read urllib3.response.HTTPResponse object,
            # so it should be extracted
            if pandas_file_reader == pd.read_excel:
                file_object = response.data
            else:
                content = io.BytesIO(response.read())
                file_object = copy.deepcopy(content)
                additional_data = dict(
                    delimiter=get_csv_delimiter_by_one_line(
                        file_object.readline()
                    )
                )
                file_object.seek(0)

            df = pandas_file_reader(
                file_object, **additional_data
            ).convert_dtypes()

            columns = list(df.columns)
            for column in columns:
                dtype = str(df[column].dtype).lower()
                if dtype.__contains__("int"):
                    result[column] = "int"
                elif dtype.__contains__("float"):
                    result[column] = "float"
                elif dtype.__contains__("bool"):
                    result[column] = "bool"
                else:
                    try:
                        pd.to_datetime(df[column])
                        result[column] = "datetime"
                    except TypeError:
                        result[column] = "str"
                    except ParserError:
                        result[column] = "str"

        except minio.error.S3Error as e:
            if e.code == "NoSuchKey":
                raise ResourceNotFoundError(
                    f"The file named '{self.file_name}' does not exist!"
                )
        finally:
            response.close()

        if self.source_data_columns:
            for col in set(result.keys()).difference(self.source_data_columns):
                result.pop(col)

        # check reserved names
        if "tmo_id" in result.keys():
            result["tmo_id"] = "int"
        if "parent_name" in result.keys():
            result["parent_name"] = "str"

        return result

    def get_source_data_for_grpc(self, source_id: int):
        """Returns generator of data converted in grpc message DataRequest"""
        df = self.get_source_all_data()
        count = df.shape[0]
        for index, row in df.iterrows():
            data_row = {k: str(v) for k, v in dict(row).items() if v}

            yield DataRequest(
                source_id=source_id, count=count, data_row=data_row
            )


class FTPSourceManager(ABCSourceManager):
    def __init__(self, con_data: dict):
        self.host = con_data.get("host", None)
        self.port = con_data.get("port", 21)
        self.user = con_data.get("login", None)
        self.password = con_data.get("password", None)

        # remote file config
        file_info = con_data.get("file")
        self.file_path = file_info.get("file_path", "/")
        self.file_name = file_info.get("file_name", None)
        self.date_pattern = file_info.get("date_pattern", None)
        self.offset = file_info.get("offset", None)

        self.source_data_columns = con_data.get("source_data_columns")
        self.is_connected = False
        self._client: FTPHost | None = None

    @property
    def is_connected(self):
        return self._is_connected

    @is_connected.setter
    def is_connected(self, value):
        if not isinstance(value, bool):
            raise InternalError('"is_connected" value must be boolean!')
        self._is_connected = value

    @property
    def path(self):
        res = self.file_path
        if not self.file_path.endswith("/"):
            res += "/"
        res += self.file_name

        return res

    def _connect(self):
        """
        Creates connection to remote FTP server
        :raises SourceConnectionError: Connection failed!
        """
        if self.is_connected:
            return

        factory = session_factory(
            base_class=ftplib.FTP,
            port=self.port,
            use_passive_mode=True,
            encrypt_data_channel=False,
            encoding=None,
            debug_level=None,
        )

        try:
            self._client = FTPHost(
                self.host, self.user, self.password, session_factory=factory
            )
        except FTPError as exc:
            raise SourceConnectionError(str(exc))

        self.is_connected = True

    def check_connection(self):
        self._connect()

    def _download_file(self) -> io.StringIO:
        remote_file_name = self.path

        # if search by date_pattern -> download last file
        if self.date_pattern:
            remote_files = self.get_list_of_files_and_dirs()
            file_pattern = self.file_name.split(self.date_pattern)[0]
            remote_files = {
                f"{self.file_path}/{rf}": None
                for rf in remote_files
                if rf.__contains__(file_pattern)
            }
            for rf in remote_files.keys():
                remote_files[rf] = self._client.stat(rf).st_mtime
            remote_files = dict(
                sorted(
                    remote_files.items(), key=lambda item: item[1], reverse=True
                )
            )
            remote_file_name = list(remote_files.keys())[0]

        with self._client.open(remote_file_name) as remote_file:
            file = io.StringIO()
            file.write(remote_file.read())
            file.seek(0)

        return file

    def _get_dataframe(self) -> pd.DataFrame:
        file = self._download_file()

        pandas_file_reader = get_pandas_file_reader(self.file_name)

        additional_data = {}
        if pandas_file_reader == pd.read_csv:
            additional_data = dict(
                delimiter=get_csv_delimiter_by_one_line(file.readline())
            )
            file.seek(0)

        df = pandas_file_reader(file, **additional_data)

        return df

    def get_source_data_columns(self):
        self._connect()

        df = self._get_dataframe()
        source_columns = list(df.columns)
        return source_columns

    def get_columns_with_types(self) -> dict[str, str]:
        """Returns key-value pairs of all file columns names and types"""
        self._connect()
        result = {}
        df = self._get_dataframe()

        columns = list(df.columns)
        for column in columns:
            dtype = str(df[column].dtype).lower()
            if dtype.__contains__("int"):
                result[column] = "int"
            elif dtype.__contains__("float"):
                result[column] = "float"
            elif dtype.__contains__("bool"):
                result[column] = "bool"
            else:
                try:
                    pd.to_datetime(df[column])
                    result[column] = "datetime"
                except TypeError:
                    result[column] = "str"
                except ParserError:
                    result[column] = "str"

        if self.source_data_columns:
            for col in set(result.keys()).difference(self.source_data_columns):
                result.pop(col)

        # check reserved names
        if "tmo_id" in result.keys():
            result["tmo_id"] = "int"
        if "parent_name" in result.keys():
            result["parent_name"] = "str"

        return result

    def get_cleaned_columns(self):
        """Returns cleaned columns if self.source_data_columns is not None, otherwise return all columns"""
        if not self.source_data_columns:
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
        self._connect()
        columns = self.get_cleaned_columns()
        df = self._get_dataframe()
        columns_to_drop = set(columns).symmetric_difference(df.columns)
        df.drop(columns=columns_to_drop, axis=1, inplace=True)  # noqa

        return df

    def get_source_data_for_grpc(self, source_id: int):
        """Returns generator of data converted in grpc message DataRequest"""
        df = self.get_source_all_data()
        count = df.shape[0]
        for index, row in df.iterrows():
            data_row = {k: str(v) for k, v in dict(row).items() if v}
            yield DataRequest(
                source_id=source_id, count=count, data_row=data_row
            )

    def get_list_of_files_and_dirs(self):
        self._connect()
        result = self._client.listdir(self.file_path)
        return result
