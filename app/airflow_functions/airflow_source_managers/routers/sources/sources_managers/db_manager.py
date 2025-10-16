import pickle

from airflow_functions.airflow_source_managers.config import (
    DB_USER,
    DB_PASS,
    DB_HOST,
    DB_PORT,
    DB_NAME,
)
from sqlalchemy import create_engine, MetaData, select, Column, Integer, String
from sqlalchemy.orm import Session, declarative_base

from airflow_functions.airflow_source_managers.routers.sources.models.db_model import (
    DBDriverTypes,
)
from airflow_functions.airflow_source_managers.routers.sources.sources_managers.general import (
    ABCSourceManager,
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
        meta_data.reflect(bind=self.__get_engine_by_db_type())

    def get_all_tables_from_db(self):
        """Returns all db tables"""
        meta_data = MetaData()
        meta_data.reflect(bind=self.__get_engine_by_db_type())
        return list(meta_data.tables.keys())

    def get_source_data_columns(self):
        """Returns list of all db table columns"""
        if self.db_table is None:
            raise ValueError("Please set value for db_table attribute")

        meta_data = MetaData()
        meta_data.reflect(bind=self.__get_engine_by_db_type())
        table = meta_data.tables.get(self.db_table, None)
        if table is None:
            raise ValueError(
                f"Table with name '{self.db_table}' does not exist!"
            )
        return list(table.columns.keys())

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
        """Returns source data with only specified columns in self.source_data_columns"""
        columns = self.get_cleaned_columns()
        meta_data = MetaData()
        engine = self.__get_engine_by_db_type()
        meta_data.reflect(bind=engine)
        table = meta_data.tables[self.db_table]

        with Session(engine) as session:
            columns = [getattr(table.c, column) for column in columns]
            stmt = select(*columns)
            res = session.execute(stmt).all()

            return res

    # def get_source_data_for_grpc(self, source_id: int):
    #     """Returns generator of data converted in grpc message DataRequest"""
    #     res = self.get_source_all_data()
    #     count = len(res)
    #     for x in res:
    #         data_row = {k: str(v) for k, v in dict(x).items()}
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
        res = self.get_source_all_data()

        with Session(engine) as session:
            [
                session.add(Data(data=pickle.dumps(dict(item)).hex()))
                for item in res
            ]

            session.commit()
