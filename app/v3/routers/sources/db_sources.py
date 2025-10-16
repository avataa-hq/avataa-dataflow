from typing import List, Annotated

from fastapi import APIRouter, HTTPException, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import get_session
from v3.database.schemas import Source
from v3.routers.sources.sources_managers.db_manager import DBSourceManager
from v3.routers.sources.models.db_model import (
    DBModelInfo,
    DBModelCreate,
    DBConnectionModelCheck,
    DBDriverTypes,
    DBConnectionModelCheckColumns,
)
from v3.routers.sources.utils.exceptions import (
    SourceConnectionError,
    ValidationError,
    ResourceNotFoundError,
)
from v3.routers.sources.utils.utils import (
    check_group_exists,
    check_source_name_in_group_exists,
    check_source_exists,
    update_for_simple_types,
)
from v3.routers.sources.models.general_model import SourceType


router = APIRouter(prefix="/db_sources")


@router.get(
    "/db_drivers",
    response_model=List,
    status_code=200,
    tags=["Sources: DB-sources"],
)
async def read_implemented_db_drivers():
    """Returns list of implemented db drivers"""
    return [x.value for x in DBDriverTypes]


@router.post(
    "",
    response_model=DBModelInfo,
    status_code=201,
    tags=["Sources: DB-sources"],
)
async def create_db_source(
    source: DBModelCreate, session: AsyncSession = Depends(get_session)
):
    """Creates database source."""
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
    "/{source_id}",
    response_model=DBModelInfo,
    status_code=200,
    tags=["Sources: DB-sources"],
)
async def full_update_db_source(
    source_id: int,
    source: DBModelCreate,
    session: AsyncSession = Depends(get_session),
):
    """Updates Source with any connection type into DB type"""
    updated_source = await update_for_simple_types(source_id, source, session)
    return updated_source.decoded_data()


@router.get(
    "/{source_id}/db_tables",
    status_code=200,
    response_model=List,
    tags=["Sources: DB-sources"],
)
async def read_db_source_tables(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns all tables from DB source"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.DB.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.DB.value}",
        )

    source_manager = DBSourceManager(source.decoded_data()["con_data"])
    try:
        tables = source_manager.get_all_tables_from_db()
    except BaseException as e:
        raise HTTPException(status_code=422, detail=str(e))
    return tables


@router.get(
    "/{source_id}/db_table_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: DB-sources"],
)
async def read_db_source_table_columns(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns all table columns for particular DB source"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.DB.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.DB.value}",
        )

    source_manager = DBSourceManager(source.decoded_data()["con_data"])

    try:
        columns = source_manager.get_source_data_columns()
    except BaseException as e:
        raise HTTPException(status_code=422, detail=str(e))
    return columns


@router.post(
    "/helpers/check_connection", status_code=200, tags=["Sources: DB-helpers"]
)
async def db_check_connection_without_source_id(source: DBConnectionModelCheck):
    """Returns status code 200 if connection is successful, otherwise raises error."""

    source_manager = DBSourceManager(source.dict())

    try:
        source_manager.check_connection()
    except BaseException as e:
        raise HTTPException(status_code=422, detail=f"""{str(e)}""")

    return {"msg": "Connection successful"}


@router.post(
    "/helpers/db_tables",
    status_code=200,
    response_model=List,
    tags=["Sources: DB-helpers"],
)
async def read_db_tables_without_source_id(source: DBConnectionModelCheck):
    """Returns all tables names for DB source if connection is successful, otherwise raises error."""
    source_manager = DBSourceManager(source.dict())
    try:
        result = source_manager.get_all_tables_from_db()
    except BaseException as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@router.post(
    "/helpers/db_table_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: DB-helpers"],
)
async def read_db_table_columns_without_source_id(
    source: DBConnectionModelCheckColumns,
    only_datetime: Annotated[bool, Query()] = False,
):
    """Returns all table columns for DB source if connection is successful, otherwise raises error."""
    source_manager = DBSourceManager(source.dict())

    try:
        columns = source_manager.get_source_data_columns(only_datetime)
    except (
        SourceConnectionError,
        ValidationError,
        ResourceNotFoundError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return columns
