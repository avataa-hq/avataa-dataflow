import base64
import pickle
from io import BytesIO

import grpc
from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import engine
from v3.database.schemas import Source, Destination
from v3.file_server.minio_client_manager import minio_client
from v3.grpc_config.dag_manager.proto.dag_manager_pb2 import (
    ResponseSourceConData,
    RequestSourceConData,
    RequestCheckDestination,
    ResponseCheckDestination,
)
from v3.grpc_config.dag_manager.proto.dag_manager_pb2_grpc import (
    DagManagerServicer,
)
from v3.routers.sources.sources_managers.file_manager import (
    ManualFileSourceManager,
)


class DagManager(DagManagerServicer):
    async def GetSourceConData(
        self, request: RequestSourceConData, context: grpc.aio.ServicerContext
    ) -> ResponseSourceConData:
        result = {}
        async with AsyncSession(engine) as session:
            for source_id in request.sources:
                query = select(Source).where(Source.id == source_id)
                response: Result = await session.execute(query)
                response: Source = response.scalars().one()
                decoded_data = response.decoded_data()
                con_data = decoded_data.get("con_data")
                con_data["con_type"] = decoded_data.get("con_type")
                if con_data["con_type"] == "File":
                    if con_data["import_type"] == "Manual":
                        manager = ManualFileSourceManager(
                            source_id, con_data, minio_client()
                        )
                        buf = BytesIO()
                        manager.get_source_all_data().to_csv(
                            path_or_buf=buf, index=False
                        )
                        buf.seek(0)
                        content = base64.b64encode(buf.read()).decode("utf-8")
                        con_data["content"] = content
                result[source_id] = pickle.dumps(con_data).hex()

        return ResponseSourceConData(con_data=result)

    async def CheckDestination(
        self,
        request: RequestCheckDestination,
        context: grpc.aio.ServicerContext,
    ) -> ResponseCheckDestination | grpc.aio.ServicerContext:
        async with AsyncSession(engine) as session:
            query = select(Destination).where(
                Destination.id == request.destination_id
            )
            destination = await session.execute(query)
            destination = destination.scalar()
            if not destination:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Destination not found!")
                return context

            print(request.con_type)
            print(destination.con_type)
            if destination.con_type != request.con_type:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Connection type is not match!")
                return context

            return ResponseCheckDestination()
