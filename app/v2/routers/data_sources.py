from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, delete, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from v2.database.database import get_session
from v2.database.schemas import (
    SourceFieldDB,
    DataSourceDB,
    SourceGroupDB,
    Preview,
)
from v2.etl.utils import create_connection, update_connection, delete_connection
from v2.models import SourceGroup, DataSource
from v2.utils import group_sources

router = APIRouter(prefix="/data_sources", tags=["Data Sources"])


@router.get("/", description="Get list of grouped data sources")
async def get_data_sources(session: AsyncSession = Depends(get_session)):
    """Get data sources with their previews"""
    response = await session.execute(
        select(
            SourceFieldDB.id,
            DataSourceDB.id.label("source_id"),
            SourceGroupDB.id.label("group_id"),
            SourceFieldDB.name,
            DataSourceDB.name.label("source_name"),
            SourceGroupDB.name.label("group_name"),
            DataSourceDB.has_preview,
        )
        .join(DataSourceDB, SourceFieldDB.source_id == DataSourceDB.id)
        .join(SourceGroupDB, DataSourceDB.group_id == SourceGroupDB.id)
    )
    return group_sources(response.fetchall())


@router.post("/groups", status_code=201, description="Create new sources group")
async def create_source_group(
    group: SourceGroup, session: AsyncSession = Depends(get_session)
):
    """
    Creates new group of data sources and corresponding Airflow connection
    :param group: group information
    :return: simplified source group information
    :raises HTTPException Source group already exists
    :raises HTTPException Airflow connection already exists
    """
    try:
        await session.execute(
            insert(SourceGroupDB).values(
                name=group.name, storage=group.storage.name
            )
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Source group already exists!"
        )

    if group.storage.conn_type:
        create_connection(group.storage)

    await session.commit()

    return {"name": group.name, "storage": group.storage.name}


@router.put(
    "/groups/{group_id}", description="Changes properties of sources group"
)
async def update_source_group(
    group_id: int,
    group: SourceGroup,
    session: AsyncSession = Depends(get_session),
):
    """
    Updates info about source group and corresponding Airflow connection
    :param group_id: id of group
    :param group: new group information
    :return: simplified group info
    :raises HTTPException Source group doesn't exist
    :raises HTTPException New Group name already exists
    :raises HTTPException Airflow connection already exists
    """
    response = await session.execute(
        select(SourceGroupDB.id, SourceGroupDB.storage).where(
            SourceGroupDB.id == group_id
        )
    )
    try:
        response = response.fetchone()._asdict()
        await session.execute(
            update(SourceGroupDB)
            .values(name=group.name, storage=group.storage.name)
            .where(SourceGroupDB.id == group_id)
        )
    except AttributeError:
        raise HTTPException(
            status_code=404, detail="Source group does not exist!"
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Group with this name already exists!"
        )

    if group.storage.conn_type:
        update_connection(response["storage"], group.storage)

    await session.commit()

    return {"name": group.name, "storage": group.storage.name}


@router.delete("/groups/{group_id}", description="Deletes source group")
async def delete_source_group(
    group_id: int, session: AsyncSession = Depends(get_session)
):
    """
    Deletes source group
    :param group_id: id of group to delete
    :return: None
    :raises HTTPException Source group already exists
    :raises HTTPException Airflow connection doesn't exist
    """
    response = await session.execute(
        select(SourceGroupDB.id, SourceGroupDB.storage).where(
            SourceGroupDB.id == group_id
        )
    )
    try:
        response = response.fetchone()._asdict()
    except AttributeError:
        raise HTTPException(
            status_code=404, detail="Source group does not exist!"
        )

    delete_connection(response["storage"])
    await session.execute(
        delete(SourceGroupDB).where(SourceGroupDB.id == group_id)
    )

    await session.commit()


