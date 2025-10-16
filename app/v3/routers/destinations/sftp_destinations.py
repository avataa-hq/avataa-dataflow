from typing import Annotated

from fastapi import APIRouter, HTTPException, Body, Depends, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import get_session
from v3.database.schemas import Destination
from v3.grpc_config.dataflow_to_dataview.client import DataviewClient
from v3.routers.destinations.models.sftp import SFTPDestinationModel
from v3.routers.sources.sources_managers.file_manager import SFTPSourceManager
from v3.routers.sources.utils.exceptions import ConflictError

router = APIRouter(prefix="/sftp_destinations")


@router.post("/", tags=["Destinations: SFTP destinations"])
async def create_sftp_destination(
    destination: Annotated[SFTPDestinationModel, Body()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    destination = Destination(**destination.dict())
    session.add(destination)
    await session.commit()
    await session.refresh(destination)
    return destination.decoded_data()


@router.put("/{destination_id}", tags=["Destinations: SFTP destinations"])
async def update_destination_to_sftp(
    destination_id: Annotated[int, Path(gt=0)],
    destination: Annotated[SFTPDestinationModel, Body()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    query = select(Destination).where(Destination.id == destination_id)
    old_destination = await session.execute(query)
    old_destination = old_destination.scalar()

    if not old_destination:
        raise HTTPException(
            status_code=404, detail="Destination with this id doesn't exist!"
        )

    is_used = await DataviewClient.is_destination_used(
        destination_id=destination_id
    )
    if old_destination.con_type != destination.con_type and is_used:
        raise ConflictError("This destination is in use!")

    old_destination.con_type = destination.con_type
    old_destination.con_data = destination.con_data
    session.add(old_destination)
    await session.flush(old_destination)
    await session.commit()
    await session.refresh(old_destination)

    return old_destination.decoded_data()


@router.delete("/{destination_id}", tags=["Destinations: SFTP destinations"])
async def delete_sftp_destination(
    destination_id: Annotated[int, Path(gt=0)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    query = select(Destination).where(Destination.id == destination_id)
    old_destination = await session.execute(query)
    old_destination = old_destination.scalar()

    if not old_destination:
        raise HTTPException(
            status_code=404, detail="Destination with this id doesn't exist!"
        )

    if await DataviewClient.is_destination_used(destination_id=destination_id):
        raise ConflictError("This destination is in use!")

    await session.delete(old_destination)
    await session.commit()


@router.get("/{destination_id}", tags=["Destinations: SFTP destinations"])
async def read_files_and_directories_of_sftp_destination(
    destination_id: Annotated[int, Path(gt=0)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    query = select(Destination).where(Destination.id == destination_id)
    old_destination = await session.execute(query)
    old_destination = old_destination.scalar()

    if not old_destination:
        raise HTTPException(
            status_code=404, detail="Destination with this id doesn't exist!"
        )

    manager = SFTPSourceManager(old_destination.decoded_data())
    return manager.get_list_of_files_and_dirs()
