from enum import Enum
from typing import List
import grpc
import sqlalchemy.exc
from fastapi import HTTPException

from v3.grpc_config.dataflow_to_dataview.proto import (
    data_carrier_pb2_grpc,
    data_carrier_pb2,
)
from v3.config import DATAVIEW_MANAGER_HOST, DATAVIEW_MANAGER_GRPC_PORT
from v3.database.schemas import SourceGroup, Source
from v3.grpc_config.dataflow_to_dataview.proto.data_carrier_pb2 import (
    DataRequest,
)
from v3.routers.sources.sources_managers.utils import get_source_manager
from v3.routers.sources.utils.exceptions import InternalError, CustomException


class GRPCResponseStatus(Enum):
    ERROR = "ERROR"
    OK = "OK"


def crete_source_group(group_id: int, group_name: str):
    """Creates group in MS DATAVIEW MANAGER, otherwise raises error"""
    with grpc.insecure_channel(
        f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
    ) as channel:
        stub = data_carrier_pb2_grpc.DataCarrierStub(channel)
        request = data_carrier_pb2.GroupRequest(
            group_id=group_id, name=group_name
        )
        response = stub.CreateSourceGroup(request)

        if response.status == GRPCResponseStatus.ERROR.value:
            raise ValueError(response.message)


def create_source(group_id: int, source_id: int, source_name: str):
    """Creates source in MS DATAVIEW MANAGER, otherwise raises error"""
    with grpc.insecure_channel(
        f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
    ) as channel:
        stub = data_carrier_pb2_grpc.DataCarrierStub(channel)
        request = data_carrier_pb2.SourceRequest(
            source_id=source_id, group_id=group_id, name=source_name
        )
        response = stub.CreateSource(request)
        if response.status == GRPCResponseStatus.ERROR.value:
            raise ValueError(response.message)


def config_source(source_id: int, columns: List):
    """Set source columns names for further import data into MS DATAVIEW MANAGER"""
    with grpc.insecure_channel(
        f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
    ) as channel:
        stub = data_carrier_pb2_grpc.DataCarrierStub(channel)
        request = data_carrier_pb2.ConfigRequest(
            source_id=source_id, columns=columns
        )
        response = stub.ConfigSource(request)

        if response.status == GRPCResponseStatus.ERROR.value:
            raise ValueError(response.message)


def config_source_with_types(source_id: int, columns: dict[str, str]):
    with grpc.insecure_channel(
        f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
    ) as channel:
        stub = data_carrier_pb2_grpc.DataCarrierStub(channel)
        response = stub.ConfigSourceWithTypes(
            data_carrier_pb2.ConfigWithTypesRequest(
                source_id=source_id, columns=columns
            )
        )

        if response.status == GRPCResponseStatus.ERROR.value:
            raise ValueError(response.message)


def load_data_into_dataview_manager(request_iterator: list[DataRequest]):
    """Load data into MS DATAVIEW MANAGER"""
    try:
        with grpc.insecure_channel(
            f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
        ) as channel:
            stub = data_carrier_pb2_grpc.DataCarrierStub(channel)
            response_future = stub.InsertData.future(request_iterator)
            response = response_future.result()
            if response.status == GRPCResponseStatus.ERROR.value:
                raise ValueError(response.message)
    except grpc.RpcError as exc:
        if exc.details() == "Exception iterating requests!":
            raise HTTPException(
                status_code=422,
                detail="No data were provided! Check data source contains data or check configuration to be correct!",
            )
        else:
            raise exc


def load_data_process(group: SourceGroup, source: Source):
    create_source(group.id, source.id, source.name)

    source_manager = get_source_manager(source)
    con_data = source.decoded_data().get("con_data")
    try:
        columns_with_types = source_manager.get_columns_with_types()
        config_source_with_types(
            source_id=source.id, columns=columns_with_types
        )
    except NotImplementedError:
        columns = con_data.get("source_data_columns")
        if not columns:
            columns = source_manager.get_source_data_columns()

        config_source(source.id, columns)
    except InternalError as exc:
        raise HTTPException(
            status_code=500, detail="Something went wrong..."
        ) from exc
    except (
        grpc.RpcError,
        sqlalchemy.exc.OperationalError,
        CustomException,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc.details()))

    res = source_manager.get_source_data_for_grpc(source.id)
    load_data_into_dataview_manager(res)


def delete_group_in_dataview_manager(group_id: int):
    """Deletes group in DATAVIEW MANAGER"""
    with grpc.insecure_channel(
        f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
    ) as channel:
        stub = data_carrier_pb2_grpc.DataCarrierStub(channel)
        request = data_carrier_pb2.GroupDeleteRequest(group_id=group_id)
        response = stub.DeleteGroup(request)

        if response.status == GRPCResponseStatus.ERROR.value:
            raise ValueError(response.message)


def delete_source_in_dataview_manager(source_id: int):
    """Deletes source in DATAVIEW MANAGER"""
    with grpc.insecure_channel(
        f"{DATAVIEW_MANAGER_HOST}:{DATAVIEW_MANAGER_GRPC_PORT}"
    ) as channel:
        stub = data_carrier_pb2_grpc.DataCarrierStub(channel)
        request = data_carrier_pb2.SourceDeleteRequest(source_id=source_id)
        response = stub.DeleteSource(request)

        if response.status == GRPCResponseStatus.ERROR.value:
            raise ValueError(response.message)