@router.post(
    "/sources", status_code=201, description="Create data source with fields"
)
async def create_data_source(
    group_id: str,
    source: DataSource,
    session: AsyncSession = Depends(get_session),
):
    """
    Creates data source
    :param group_id: id of group data source refers to
    :param source: data source with fields
    :return: None
    :raises HTTPException Data source already exists
    """
    try:
        await session.execute(
            insert(DataSourceDB).values(name=source.name, group_id=group_id)
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Data source already exists"
        )

    response = await session.execute(
        select(DataSourceDB.id).where(
            DataSourceDB.name == source.name
            and DataSourceDB.group_id == group_id
        )
    )
    source_id = response.scalars().one()
    try:
        for field in source.fields:
            await session.execute(
                insert(SourceFieldDB).values(
                    name=field.name, source_id=source_id
                )
            )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Some of fields are repeated!"
        )

    await session.commit()


@router.put("/sources/{source_id}", description="Update data source")
async def update_data_source(
    source_id: int,
    source_name: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Updates data source information
    :param source_id: id of data source needed to update
    :param source_name: new name for data source
    :return: data source info
    :raises HTTPException Data source does not exist
    :raises HTTPException Data source already exists
    """
    response = await session.execute(
        select(DataSourceDB.id).where(DataSourceDB.id == source_id)
    )
    try:
        response.scalars().one()
        await session.execute(
            update(DataSourceDB)
            .values(name=source_name)
            .where(DataSourceDB.id == source_id)
        )
        await session.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=404, detail="Data source does not exist!"
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Data source with this name already exists!"
        )

    return {"id": source_id, "name": source_name}


@router.delete("/sources/{source_id}", description="Delete data source!")
async def delete_data_source(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """
    Deletes data source, it's fields and preview
    :param source_id: id of data source needed to delete
    :return: None
    """
    response = await session.execute(
        select(DataSourceDB.id).where(DataSourceDB.id == source_id)
    )
    if not response.fetchone():
        raise HTTPException(
            status_code=404, detail="Data source does not exist!"
        )

    await session.execute(delete(Preview).where(Preview.source == source_id))
    await session.execute(
        delete(SourceFieldDB).where(SourceFieldDB.source_id == source_id)
    )
    await session.execute(
        delete(DataSourceDB).where(DataSourceDB.id == source_id)
    )
    await session.commit()


@router.put("/fields/{field_id}", description="Update source field")
async def update_source_field(
    field_id: int, name: str, session: AsyncSession = Depends(get_session)
):
    """
    Updates source field
    :param field_id: id of a field needed to update
    :param name: new name for source field
    :return: new source field info
    :raises HTTPException Source field doesn't exist
    :raises HTTPException Source field already exists
    """
    try:
        response = await session.execute(
            select(SourceFieldDB.id).where(SourceFieldDB.id == field_id)
        )
        response.scalars().one()
        await session.execute(
            update(SourceFieldDB)
            .values(name=name)
            .where(SourceFieldDB.id == field_id)
        )
    except NoResultFound:
        raise HTTPException(
            status_code=404, detail="Source field does not exist!"
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Source field already exists!"
        )

    await session.commit()

    return {"id": field_id, "name": name}


@router.delete("/fields/{field_id}", description="Delete source field")
async def delete_source_field(
    field_id: int, session: AsyncSession = Depends(get_session)
):
    """
    Deletes source field
    :param field_id: id of a field needed to delete
    :return: None
    :raises HTTPException Source field doesn't exist
    """
    response = await session.execute(
        select(SourceFieldDB.id).where(SourceFieldDB.id == field_id)
    )
    try:
        response.scalars().one()
    except NoResultFound:
        raise HTTPException(
            status_code=404, detail="Source field with this id does not exist!"
        )

    await session.execute(
        delete(SourceFieldDB).where(SourceFieldDB.id == field_id)
    )

    await session.commit()


@router.post(
    "/replace_with_id",
    description="Replaces lists of sources and groups names with their ids",
)
async def replace_with_id(
    sources: list[str],
    groups: list[str],
    session: AsyncSession = Depends(get_session),
):
    pass


@router.post(
    "/replace_with_names",
    description="Replaces list of ids with lists of sources and groups names",
)
async def replace_with_names(
    sources: list[int], session: AsyncSession = Depends(get_session)
):
    pass


@router.get("/has_preview")
async def get_preview_param(session: AsyncSession = Depends(get_session)):
    pass
