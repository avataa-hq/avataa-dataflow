import logging

import grpc

from v3.grpc_config.airflow_to_dataflow.proto.airflow_to_dataflow_pb2_grpc import (
    add_AirflowToDataflowServicer_to_server,
)
from v3.grpc_config.airflow_to_dataflow.servicer import AirflowToDataflowManager
from v3.grpc_config.dag_manager.proto.dag_manager_pb2_grpc import (
    add_DagManagerServicer_to_server,
)
from v3.grpc_config.dag_manager.servicer import DagManager


async def start_grpc_server() -> None:
    """Entry point to gRPC server"""
    server = grpc.aio.server()
    add_DagManagerServicer_to_server(DagManager(), server)
    add_AirflowToDataflowServicer_to_server(AirflowToDataflowManager(), server)
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()
