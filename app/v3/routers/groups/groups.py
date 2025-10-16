import grpc.aio
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from v3.database.database import get_session
from v3.database.schemas import SourceGroup, Source
from v3.file_server.minio_client_manager import minio_client
from v3.grpc_config.dataview_manager_utils import (
    crete_source_group,
    load_data_process,
    delete_group_in_dataview_manager,
)
from v3.routers.groups.models import (
    SourceGroupCreateModel,
    SourceGroupModelInfo,
    SourceGroupPatchModel,
)
from v3.routers.sources.models.file_model import FileImportType
from v3.routers.sources.models.general_model import SourceType
from v3.routers.sources.sources_managers.file_manager import (
    ManualFileSourceManager,
)

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("", status_code=200)
async def read_groups(session: AsyncSession = Depends(get_session)):
    stmt = select(SourceGroup)
    groups = await session.execute(stmt)
    groups = groups.scalars().all()
    return groups


@router.get("/{group_id}", status_code=200, response_model=SourceGroupModelInfo)
async def read_group(
    group_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns info about group by group_id"""

    stmt = select(SourceGroup).where(SourceGroup.id == group_id)
    group = await session.execute(stmt)
    group = group.scalars().first()

    if group is None:
        raise HTTPException(
            status_code=404, detail=f"Group with id = {group_id} does not exist"
        )
    return group.__dict__


@router.patch(
    "/{group_id}", status_code=200, response_model=SourceGroupModelInfo
)
async def partial_update_group(
    group_id: int,
    group: SourceGroupPatchModel,
    session: AsyncSession = Depends(get_session),
):
    """Updates group data by group_id"""

    stmt = select(SourceGroup).where(SourceGroup.id == group_id)
    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.scalars().first()

    if group_from_db is None:
        raise HTTPException(
            status_code=404, detail=f"Group with id = {group_id} does not exist"
        )

    for k, v in group.dict(exclude_unset=True).items():
        setattr(group_from_db, k, v)

    session.add(group_from_db)
    await session.commit()
    await session.refresh(group_from_db)
    return group_from_db.__dict__


@router.post("", status_code=201, response_model=SourceGroupModelInfo)
async def create_group(
    group: SourceGroupCreateModel, session: AsyncSession = Depends(get_session)
):
    """Creates group"""
    stmt = select(SourceGroup).where(SourceGroup.name == group.name)
    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.first()

    if group_from_db is not None:
        raise HTTPException(
            status_code=422,
            detail=f"A group named '{group.name}' already exists",
        )

    new_group = SourceGroup(name=group.name, source_type=group.source_type)
    session.add(new_group)
    await session.commit()
    await session.refresh(new_group)
    return new_group.__dict__


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: int, session: AsyncSession = Depends(get_session)
):
    """Deletes group by group_id"""

    stmt = select(SourceGroup).where(SourceGroup.id == group_id)
    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.scalars().first()

    if group_from_db is None:
        raise HTTPException(
            status_code=404, detail=f"Group with id = {group_id} does not exist"
        )

    stmt = select(Source).where(
        Source.group_id == group_from_db.id,
        Source.con_type == SourceType.FILE.value,
    )
    all_group_file_sources = await session.execute(stmt)
    all_group_file_sources = all_group_file_sources.scalars().all()

    for source in all_group_file_sources:
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
    group_id = group_from_db.id
    await session.delete(group_from_db)
    await session.commit()
    delete_group_in_dataview_manager(group_id=group_id)
    return {"msg": "Group deleted successfully"}


@router.get("/{group_id}/load_data", status_code=200)
async def load_group_data(
    group_id: int, session: AsyncSession = Depends(get_session)
):
    stmt = select(SourceGroup).where(SourceGroup.id == group_id)
    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.scalars().first()

    if group_from_db is None:
        raise HTTPException(
            status_code=404, detail=f"Group with id = {group_id} does not exist"
        )

    stmt = select(Source).where(Source.group_id == group_id)
    group_sources = await session.execute(stmt)
    group_sources = group_sources.scalars().all()

    try:
        crete_source_group(group_from_db.id, group_from_db.name)

        for source in group_sources:
            load_data_process(group_from_db, source)
    except grpc.RpcError as exc:
        if exc.code() == grpc.StatusCode.UNAVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Service unavailable! Try again later...",
            )

    return {"msg": "Data uploaded successfully"}


@router.get("/{group_id}/sources", status_code=200)
async def read_group_sources(
    group_id: int, session: AsyncSession = Depends(get_session)
):
    stmt = select(SourceGroup).where(SourceGroup.id == group_id)
    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.scalars().first()

    if group_from_db is None:
        raise HTTPException(
            status_code=404, detail=f"Group with id = {group_id} does not exist"
        )

    stmt = select(Source).where(Source.group_id == group_id)
    res = await session.execute(stmt)
    res = res.scalars().all()
    res = [source.decoded_data() for source in res]
    return res
