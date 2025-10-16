import io
from typing import List, Optional

import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Form,
    UploadFile,
    File,
    Path,
)
from minio import Minio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import get_session
from v3.database.schemas import Source
from v3.file_server.minio_client_manager import minio_client
from v3.routers.sources.models.file_model import (
    FileImportType,
    FileExtension,
    SFTPModelInfo,
    SFTPModelCreate,
    ManualModelInfo,
    SFTPConnectionModelCheck,
    SFTPConnectionModelCheckPath,
    FTPModelCreate,
    FTPModelInfo,
)
from v3.routers.sources.models.general_model import SourceType
from v3.routers.sources.sources_managers.file_manager import (
    SFTPSourceManager,
    ManualFileSourceManager,
    get_pandas_file_reader,
    FTPSourceManager,
)
from v3.routers.sources.sources_managers.file_manager_utils.utils import (
    get_csv_delimiter,
)
from v3.routers.sources.utils.exceptions import (
    ValidationError,
    SourceConnectionError,
)
from v3.routers.sources.utils.file_utils import validate_file_extension
from v3.routers.sources.utils.utils import (
    check_group_exists,
    check_source_name_in_group_exists,
    check_source_exists,
    update_for_simple_types,
)
from v3.config import MINIO_BUCKET

router = APIRouter(prefix="/file_sources")


@router.get(
    "/types",
    response_model=List,
    status_code=200,
    tags=["Sources: File-sources"],
)
async def read_implemented_file_sources_types():
    """Returns implemented types for file sources"""
    return [item.value for item in FileImportType]


@router.get(
    "/file_extensions",
    response_model=List,
    status_code=200,
    tags=["Sources: File-sources"],
)
async def read_implemented_file_sources_file_extensions():
    """Returns implemented file extensions"""
    return [item.value for item in FileExtension]


@router.post(
    "/sftp",
    response_model=SFTPModelInfo,
    status_code=201,
    tags=["Sources: File-SFTP sources"],
)
async def create_file_sftp_source(
    source: SFTPModelCreate, session: AsyncSession = Depends(get_session)
):
    await check_group_exists(session, source.group_id)
    await check_source_name_in_group_exists(
        session, source.group_id, source.name
    )

    source = Source(**source.dict())
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source.decoded_data()


@router.put(
    "/sftp/{source_id}",
    response_model=SFTPModelInfo,
    status_code=200,
    tags=["Sources: File-SFTP sources"],
)
async def full_update_file_sftp_source(
    source_id: int,
    source: SFTPModelCreate,
    session: AsyncSession = Depends(get_session),
):
    """Updates Source with any connection type into File SFTP type"""
    updated_source = await update_for_simple_types(source_id, source, session)
    return updated_source.decoded_data()


@router.get(
    "/sftp/{source_id}/files_in_source_path",
    status_code=200,
    response_model=List,
    tags=["Sources: File-SFTP sources"],
)
async def read_files_and_directories_from_sftp_source_path(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns all directories and files from File source with connection_type = SFTP"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.FILE.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.FILE.value}",
        )

    decoded_data = source.decoded_data()
    if decoded_data["con_data"]["import_type"] != FileImportType.SFTP.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has import_type not equal to {FileImportType.SFTP.value}",
        )

    source_manager = SFTPSourceManager(decoded_data["con_data"])
    try:
        list_of_files_and_dirs = source_manager.get_list_of_files_and_dirs()
    except (SourceConnectionError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return list_of_files_and_dirs


@router.get(
    "/sftp/{source_id}/file_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: File-SFTP sources"],
)
async def read_file_sftp_source_columns(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns all table columns for particular File source"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.FILE.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.FILE.value}",
        )

    decoded_data = source.decoded_data()
    if decoded_data["con_data"]["import_type"] != FileImportType.SFTP.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has import_type not equal to {FileImportType.SFTP.value}",
        )

    try:
        source_manager = SFTPSourceManager(decoded_data["con_data"])
        columns = source_manager.get_source_data_columns()
    except (SourceConnectionError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return columns


@router.post(
    "/sftp/helpers/check_connection",
    status_code=200,
    tags=["Sources: File-SFTP helpers"],
)
async def sftp_check_connection_without_source_id(
    source: SFTPConnectionModelCheckPath,
):
    """Returns status code 200 if connection is successful, otherwise raises error."""
    con_data = source.dict()

    try:
        source_manager = SFTPSourceManager(con_data)
        source_manager.check_connection()

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except SourceConnectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"msg": "Connection successful"}


@router.post(
    "/sftp/helpers/listdir",
    status_code=200,
    tags=["Sources: File-SFTP helpers"],
)
async def sftp_get_dirs_and_files_names(source: SFTPConnectionModelCheckPath):
    """Returns all dirs and files names from sftp path if connection is successful,
    otherwise raises error."""
    con_data = source.dict()

    try:
        source_manager = SFTPSourceManager(con_data)
        result = source_manager.get_list_of_files_and_dirs()
    except (SourceConnectionError, ValidationError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=f"""{str(e)}""")

    return result


