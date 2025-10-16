from sqlalchemy import (
    Column,
    Integer,
    String,
    PrimaryKeyConstraint,
    UniqueConstraint,
    ForeignKeyConstraint,
    Boolean,
    CheckConstraint,
    Text,
    JSON,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SourceGroupDB(Base):
    __tablename__ = "source_groups"

    id: int = Column("id", Integer, nullable=False, autoincrement=True)
    name: str = Column("name", String(32), nullable=False)
    storage: str = Column("storage", String(32), nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="source_groups_pkey"),
        UniqueConstraint("name", name="source_groups_name_uc"),
    )


class DataSourceDB(Base):
    __tablename__ = "data_sources"

    id: int = Column("id", Integer, nullable=False, autoincrement=True)
    group_id = Column("group_id", Integer, nullable=False)
    name: str = Column("name", String(32), nullable=False)
    has_preview: bool = Column("has_preview", Boolean, server_default="False")

    __table_args__ = (
        PrimaryKeyConstraint("id", name="data_sources_pkey"),
        ForeignKeyConstraint(
            ["group_id"], ["source_groups.id"], name="data_sources_group_fkey"
        ),
        UniqueConstraint("name", "group_id", name="data_sources_name_uc"),
    )


class SourceFieldDB(Base):
    __tablename__ = "source_fields"

    id: int = Column("id", Integer, nullable=False, autoincrement=True)
    source_id: int = Column("source_id", Integer, nullable=False)
    name: str = Column("name", String(32), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="source_fields_pkey"),
        ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], name="source_fields_source_fkey"
        ),
        UniqueConstraint("name", "source_id", name="source_fields_name_uc"),
    )


class Preview(Base):
    __tablename__ = "previews"

    id: int = Column("id", Integer)
    name: str = Column("name", String(32))
    value: str = Column("value", String(32))
    row: int = Column("row", Integer)
    source: int = Column("source_id", Integer)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="previews_pkey"),
        ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], name="previews_source_fkey"
        ),
        CheckConstraint("""row BETWEEN 1 AND 5""", name="previews_row_check"),
    )


class Operation(Base):
    __tablename__ = "operations"

    id: int = Column("id", Integer, nullable=False)
    source_id: int = Column("source_id", Integer, nullable=False)
    type: str = Column("operation_type", String(16), nullable=False)
    name: str = Column("name", String(32), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="operations_pkey"),
        ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], name="operations_source_fkey"
        ),
        UniqueConstraint("source_id", "name", name="operations_uc"),
        CheckConstraint(
            """operation_type = 'extract'
                      OR operation_type = 'transform'
                      OR operation_type = 'load'""",
            name="operations_type_check",
        ),
    )


class DBSettings(Base):
    __tablename__ = "db_settings"

    id: int = Column("id", Integer, nullable=False)
    operation_id: int = Column("operation_id", Integer, nullable=False)
    driver: str = Column("driver", String(16), nullable=False)
    host: str = Column("host", String(32), nullable=False)
    port: str = Column("port", String(4), nullable=False)
    user: str = Column("user", String(128))
    password: str = Column("password", String(128))
    table: str = Column("table", String(16), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="db_settings_pkey"),
        ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="db_settings_operation_fkey",
        ),
        UniqueConstraint("operation_id", name="db_settings_operation_uc"),
    )


class FileSettings(Base):
    __tablename__ = "file_settings"

    id: int = Column("id", Integer, nullable=False)
    operation_id: int = Column("operation_id", Integer, nullable=False)
    data: str = Column("data", Text, nullable=False)
    extension: str = Column("extension", String(8), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="file_settings_pkey"),
        ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="file_settings_operation_fkey",
        ),
        UniqueConstraint("operation_id", name="file_settings_operation_uc"),
        CheckConstraint(
            """extension = 'csv' OR extension = 'xlsx' OR extension = 'json'""",
            name="file_settings_extension_check",
        ),
    )


class SFTPSettings(Base):
    __tablename__ = "sftp_settings"

    id: int = Column("id", Integer, nullable=False)
    operation_id: int = Column("operation_id", Integer, nullable=False)
    host: str = Column("host", String(32), nullable=False)
    port: str = Column("port", String(4), nullable=False)
    user: str = Column("user", String(128))
    password: str = Column("password", String(128))
    file_path: str = Column("file_path", String(128))

    __table_args__ = (
        PrimaryKeyConstraint("id", name="sftp_settings_pkey"),
        ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="sftp_settings_operation_fkey",
        ),
        UniqueConstraint("operation_id", name="sftp_settings_operation_uc"),
    )


class APIAuth(Base):
    __tablename__ = "api_auth"

    id: int = Column("id", Integer, nullable=False)
    user: str = Column("user", String(128))
    password: str = Column("password", String(128))
    token: str = Column("token", String(128))
    client_id: str = Column("client_id", String(128))
    client_secret: str = Column("secret", String(128))
    settings_id: int = Column("settings_id", Integer)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="api_auth_pkey"),
        ForeignKeyConstraint(
            ["settings_id"], ["api_settings.id"], name="api_auth_settings_fkey"
        ),
    )


class APISettings(Base):
    __tablename__ = "api_settings"

    id: int = Column("id", Integer, nullable=False)
    operation_id: int = Column("operation_id", Integer, nullable=False)
    entry_point: str = Column("entry_point", String(32), nullable=False)
    end_point: str = Column("end_point", String(32), nullable=False)
    params: dict = Column("params", JSON, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("id", name="api_settings_pkey"),
        ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="api_settings_operation_fkey",
        ),
    )
