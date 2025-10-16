from fastapi import HTTPException

from v3.routers.sources.models.file_model import FileExtension


def validate_file_extension(file_name: str):
    implemented_ext = [item.value for item in FileExtension]
    file_ext = file_name.split(".")[-1]
    if file_ext not in implemented_ext:
        raise HTTPException(
            status_code=422,
            detail=f"There are no implemented file reader for extension '.{file_ext}'.",
        )
