from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession


from v3.database.database import get_session
from v3.database.schemas import SourceGroup
from v3.file_server.minio_client_manager import minio_client
from v3.grpc_config.dataview_manager_utils import (
    load_data_process,
    crete_source_group,
    delete_source_in_dataview_manager,
)

from v3.routers.sources.models.file_model import FileImportType
from v3.routers.sources.sources_managers.file_manager import (
    ManualFileSourceManager,
)
from v3.routers.sources.sources_managers.utils import get_source_manager

from v3.routers.sources.utils.utils import check_source_exists
from v3.routers.sources.models.general_model import SourceType


router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get("/con_types", status_code=200)
async def read_all_con_types():
    """Returns list of all connection types for sources"""
    return [x.value for x in SourceType]


@router.get("/source/{source_id}", status_code=200)
async def read_source(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    source = await check_source_exists(session, source_id)
    return source.decoded_data()


@router.delete("/source/{source_id}", status_code=204)
async def delete_source(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    source = await check_source_exists(session, source_id)

    if source.con_type == SourceType.FILE.value:
        decoded_data = source.decoded_data()
        if (
            decoded_data["con_data"]["import_type"]
            == FileImportType.MANUAL.value
        ):
            source_manager = ManualFileSourceManager(
                source_id=source.id,
                con_data=decoded_data["con_data"],
                client=minio_client(),
            )
            source_manager.delete_file_from_minio()
    source_id = source.id
    await session.delete(source)
    await session.commit()
    delete_source_in_dataview_manager(source_id=source_id)
    return {"msg": "Source deleted successfully"}


@router.get("/source/{source_id}/check_connection", status_code=200)
async def check_connection(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    source = await check_source_exists(session, source_id)
    source_manager = get_source_manager(source)
    try:
        res = source_manager.check_connection()
    except BaseException as e:
        raise HTTPException(status_code=422, detail=f"""{str(e)}""")
    if res is False:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {"msg": "Connection successful"}


@router.get("/source/{source_id}/load_data", status_code=200)
async def load_source_data(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    source = await check_source_exists(session, source_id)

    stmt = select(SourceGroup).where(SourceGroup.id == source.group_id)
    res = await session.execute(stmt)
    source_group = res.scalars().first()
    crete_source_group(source_group.id, source_group.name)
    load_data_process(source_group, source)

    return {"ok": "Data uploaded successfully"}
