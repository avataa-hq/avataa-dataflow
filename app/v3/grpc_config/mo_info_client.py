import pickle

import grpc

from v3.grpc_config.config import INVENTORY_GRPC_URL
from v3.grpc_config.mo_info.mo_info_pb2 import (
    RequestMODetailsWithTPRMNames,
    RequestObjWithParamsLimited,
    RequestTPRMNameToType,
)
from v3.grpc_config.mo_info.mo_info_pb2_grpc import InformerStub


class MOInfoClient:
    @staticmethod
    def get_columns(tmo_id: int):
        with grpc.insecure_channel(f"{INVENTORY_GRPC_URL}") as channel:
            stub = InformerStub(channel)
            result = stub.GetMODetailsWithTPRMNames(
                RequestMODetailsWithTPRMNames(tmo_id=tmo_id)
            )

            return result.column

    @staticmethod
    def get_columns_with_types(tmo_id: int, columns: list[str]):
        with grpc.insecure_channel(f"{INVENTORY_GRPC_URL}") as channel:
            stub = InformerStub(channel)
            result = stub.GetTPRMNameToTypeMapper(
                RequestTPRMNameToType(tmo_id=tmo_id, columns=columns)
            )

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
            stub = InformerStub(channel)
            response = stub.GetObjWithParamsLimited(
                RequestObjWithParamsLimited(
                    tmo_id=tmo_id,
                    tprm_names=columns,
                    limit=limit,
                    offset=offset,
                )
            )
            result = []
            for res in response:
                result.append(pickle.loads(bytes.fromhex(res.data)))

        return result
