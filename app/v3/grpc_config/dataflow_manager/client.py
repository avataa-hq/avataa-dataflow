import json

import grpc

from v3.grpc_config.config import INVENTORY_GRPC_URL
from v3.grpc_config.dataflow_manager.proto import dataflow_manager_pb2
from v3.grpc_config.dataflow_manager.proto.dataflow_manager_pb2_grpc import (
    DataflowManagerStub,
)


class DataflowManagerClient:
    @staticmethod
    def get_columns(tmo_id: int):
        with grpc.insecure_channel(f"{INVENTORY_GRPC_URL}") as channel:
            stub = DataflowManagerStub(channel)
            result = stub.GetTPRMNamesOfTMO(
                dataflow_manager_pb2.RequestGetTPRMNamesOfTMO(tmo_id=tmo_id)
            )

            return result.column

    @staticmethod
    def get_columns_with_types(tmo_id: int, columns: list[str]):
        with grpc.insecure_channel(f"{INVENTORY_GRPC_URL}") as channel:
            stub = DataflowManagerStub(channel)
            msg = dataflow_manager_pb2.RequestGetTPRMNameToTypeMapper(
                tmo_id=tmo_id, columns=columns
            )
            result = stub.GetTPRMNameToTypeMapper(msg)

            return result.mapper

    @staticmethod
    def get_data(
        tmo_id: int,
        columns: list[str],
        limit: int = 5000,
        offset: int | None = None,
    ):
        with grpc.insecure_channel(
            f"{INVENTORY_GRPC_URL}",
            options=[
                ("grpc.max_send_message_length", 100 * 1024 * 1024),
                ("grpc.max_receive_message_length", 100 * 1024 * 1024),
            ],
        ) as channel:
            stub = DataflowManagerStub(channel)
            msg = dataflow_manager_pb2.RequestGetObjectsWithParams(
                tmo_id=tmo_id, tprm_names=columns, limit=limit, offset=offset
            )
            response = stub.GetObjectsWithParams(msg)
            result = []
            for res in response:
                result.append(json.loads(res.data))

        return result
