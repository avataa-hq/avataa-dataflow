import pickle

import minio
import pysftp
from minio import Minio
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session

from airflow_functions.airflow_source_managers.config import (
    MINIO_BUCKET,
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASS,
    DB_NAME,
)
from airflow_functions.airflow_source_managers.routers.sources.models.file_model import (
    FileExtension,
)
from airflow_functions.airflow_source_managers.routers.sources.sources_managers.file_manager_utils.utils import (
    get_csv_delimiter_by_one_line,
)
from airflow_functions.airflow_source_managers.routers.sources.sources_managers.general import (
    ABCSourceManager,
)
import pandas as pd

PANDAS_FILE_READER = {
    FileExtension.CSV.value: pd.read_csv,
    FileExtension.EXCEL.value: pd.read_excel,
    FileExtension.OlD_EXCEL.value: pd.read_excel,
}


def get_pandas_file_reader(file_name: str):
    """Returns padnas file reader function instance if file there are implemented readers, otherwise
    raises error"""
    file_ext = file_name.split(".")[-1]
    pd_file_reader = PANDAS_FILE_READER.get(file_ext, None)
    if pd_file_reader is None:
        raise TypeError(
            f"There are no implemented file reader for extension '.{file_ext}'."
        )
    return pd_file_reader


class SFTPSourceManager(ABCSourceManager):
    def __init__(self, con_data: dict):
        self.host = con_data.get("host", None)
        self.port = con_data.get("port", None)
        self.user = con_data.get("login", None)
        self.password = con_data.get("password", None)
        self.file_path = con_data.get("file_path", "/")
        self.file_name = con_data.get("file_name", None)
        self.source_data_columns = con_data.get("source_data_columns")

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        if isinstance(value, str):
            self._host = value
        else:
            raise ValueError("Host value must be string")

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        if isinstance(value, int):
            self._port = value
        else:
            raise ValueError("Port value must be integer")

    @property
    def file_name(self):
        return self._file_name

    @file_name.setter
    def file_name(self, value):
        if value:
            extensions = [item.value for item in FileExtension]
            file_ext = value.split(".")[-1]
            if file_ext not in extensions:
                raise ValueError(
                    f"Wrong file extension - '.{file_ext}'. Supported extensions are: {extensions}"
                )
            self._file_name = value
        else:
            raise ValueError("con_data must have file_name value")

    @property
    def source_data_columns(self):
        return self._source_data_columns

    @source_data_columns.setter
    def source_data_columns(self, value):
        if value is not None and isinstance(value, list) is False:
            raise ValueError(
                "ManualFileSourceManager.source_data_columns must be list type"
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
        """Raises error if the connection failed."""
        with pysftp.Connection(**self.__connection_data_dict()):
            pass

    def get_list_of_files_and_dirs(self):
        with pysftp.Connection(**self.__connection_data_dict()) as connection:
            results = connection.listdir()
        return results

    def get_source_data_columns(self):
        self.check_connection()

        with pysftp.Connection(**self.__connection_data_dict()) as connection:
            with connection.open(self.file_name) as file:
                pandas_file_reader = get_pandas_file_reader(self.file_name)

                additional_data = {}
                if pandas_file_reader == pd.read_csv:
                    additional_data = dict(
                        delimiter=get_csv_delimiter_by_one_line(file.readline())
                    )
                    file.seek(0)

                df = pandas_file_reader(file, **additional_data)
                source_columns = list(df.columns)
        return source_columns

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
        with pysftp.Connection(**self.__connection_data_dict()) as connection:
            with connection.open(self.file_name) as file:
                pandas_file_reader = get_pandas_file_reader(self.file_name)
                additional_data = {}
                if pandas_file_reader == pd.read_csv:
                    additional_data = dict(
                        delimiter=get_csv_delimiter_by_one_line(file.readline())
                    )
                    file.seek(0)

                df = pandas_file_reader(
                    file,
                    dtype=str,
                    usecols=self.get_cleaned_columns(),
                    **additional_data,
                )
        return df

    # def get_source_data_for_grpc(self, source_id: int):
    #     """Returns generator of data converted in grpc message DataRequest"""
    #     df = self.get_source_all_data()
    #     count = df.shape[0]
    #
    #     for index, row in df.iterrows():
    #         data_row = dict(row)
    #         yield DataRequest(source_id=source_id,
    #                           count=count,
    #                           data_row=data_row)

    def save_source_data_into_database(
        self,
        create_db_task_id: str,
        db_driver="postgresql",
        db_host=DB_HOST,
        db_port=DB_PORT,
        db_user=DB_USER,
        db_pass=DB_PASS,
        db_name=DB_NAME,
        **kwargs,
    ):
        """Returns save data into particular db"""

        table_name = kwargs["ti"].xcom_pull(task_ids=create_db_task_id)
        DATABASE_URL = (
            f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        )
        engine = create_engine(
            DATABASE_URL, echo=False, pool_size=20, max_overflow=100
        )

        Base = declarative_base(bind=engine)

        class Data(Base):
            __tablename__ = table_name
            id: int = Column("id", Integer, primary_key=True)
            data: str = Column("data", String)

        Base.metadata.create_all()
        df = self.get_source_all_data()

        with Session(engine) as session:
            [
                session.add(Data(data=pickle.dumps(item.to_dict()).hex()))
                for _, item in df.iterrows()
            ]

            session.commit()


class ManualFileSourceManager(ABCSourceManager):
    def __init__(
        self, source_id: int, con_data: dict, client: Minio, *args, **kwargs
    ):
        self.source_id = source_id
        self.file_name = con_data.get("file_name")
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
            raise ValueError(
                f"Wrong file extension - '.{file_ext}'. Supported extensions are: {extensions}"
            )
        self._file_name = value

    @property
    def source_data_columns(self):
        return self._source_data_columns

    @source_data_columns.setter
    def source_data_columns(self, value):
        if value is not None and isinstance(value, list) is False:
            raise ValueError(
                "ManualFileSourceManager.source_data_columns must be list type"
            )
        self._source_data_columns = value

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value):
        if isinstance(value, Minio) is False:
            raise ValueError(
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
                raise ValueError(
                    f"The file named '{self.file_name}' does not exist!"
                )
        finally:
            res.close()

    def get_source_data_columns(self):
        """Returns list of all file columns"""
        try:
            response = self.client.get_object(
                bucket_name=MINIO_BUCKET,
                object_name=f"{self.source_id}/{self.file_name}",
            )
            pandas_file_reader = get_pandas_file_reader(self.file_name)

            additional_data = {}
            if pandas_file_reader == pd.read_csv:
                additional_data = dict(
                    delimiter=get_csv_delimiter_by_one_line(response.readline())
                )
                response = self.client.get_object(
                    bucket_name=MINIO_BUCKET,
                    object_name=f"{self.source_id}/{self.file_name}",
                )
            columns = list(
                pandas_file_reader(response, **additional_data).columns
            )

        except minio.error.S3Error as e:
            if e.code == "NoSuchKey":
                raise ValueError(
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
                raise ValueError(str(e))

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
            if pandas_file_reader == pd.read_csv:
                additional_data = dict(
                    delimiter=get_csv_delimiter_by_one_line(response.readline())
                )
                response = self.client.get_object(
                    bucket_name=MINIO_BUCKET,
                    object_name=f"{self.source_id}/{self.file_name}",
                )

            df = pandas_file_reader(
                response,
                dtype=str,
                usecols=self.get_cleaned_columns(),
                **additional_data,
            )
        finally:
            response.close()
        return df

    # def get_source_data_for_grpc(self, source_id: int):
    #     """Returns generator of data converted in grpc message DataRequest"""
    #     df = self.get_source_all_data()
    #     count = df.shape[0]
    #     for index, row in df.iterrows():
    #         data_row = {k: str(v) for k, v in dict(row).items() if v}
    #         yield DataRequest(source_id=source_id,
    #                           count=count,
    #                           data_row=data_row)

    def save_source_data_into_database(
        self,
        create_db_task_id: str,
        db_driver="postgresql",
        db_host=DB_HOST,
        db_port=DB_PORT,
        db_user=DB_USER,
        db_pass=DB_PASS,
        db_name=DB_NAME,
        **kwargs,
    ):
        """Returns save data into particular db"""

        table_name = kwargs["ti"].xcom_pull(task_ids=create_db_task_id)
        DATABASE_URL = (
            f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        )
        engine = create_engine(
            DATABASE_URL, echo=False, pool_size=20, max_overflow=100
        )

        Base = declarative_base(bind=engine)

        class Data(Base):
            __tablename__ = table_name
            id: int = Column("id", Integer, primary_key=True)
            data: str = Column("data", String)

        Base.metadata.create_all()
        df = self.get_source_all_data()

        with Session(engine) as session:
            [
                session.add(Data(data=pickle.dumps(item.to_dict()).hex()))
                for _, item in df.iterrows()
            ]

            session.commit()
