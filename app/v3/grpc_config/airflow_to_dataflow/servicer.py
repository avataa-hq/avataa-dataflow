import json

import grpc.aio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.database import engine
from v3.database.schemas import Source, Destination
from v3.grpc_config.airflow_to_dataflow.proto.airflow_to_dataflow_pb2 import (
    RequestGetSourceConfiguration,
    ResponseGetSourceConfiguration,
    RequestGetDestinationData,
    ResponseGetDestinationData,
)
from v3.grpc_config.airflow_to_dataflow.proto.airflow_to_dataflow_pb2_grpc import (
    AirflowToDataflowServicer,
)


class AirflowToDataflowManager(AirflowToDataflowServicer):
    async def GetSourceConfiguration(
        self,
        request: RequestGetSourceConfiguration,
        context: grpc.aio.ServicerContext,
    ) -> ResponseGetSourceConfiguration:
        async with AsyncSession(engine) as session:
            query = select(Source).where(Source.id == request.source_id)
            source = await session.execute(query)
            source = source.scalar()

            if not source:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Source with given id not found!")
                return context

            source_data = source.decoded_data()["con_data"]
            if source_data.get("import_type", None) == "Manual":
                if source_data.get("file_name"):
                    key_for_file_name = "file_name"
                else:
                    key_for_file_name = "filename"
                source_data[key_for_file_name] = (
                    f"{request.source_id}/{source_data[key_for_file_name]}"
                )
            return ResponseGetSourceConfiguration(
                source_data=json.dumps(source_data)
            )

    async def GetDestinationData(
        self,
        request: RequestGetDestinationData,
        context: grpc.aio.ServicerContext,
    ) -> ResponseGetDestinationData:
        async with AsyncSession(engine) as session:
            query = select(Destination).where(
                Destination.id == request.destination_id
            )
            destination = await session.execute(query)
            destination = destination.scalar()

            if not destination:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Source with given id not found!")
                return context

            destination_data = destination.decoded_data()["con_data"]
            return ResponseGetDestinationData(
                destination_data=json.dumps(destination_data)
            )
