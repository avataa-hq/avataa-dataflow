import datetime

from sqlalchemy import (
    create_engine,
    MetaData,
    select,
    func,
    DATETIME,
    DATE,
    TIMESTAMP,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from v3.grpc_config.dataflow_to_dataview.proto.data_carrier_pb2 import (
    DataRequest,
)
from v3.routers.sources.models.db_model import DBDriverTypes
from v3.routers.sources.sources_managers.general import ABCSourceManager
from v3.routers.sources.utils.exceptions import (
    InternalError,
    ResourceNotFoundError,
    SourceConnectionError,
)

DBConnectionDrivers = {
    DBDriverTypes.POSTGRESQL.value: "postgresql+psycopg2",
    DBDriverTypes.MYSQL.value: "mysql+mysqlconnector",
    DBDriverTypes.ORACLE.value: "oracle+cx_oracle",
}


class DBSourceManager(ABCSourceManager):
    def __init__(self, con_data: dict):
        self.db_type = con_data.get("db_type")
        self.host = con_data.get("host")
        self.port = con_data.get("port")
        self.user = con_data.get("user")
        self.password = con_data.get("password")
        self.db_name = con_data.get("db_name", None)
        self.db_table = con_data.get("db_table", None)
        self.source_data_columns = con_data.get("source_data_columns", None)
        self.date_column = con_data.get("date_column")
        self.offset = con_data.get("offset")

    @property
    def db_type(self):
        return self._db_type

    @db_type.setter
    def db_type(self, value):
        db_types = [x.value for x in list(DBDriverTypes)]
        if value not in db_types:
            raise ValueError(f"Source.db_types must be one of {db_types}")
        self._db_type = value

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        if isinstance(value, str):
            self._host = value
        else:
            raise ValueError("Host value must be str type")

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        if isinstance(value, int):
            self._port = value
        else:
            raise ValueError("Port value must be int type")

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        if isinstance(value, str):
            self._user = value
        else:
            raise ValueError("User value must be str type")

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        if isinstance(value, str):
            self._password = value
        else:
            raise ValueError("User value must be str type")

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

    def __get_engine_by_db_type(self):
        url = f"{DBConnectionDrivers[self._db_type]}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        return create_engine(url)

    def check_connection(self):
        """Raises error if the connection failed."""
        meta_data = MetaData()
        try:
            meta_data.reflect(bind=self.__get_engine_by_db_type())
        except OperationalError as ex:
            raise ValueError(ex.orig.args[0].capitalize())

    def get_all_tables_from_db(self):
        """Returns all db tables"""
        meta_data = MetaData()
        meta_data.reflect(bind=self.__get_engine_by_db_type())
        return list(meta_data.tables.keys())

    def get_source_data_columns(self, only_datetime: bool = False):
        """Returns list of all db table columns"""
        if self.db_table is None:
            raise InternalError("Please set value for db_table attribute")

        meta_data = MetaData()
        try:
            meta_data.reflect(bind=self.__get_engine_by_db_type())
        except OperationalError as exc:
            raise SourceConnectionError(str(exc))

        table = meta_data.tables.get(self.db_table, None)
        if table is None:
            raise ResourceNotFoundError(
                f"Table with name '{self.db_table}' does not exist!"
            )

        if only_datetime:
            columns = [
                col.name
                for col in table.columns
                if any(
                    isinstance(col.type, date_type)
                    for date_type in [DATETIME, DATE, TIMESTAMP]
                )
            ]
        else:
            columns = list(table.columns.keys())

        return columns

    def get_columns_with_types(self) -> dict[str, str]:
        if self.db_table is None:
            raise InternalError("Please set value for db_table attribute")

        meta_data = MetaData()
        meta_data.reflect(bind=self.__get_engine_by_db_type())
        table = meta_data.tables.get(self.db_table, None)
        if table is None:
            raise ResourceNotFoundError(
                f"Table with name '{self.db_table}' does not exist!"
            )

        columns = set(table.columns.keys())
        if (
            self.source_data_columns is not None
            and len(self.source_data_columns) > 0
        ):
            columns.intersection_update(self.source_data_columns)

        result = dict.fromkeys(columns)
        for col in table.columns:
            if col.name not in result.keys():
                continue
            result[col.name] = self.__define_data_type(str(col.type).lower())

        return result

    @classmethod
    def __define_data_type(cls, type_):
        if type_ in ["integer", "bigint", "smallint"]:
            return "int"
        elif type_ in [
            "float",
            "double",
            "double_precision",
            "numeric",
            "real",
        ]:
            return "float"
        elif type_ in ["date", "datetime"]:
            return "datetime"
        elif type_ == "boolean":
            return "bool"
        else:
            return "str"

    def get_cleaned_columns(self):
        """Returns cleaned columns if self.file_columns is not None, otherwise return all columns"""
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
        """Returns source data with only specified columns in self.source_data_columns"""
        columns = self.get_cleaned_columns()
        meta_data = MetaData()
        engine = self.__get_engine_by_db_type()
        meta_data.reflect(bind=engine)
        table = meta_data.tables[self.db_table]

        with Session(engine) as session:
            columns = [getattr(table.c, column) for column in columns]
            stmt = select(*columns)
            if self.date_column:
                date_column = getattr(table.c, self.date_column)
                query = select(func.max(date_column))
                right_date = session.execute(query).scalar()
                if right_date is None:
                    right_date = datetime.date.today() - datetime.timedelta(
                        days=self.offset
                    )
                left_date = right_date - datetime.timedelta(days=1)
                stmt = stmt.where(
                    right_date > date_column, date_column >= left_date
                )
            res = session.execute(stmt).all()

            return res

    def get_source_data_for_grpc(self, source_id: int):
        """Returns generator of data converted in grpc message DataRequest"""
        res = self.get_source_all_data()
        count = len(res)
        for x in res:
            data_row = {k: str(v) for k, v in dict(x).items()}
            yield DataRequest(
                source_id=source_id, count=count, data_row=data_row
            )
