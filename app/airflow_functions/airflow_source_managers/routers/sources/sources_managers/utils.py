from airflow_functions.airflow_source_managers.file_server.minio_client_manager import (
    minio_client,
)
from airflow_functions.airflow_source_managers.routers.sources.models.file_model import (
    FileImportType,
)
from airflow_functions.airflow_source_managers.routers.sources.models.general_model import (
    SourceType,
)
from airflow_functions.airflow_source_managers.routers.sources.sources_managers.api_manager import (
    APISourceManager,
)
from airflow_functions.airflow_source_managers.routers.sources.sources_managers.db_manager import (
    DBSourceManager,
)
from airflow_functions.airflow_source_managers.routers.sources.sources_managers.file_manager import (
    SFTPSourceManager,
    ManualFileSourceManager,
)
from v3.routers.sources.sources_managers.file_manager import FTPSourceManager


def get_source_manager(source: dict):
    """Returns instance of particular Source Manager class, otherwise raises error"""
    source_manager = None

    if source["con_type"] == SourceType.RESTAPI.value:
        source_manager = APISourceManager(source["con_data"])
    elif source["con_type"] == SourceType.DB.value:
        source_manager = DBSourceManager(source["con_data"])
    elif source["con_type"] == SourceType.FILE.value:
        if source["con_data"]["import_type"] == FileImportType.SFTP.value:
            source_manager = SFTPSourceManager(source["con_data"])
        elif source["con_data"]["import_type"] == FileImportType.FTP.value:
            source_manager = FTPSourceManager(source["con_data"])
        elif source["con_data"]["import_type"] == FileImportType.MANUAL.value:
            source_manager = ManualFileSourceManager(
                source_id=source["id"],
                con_data=source["con_data"],
                client=minio_client(),
            )

    if source_manager is None:
        raise ValueError(
            f"The check_connection method not implemented for connection type={source['con_type']}"
        )

    return source_manager
