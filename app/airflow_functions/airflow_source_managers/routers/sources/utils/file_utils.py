from airflow_functions.airflow_source_managers.routers.sources.models.file_model import (
    FileExtension,
)


def validate_file_extension(file_name: str):
    implemented_ext = [item.value for item in FileExtension]
    file_ext = file_name.split(".")[-1]
    if file_ext not in implemented_ext:
        raise ValueError(
            f"There are no implemented file reader for extension '.{file_ext}'."
        )
