from typing import Annotated

import grpc
from fastapi import APIRouter, Body, Depends, Path, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import get_session
from v3.database.schemas import Source
from v3.grpc_config.mo_info_client import MOInfoClient
from v3.routers.sources.models.inventory_model import InventoryModelCreate
from v3.routers.sources.utils.utils import (
    check_group_exists,
    check_source_name_in_group_exists,
    update_for_simple_types,
)

router = APIRouter(prefix="/inventory_sources")


@router.post("", tags=["Sources: Inventory-sources"])
async def create_source_from_inventory(
    source: Annotated[InventoryModelCreate, Body()],
    session: AsyncSession = Depends(get_session),
):
    """Create new source of inventory type (tmo loaded from MS Inventory)"""
    await check_group_exists(session, source.group_id)
    await check_source_name_in_group_exists(
        session, source.group_id, source.name
    )
    if (
        source.con_data.source_data_columns is not None
        and len(source.con_data.source_data_columns) > 0
    ):
        source.con_data.source_data_columns.extend(["tmo_id"])
    source = Source(**source.dict())
    session.add(source)
    await session.commit()
    await session.refresh(source)

    return source.decoded_data()


@router.put("/{source_id}", tags=["Sources: Inventory-sources"])
async def update_to_inventory_source(
    source_id: Annotated[int, Path(gt=0)],
    source: Annotated[InventoryModelCreate, Body()],
    session: AsyncSession = Depends(get_session),
):
    """Update some source to inventory type"""
    if (
        source.con_data.source_data_columns is not None
        and len(source.con_data.source_data_columns) > 0
    ):
        source.con_data.source_data_columns.extend(["tmo_id"])
    updated_source = await update_for_simple_types(source_id, source, session)
    return updated_source.decoded_data()


@router.get("/helpers/columns", tags=["Sources: Inventory-helpers"])
async def read_tmo_fields(
    tmo_id: Annotated[int, Query(gt=0)],
):
    """Read tmo columns to choose them in future processing"""
    try:
        res = MOInfoClient.get_columns(tmo_id)
    except grpc.RpcError as exc:
        status_code = 400
        if exc.code() == grpc.StatusCode.NOT_FOUND:
            status_code = 404

        raise HTTPException(status_code=status_code, detail=exc.details())

    return list(res)
