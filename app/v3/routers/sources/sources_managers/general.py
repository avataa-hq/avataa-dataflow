from abc import abstractmethod, ABC


class ABCSourceManager(ABC):
    @abstractmethod
    def check_connection(self):
        """Checks if connection is available."""
        pass

    @abstractmethod
    def get_source_data_columns(self):
        pass

    @abstractmethod
    def get_columns_with_types(self) -> dict[str, str]:
        pass

    @abstractmethod
    def get_cleaned_columns(self):
        pass

    @abstractmethod
    def get_source_all_data(self):
        pass

    @abstractmethod
    def get_source_data_for_grpc(self, source_id: int):
        pass

    # @abstractmethod
    # def check_data_loading(self):
    #     """Checks if data download is available."""
    #     pass
