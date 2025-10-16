from typing import Annotated

from fastapi import APIRouter, Depends, Query, Path, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import get_session
from v3.routers.destinations.controller import DestinationController
from v3.routers.destinations.examples.con_data import con_data_examples
from v3.routers.destinations.examples.destinations import destinations_examples
from v3.routers.destinations.models.models import (
    DestinationModel,
    ConnectionModel,
    con_types_managers,
)
from v3.routers.sources.utils.exceptions import SourceConnectionError

router = APIRouter(prefix="/destinations", tags=["Remote destinations"])


@router.get("/")
async def get_all_destinations(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(gt=0)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    controller = DestinationController(session=session)
    return await controller.get_all_destinations(limit=limit, offset=offset)


@router.get("/{destination_id}")
async def get_destination_info(
    session: Annotated[AsyncSession, Depends(get_session)],
    destination_id: Annotated[int, Path(gt=0)],
):
    controller = DestinationController(
        session=session, destination_id=destination_id
    )
    return await controller.get_destination_info()


@router.post("/")
async def create_destination(
    session: Annotated[AsyncSession, Depends(get_session)],
    destination_model: Annotated[
        DestinationModel, Body(examples=destinations_examples)
    ],
):
    controller = DestinationController(
        session=session, destination_model=destination_model
    )
    return await controller.create_destination()


@router.put("/{destination_id}")
async def update_destination(
    session: Annotated[AsyncSession, Depends(get_session)],
    destination_id: Annotated[int, Path(gt=0)],
    destination_model: Annotated[
        DestinationModel, Body(examples=destinations_examples)
    ],
):
    controller = DestinationController(
        session=session,
        destination_id=destination_id,
        destination_model=destination_model,
    )
    return await controller.update_destination()


@router.delete("/{destination_id}")
async def delete_destination(
    session: Annotated[AsyncSession, Depends(get_session)],
    destination_id: Annotated[int, Path(gt=0)],
):
    controller = DestinationController(
        session=session, destination_id=destination_id
    )
    return await controller.delete_destination()


@router.post("/check_connection")
def check_connection(
    con_data: Annotated[ConnectionModel, Body(examples=con_data_examples)],
):
    manager_class = con_types_managers.get(con_data.con_type)
    if not manager_class:
        raise HTTPException(
            status_code=422, detail="Unsupported connection type!"
        )

    manager = manager_class(con_data.dict()["con_data"])
    try:
        manager.check_connection()
    except SourceConnectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/listdir")
def get_list_of_dirs_and_files(
    con_data: Annotated[ConnectionModel, Body(examples=con_data_examples)],
):
    manager_class = con_types_managers.get(con_data.con_type)
    if not manager_class:
        raise HTTPException(
            status_code=422, detail="Unsupported connection type!"
        )

    manager = manager_class(con_data.dict()["con_data"])
    try:
        manager.listdir()
    except SourceConnectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NotImplementedError:
        raise HTTPException(
            status_code=422,
            detail="Given connection type doesn't support this operation!",
        )
