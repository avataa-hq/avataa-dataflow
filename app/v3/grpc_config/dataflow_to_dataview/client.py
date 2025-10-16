import grpc

from v3.config import DATAVIEW_GRPC_URL
from v3.grpc_config.dataflow_to_dataview.proto.data_carrier_pb2 import (
    RequestIsDestinationUsed,
    ResponseIsDestinationUsed,
)
from v3.grpc_config.dataflow_to_dataview.proto.data_carrier_pb2_grpc import (
    DataCarrierStub,
)


class DataviewClient:
    @staticmethod
    def is_destination_used(destination_id: int):
        with grpc.insecure_channel(DATAVIEW_GRPC_URL) as channel:
            stub = DataCarrierStub(channel)
            msg = RequestIsDestinationUsed(destination_id=destination_id)

            response: ResponseIsDestinationUsed = stub.IsDestinationUsed(msg)
            return response.is_used
