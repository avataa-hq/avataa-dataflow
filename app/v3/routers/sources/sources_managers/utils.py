from fastapi import HTTPException

from v3.database.schemas import Source
from v3.file_server.minio_client_manager import minio_client
from v3.routers.sources.models.file_model import FileImportType
from v3.routers.sources.models.general_model import SourceType
from v3.routers.sources.sources_managers.api_manager import APISourceManager
from v3.routers.sources.sources_managers.db_manager import DBSourceManager
from v3.routers.sources.sources_managers.file_manager import (
    SFTPSourceManager,
    ManualFileSourceManager,
    FTPSourceManager,
)
from v3.routers.sources.sources_managers.inventory_manager import (
    InventorySourceManager,
)


def get_source_manager(source: Source):
    """Returns instance of particular Source Manager class, otherwise raises error"""
    source_manager = None
    match source.con_type:
        case SourceType.RESTAPI.value:
            source_manager = APISourceManager(source.decoded_data()["con_data"])
        case SourceType.DB.value:
            source_manager = DBSourceManager(source.decoded_data()["con_data"])
        case SourceType.FILE.value:
            decoded_data = source.decoded_data()
            if (
                decoded_data["con_data"]["import_type"]
                == FileImportType.SFTP.value
            ):
                source_manager = SFTPSourceManager(decoded_data["con_data"])
            elif (
                decoded_data["con_data"]["import_type"]
                == FileImportType.FTP.value
            ):
                source_manager = FTPSourceManager(decoded_data["con_data"])
            elif (
                decoded_data["con_data"]["import_type"]
                == FileImportType.MANUAL.value
            ):
                source_manager = ManualFileSourceManager(
                    source_id=source.id,
                    con_data=decoded_data["con_data"],
                    client=minio_client(),
                )
        case SourceType.INVENTORY.value:
            source_manager = InventorySourceManager(
                source.decoded_data()["con_data"]
            )

    if source_manager is None:
        raise HTTPException(
            status_code=422,
            detail=f"The check_connection method not implemented for connection type={source.con_type}",
        )

    return source_manager
