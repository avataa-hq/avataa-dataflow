from icecream import ic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.schemas import Destination
from v3.grpc_config.dataflow_to_dataview.client import DataviewClient
from v3.routers.destinations.models.models import DestinationModel
from v3.routers.sources.utils.exceptions import (
    ResourceNotFoundError,
    ConflictError,
)


class DestinationController:
    def __init__(
        self,
        session: AsyncSession,
        destination_id: int | None = None,
        destination_model: DestinationModel | None = None,
        limit: int = 10,
        offset: int = 0,
    ):
        self.db_session = session
        self.destination_id = destination_id
        self.destination = destination_model
        self.limit = limit
        self.offset = offset

    async def get_all_destinations(self, limit: int, offset: int) -> list[dict]:
        query = select(Destination).limit(limit).offset(offset)
        destinations = await self.db_session.execute(query)
        destinations = [
            dest.decoded_data() for dest in destinations.scalars().all()
        ]

        return destinations

    async def get_destination_info(self) -> dict:
        query = select(Destination).where(Destination.id == self.destination_id)
        destination = await self.db_session.execute(query)
        destination = destination.scalar()
        if not destination:
            ic(f"Not found destination with id={self.destination_id}!")
            raise ResourceNotFoundError("Destination not exist!")

        return destination.decoded_data()

    async def create_destination(self) -> dict:
        new_destination = Destination(**self.destination.dict())
        self.db_session.add(new_destination)
        await self.db_session.commit()
        await self.db_session.refresh(new_destination)

        return new_destination.decoded_data()

    async def update_destination(self) -> dict:
        # find existing destination
        query = select(Destination).where(Destination.id == self.destination_id)
        destination = await self.db_session.execute(query)
        destination = destination.scalar()
        if not destination:
            ic(f"Not found destination with id={self.destination_id}!")
            raise ResourceNotFoundError("Destination not exist!")

        # check if destination used in Dataview MS
        if await DataviewClient.is_destination_used(self.destination_id):
            raise ConflictError("Destination is used in some pipelines!")

        # update destination info
        destination.name = self.destination.name
        destination.con_type = self.destination.con_type
        destination.con_data = self.destination.con_data

        # apply changes
        self.db_session.add(destination)
        await self.db_session.commit()
        await self.db_session.refresh(destination)

        return destination.decoded_data()

    async def delete_destination(self):
        # find existing destination
        query = select(Destination).where(Destination.id == self.destination_id)
        destination = await self.db_session.execute(query)
        destination = destination.scalar()
        if not destination:
            ic(f"Not found destination with id={self.destination_id}!")
            raise ResourceNotFoundError("Destination not exist!")

        # check if destination used in Dataview MS
        if await DataviewClient.is_destination_used(self.destination_id):
            raise ConflictError("Destination is used in some pipelines!")

        # delete destination from db
        await self.db_session.delete(destination)
        await self.db_session.commit()
