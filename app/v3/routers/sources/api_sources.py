from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import get_session
from v3.database.schemas import Source

from v3.routers.sources.models.api_model import (
    APIModelInfo,
    APIModelCreate,
    APIAuthType,
    AUTH_TYPE_MODEL_DICT,
    APIConnectionBaseModel,
)
from v3.routers.sources.sources_managers.api_manager_utils.utils import (
    RESTAPIResponseTypes,
)
from v3.routers.sources.utils.exceptions import CustomException
from v3.routers.sources.utils.utils import (
    check_group_exists,
    check_source_name_in_group_exists,
    check_source_exists,
    update_for_simple_types,
)
from v3.routers.sources.sources_managers.api_manager import APISourceManager
from v3.routers.sources.models.general_model import SourceType


router = APIRouter(prefix="/api_sources")


@router.get("/auth_types", status_code=200, tags=["Sources: API-sources"])
async def read_implemented_auth_types():
    """Returns implemented auth types for RESTAPI sources"""
    return {
        item.value: AUTH_TYPE_MODEL_DICT.get(item.value).schema()
        for item in APIAuthType
    }


@router.post(
    "",
    response_model=APIModelInfo,
    status_code=201,
    tags=["Sources: API-sources"],
)
async def create_api_source(
    source: APIModelCreate, session: AsyncSession = Depends(get_session)
):
    """Creates RESTAPI source."""
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
    response_model=APIModelInfo,
    status_code=200,
    tags=["Sources: API-sources"],
)
async def full_update_api_source(
    source_id: int,
    source: APIModelCreate,
    session: AsyncSession = Depends(get_session),
):
    """Updates Source with any connection type into RESTAPI type"""
    updated_source = await update_for_simple_types(source_id, source, session)
    return updated_source.decoded_data()


@router.get(
    "/{source_id}/response_type",
    status_code=200,
    tags=["Sources: API-sources"],
    description=f"""Returns RESTAPI source response type if there is implemented parser for this type,
                         otherwise raises error. Allowed response types: {[x.value for x in RESTAPIResponseTypes]}""",
)
async def read_api_response_type(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns RESTAPI source response type if there is implemented parser for this type,
    otherwise raises error"""
    source = await check_source_exists(session, source_id)
    try:
        source_manager = APISourceManager(source.decoded_data()["con_data"])
        response_type = source_manager.get_response_type()
    except NotImplementedError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"response_type": response_type}


@router.get(
    "/{source_id}/source_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: API-sources"],
)
async def read_api_source_columns_by_source_id(
    source_id: int, session: AsyncSession = Depends(get_session)
):
    """Returns all attrs names of object of particular API source response"""
    source = await check_source_exists(session, source_id)

    if source.con_type != SourceType.RESTAPI.value:
        raise HTTPException(
            status_code=422,
            detail=f"Source with id={source_id} has con_type not equal to {SourceType.RESTAPI.value}",
        )

    try:
        source_manager = APISourceManager(source.decoded_data()["con_data"])
        columns = source_manager.get_source_data_columns()
    except NotImplementedError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return columns


@router.post(
    "/helpers/check_connection", status_code=200, tags=["Sources: API-helpers"]
)
async def api_check_connection_without_source_id(
    source: APIConnectionBaseModel,
):
    """Returns status code 200 if connection is successful, otherwise raises error."""
    try:
        source_manager = APISourceManager(source.dict())
        source_manager.check_connection()
    except CustomException as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"msg": "Connection successful"}


@router.post(
    "/helpers/get_source_columns",
    status_code=200,
    response_model=List,
    tags=["Sources: API-helpers"],
)
async def read_api_source_columns(source: APIConnectionBaseModel):
    """Returns all attrs names of object of particular API source response without source id"""
    try:
        source_manager = APISourceManager(source.dict())
        columns = source_manager.get_source_data_columns()
    except CustomException as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return columns
