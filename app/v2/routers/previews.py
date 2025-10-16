from fastapi import APIRouter, HTTPException, UploadFile, Depends
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from v2.database.database import get_session
from v2.database.schemas import DataSourceDB, Preview
from v2.utils import (
    group_previews,
    read_file,
    build_preview_data,
    check_input_file,
)

router = APIRouter(prefix="/previews", tags=["Previews"])


@router.get(
    "/{source_id}", description="Returns preview of specific data source"
)
async def get_preview(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns preview of specific data source
    :param source_id: id of data source which preview you want to get"""
    response = await session.execute(
        select(Preview.name, Preview.value, Preview.row).where(
            Preview.source == source_id
        )
    )
    response = response.fetchall()

    if len(response) == 0:
        raise HTTPException(
            status_code=404, detail="Data source does not have a preview!"
        )
    result = group_previews(response)
    return result


@router.post(
    "/", status_code=201, description="Adds preview to specific data source"
)
async def add_preview(
    source_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
):
    """
    Adds preview to specific data source
    :param source_id: id of data source which you want to add preview"""
    check_input_file(file)

    query = select(DataSourceDB.has_preview).where(DataSourceDB.id == source_id)
    response = await session.execute(query)

    if (response := response.fetchone()) is None:
        raise HTTPException(
            status_code=404, detail="Data source does not exist!"
        )
    if response[0] is True:
        raise HTTPException(
            status_code=418,
            detail="Data source already has preview! Use PUT method to change it!",
        )

    to_db = build_preview_data(read_file(file), source_id)
    session.add_all([Preview(**preview) for preview in to_db])
    await session.execute(
        update(DataSourceDB)
        .values(has_preview=True)
        .where(DataSourceDB.id == source_id)
    )
    await session.commit()


@router.put(
    "/{source_id}",
    description="Replaces old preview of specific data source with new one",
)
async def update_preview(
    source_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
):
    """Replaces old preview of specific data source with new one
    :param source_id: id of data source which preview you want to replace"""
    check_input_file(file)

    query = select(DataSourceDB.has_preview).where(DataSourceDB.id == source_id)
    response = await session.execute(query)

    if not (response := response.fetchone()):
        raise HTTPException(
            status_code=404, detail="Data source does not exist!"
        )
    if response[0] is False:
        raise HTTPException(
            status_code=418,
            detail="Data source does not have a preview! Use POST method to create it!",
        )

    to_db = build_preview_data(read_file(file), source_id)
    preview = [Preview(**preview) for preview in to_db]

    await session.execute(delete(Preview).where(Preview.source == source_id))
    session.add_all(preview)
    await session.commit()

    return Response(status_code=200)


@router.delete(
    "/{source_id}", description="Deletes preview of specific data source"
)
async def delete_preview(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Deletes preview of specific data source
    :param source_id: if of data source which preview you want to delete"""
    response = await session.execute(
        select(Preview.id).where(Preview.source == source_id)
    )
    if len(response.fetchall()) == 0:
        raise HTTPException(
            status_code=404,
            detail="Source does not exist or does not have previews!",
        )
    await session.execute(delete(Preview).where(Preview.source == source_id))
    await session.execute(
        update(DataSourceDB)
        .values(has_preview=False)
        .where(DataSourceDB.id == source_id)
    )
    await session.commit()
