from pydantic import BaseModel, Field, validator

from v3.routers.destinations.enums import ConType
from v3.routers.destinations.managers.sftp import SFTPManager
from v3.routers.destinations.validation_models import SFTPConnectionModel

con_types_models = {ConType.SFTP: SFTPConnectionModel}

con_types_managers = {ConType.SFTP: SFTPManager}


class ConnectionModel(BaseModel):
    con_type: ConType
    con_data: dict

    @validator("con_data")
    def check_con_data(cls, value, values):
        model = con_types_models.get(values.get("con_type", None))
        if not model:
            raise ValueError("This connection type is not implemented!")
        model(**value)

        return value


class DestinationModel(ConnectionModel):
    name: str = Field(min_length=1)