@router.post(
    "/sftp/helpers/file_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: File-SFTP helpers"],
)
async def read_sftp_file_columns_without_source_id(
    source: SFTPConnectionModelCheck,
):
    """Returns all file columns for SFTP source if connection is successful, otherwise raises error."""
    try:
        source_manager = SFTPSourceManager(source.dict())
        columns = source_manager.get_source_data_columns()
    except (SourceConnectionError, ValidationError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return columns


@router.post(
    "/manual",
    status_code=201,
    response_model=ManualModelInfo,
    tags=["Sources: File-Manual sources"],
)
async def create_file_manual_source(
    name: str = Form(),
    group_id: int = Form(),
    file_columns: Optional[List] = None,
    file: UploadFile = File(),
    client: Minio = Depends(minio_client),
    session: AsyncSession = Depends(get_session),
):
    await check_group_exists(session, group_id)
    await check_source_name_in_group_exists(session, group_id, name)

    # validate file_columns on empty values
    if file_columns is not None:
        for x in file_columns:
            if not x:
                raise HTTPException(
                    status_code=422,
                    detail="source_data_columns can`t have empty column names",
                )

    validate_file_extension(file.filename)

    source = Source(
        name=name,
        group_id=group_id,
        con_type=SourceType.FILE.value,
        con_data={
            "import_type": FileImportType.MANUAL.value,
            "file_name": file.filename,
            "source_data_columns": file_columns,
        },
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)

    try:
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=f"{source.id}/{file.filename}",
            data=file.file,
            content_type=file.content_type,
            length=file.size,
        )
    except BaseException as e:
        await session.delete(source)
        await session.commit()
        raise HTTPException(status_code=422, detail=str(e))
    return source.decoded_data()


@router.put(
    "/manual/{source_id}",
    response_model=ManualModelInfo,
    status_code=200,
    tags=["Sources: File-Manual sources"],
)
async def full_update_file_manual_source(
    name: str = Form(),
    source_id: int = Path(),
    group_id: int = Form(),
    file_columns: Optional[List] = None,
    file: UploadFile = File(),
    client: Minio = Depends(minio_client),
    session: AsyncSession = Depends(get_session),
):
    """Updates Source with any connection type into File Manual type"""

    # validate file_columns on empty values
    if file_columns is not None:
        for x in file_columns:
            if not x:
                raise HTTPException(
                    status_code=422,
                    detail="source_data_columns can`t have empty column names",
                )

    await check_group_exists(session, group_id)
    # check if source name is unique across the group
    stmt = select(Source).where(
        Source.name == name, Source.group_id == group_id, Source.id != source_id
    )
    source_from_db = await session.execute(stmt)
    source_from_db = source_from_db.scalars().first()
    if source_from_db is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Source named '{name}' already exists in group with id={group_id}!",
        )

    validate_file_extension(file.filename)

    source_to_update = await check_source_exists(session, source_id)

    if source_to_update.con_type == SourceType.FILE.value:
        decoded_data = source_to_update.decoded_data()
        if (
            decoded_data["con_data"]["import_type"]
            == FileImportType.MANUAL.value
        ):
            source_manager = ManualFileSourceManager(
                source_id=source_to_update.id,
                con_data=decoded_data["con_data"],
                client=minio_client(),
            )
            source_manager.delete_file_from_minio()

    source_to_update.name = name
    source_to_update.group_id = group_id
    source_to_update.con_type = SourceType.FILE.value
    source_to_update.con_data = {
        "import_type": FileImportType.MANUAL.value,
        "filename": file.filename,
        "source_data_columns": file_columns,
    }

    session.add(source_to_update)
    await session.commit()
    await session.refresh(source_to_update)

    try:
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=f"{source_to_update.id}/{file.filename}",
            data=file.file,
            content_type=file.content_type,
            length=file.size,
        )
    except BaseException as e:
        await session.delete(source_to_update)
        await session.commit()
        raise HTTPException(status_code=422, detail=str(e))

    return source_to_update.decoded_data()


