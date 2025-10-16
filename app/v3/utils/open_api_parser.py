from http.client import HTTPException


class OpenApiParser:
    def __init__(self, data: dict):
        self.data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if isinstance(value, dict) is False:
            raise TypeError("Value must be of type dict")
        self._value = value

    def get_all_paths(self):
        return list(self.data["paths"].keys())

    def __validate_path_exist(self, path: str):
        if path not in self.data["paths"]:
            raise HTTPException(f"Path = {path} does not exist!")

    def get_path_methods(self, path: str):
        methods = self.data["paths"].get(path)
        if not methods:
            raise HTTPException(f"Path = {path} does not exist!")
        return list(methods.keys())

    def get_path_method_variables(self, path: str):
        self.__validate_path_exist(self, path)
