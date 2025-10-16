from v3.grpc_config.mo_info_client import MOInfoClient
from v3.grpc_config.dataflow_to_dataview.proto.data_carrier_pb2 import (
    DataRequest,
)
from v3.routers.sources.sources_managers.general import ABCSourceManager


class InventorySourceManager(ABCSourceManager):
    def __init__(self, con_data: dict) -> None:
        self.tmo_id = con_data["tmo_id"]
        self.source_data_columns = con_data["source_data_columns"]

    def check_connection(self):
        pass

    def get_source_data_columns(self):
        """get list of source columns"""
        return MOInfoClient.get_columns(self.tmo_id)

    def get_columns_with_types(self) -> dict[str, str]:
        columns = MOInfoClient.get_columns_with_types(
            tmo_id=self.tmo_id, columns=self.source_data_columns
        )
        # set type for reserved columns
        columns["tmo_id"] = "int"
        columns["parent_name"] = "str"

        return columns

    def get_cleaned_columns(self):
        """get list of columns names that intersect between given and existing"""
        all_columns = self.get_source_data_columns()
        if not self.source_data_columns:
            return all_columns

        return set(all_columns).intersection(self.source_data_columns)

    def get_source_all_data(self):
        """get data"""
        columns = self.get_cleaned_columns()
        return MOInfoClient.get_data(tmo_id=self.tmo_id, columns=columns)

    def get_source_data_for_grpc(self, source_id: int):
        """Pack data to grpc object"""
        data = self.get_source_all_data()
        count = len(data)
        for item in data:
            data_row = {
                k: str(v) for k, v in dict(item).items() if v is not None
            }
            yield DataRequest(
                source_id=source_id, count=count, data_row=data_row
            )