@router.get(
    "/manual/{source_id}/file_columns",
    status_code=200,
    tags=["Sources: File-Manual sources"],
)
async def read_file_manual_source_columns(
    source_id: int,
    session: AsyncSession = Depends(get_session),
    client: Minio = Depends(minio_client),
):
    """Returns all table columns for particular File Manual source"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.FILE.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.FILE.value}",
        )
    decoded_data = source.decoded_data()
    if decoded_data["con_data"]["import_type"] != FileImportType.MANUAL.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has import_type not equal to {FileImportType.MANUAL.value}",
        )

    source_manager = ManualFileSourceManager(
        source_id=source.id, client=client, con_data=decoded_data["con_data"]
    )

    try:
        columns = source_manager.get_source_data_columns()
    except BaseException as e:
        raise HTTPException(status_code=422, detail=str(e))
    return columns


@router.post(
    "/manual/helpers/get_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: File-Manual helpers"],
)
async def read_manual_file_columns(file: UploadFile = File()):
    validate_file_extension(file.filename)

    try:
        pandas_file_reader = get_pandas_file_reader(file.filename)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    file_data = file.file.read()

    additional_data = dict()
    if pandas_file_reader == pd.read_csv:
        additional_data = dict(delimiter=get_csv_delimiter(file_data))
    with io.BytesIO(file_data) as output:
        try:
            columns = list(
                pandas_file_reader(output, **additional_data).columns
            )
        except BaseException as e:
            return HTTPException(status_code=422, detail=str(e))
    return columns


@router.post(
    "/ftp",
    response_model=FTPModelInfo,
    status_code=201,
    tags=["Sources: File-FTP sources"],
)
async def create_file_ftp_source(
    source: FTPModelCreate, session: AsyncSession = Depends(get_session)
):
    await check_group_exists(session, source.group_id)
    await check_source_name_in_group_exists(
        session, source.group_id, source.name
    )

    source = Source(**source.dict())
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source.decoded_data()


@router.put(
    "/ftp/{source_id}",
    response_model=FTPModelInfo,
    status_code=200,
    tags=["Sources: File-FTP sources"],
)
async def full_update_file_ftp_source(
    source_id: int,
    source: FTPModelCreate,
    session: AsyncSession = Depends(get_session),
):
    """Updates Source with any connection type into File SFTP type"""
    updated_source = await update_for_simple_types(source_id, source, session)
    return updated_source.decoded_data()


@router.get(
    "/ftp/{source_id}/files_in_source_path",
    status_code=200,
    response_model=List,
    tags=["Sources: File-FTP sources"],
)
async def read_files_and_directories_from_ftp_source_path(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns all directories and files from File source with connection_type = SFTP"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.FILE.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.FILE.value}",
        )

    decoded_data = source.decoded_data()
    if decoded_data["con_data"]["import_type"] != FileImportType.FTP.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has import_type not equal to {FileImportType.FTP.value}",
        )

    try:
        source_manager = FTPSourceManager(decoded_data["con_data"])
        list_of_files_and_dirs = source_manager.get_list_of_files_and_dirs()
    except (SourceConnectionError, ValidationError) as e:
        msg = str(e).split("\n")[0]
        raise HTTPException(status_code=422, detail=msg)
    return list_of_files_and_dirs


@router.get(
    "/ftp/{source_id}/file_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: File-FTP sources"],
)
async def read_file_ftp_source_columns(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns all table columns for particular File source"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.FILE.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.FILE.value}",
        )

    decoded_data = source.decoded_data()
    if decoded_data["con_data"]["import_type"] != FileImportType.FTP.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has import_type not equal to {FileImportType.FTP.value}",
        )

    try:
        source_manager = FTPSourceManager(decoded_data["con_data"])
        columns = source_manager.get_source_data_columns()
    except (SourceConnectionError, ValidationError) as e:
        msg = str(e).split("\n")[0]
        raise HTTPException(status_code=422, detail=msg)
    return columns


@router.post(
    "/ftp/helpers/check_connection",
    status_code=200,
    tags=["Sources: File-FTP helpers"],
)
async def ftp_check_connection_without_source_id(
    source: SFTPConnectionModelCheckPath,
):
    """Returns status code 200 if connection is successful, otherwise raises error."""
    con_data = source.dict()

    try:
        source_manager = FTPSourceManager(con_data)
        source_manager.check_connection()
    except (SourceConnectionError, ValidationError) as exc:
        msg = str(exc).split("\n")[0]
        raise HTTPException(status_code=422, detail=msg)

    return {"msg": "Connection successful"}


@router.post(
    "/ftp/helpers/listdir", status_code=200, tags=["Sources: File-FTP helpers"]
)
async def ftp_get_dirs_and_files_names(source: SFTPConnectionModelCheckPath):
    """Returns all dirs and files names from sftp path if connection is successful,
    otherwise raises error."""
    con_data = source.dict()

    try:
        source_manager = FTPSourceManager(con_data)
        result = source_manager.get_list_of_files_and_dirs()
    except (SourceConnectionError, ValidationError) as e:
        msg = str(e).split("\n")[0]
        raise HTTPException(status_code=422, detail=msg)

    return result


@router.post(
    "/ftp/helpers/file_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: File-FTP helpers"],
)
async def read_ftp_file_columns_without_source_id(
    source: SFTPConnectionModelCheck,
):
    """Returns all file columns for SFTP source if connection is successful, otherwise raises error."""
    try:
        source_manager = FTPSourceManager(source.dict())
        columns = source_manager.get_source_data_columns()
    except (SourceConnectionError, ValidationError) as e:
        msg = str(e).split("\n")[0]
        raise HTTPException(status_code=422, detail=msg)
    return columns
