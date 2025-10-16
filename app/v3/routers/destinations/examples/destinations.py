from v3.routers.destinations.enums import ConType
from v3.routers.destinations.models.models import DestinationModel

sftp_dest_example = {
    "summary": "SFTP destination",
    "description": "Example for SFTP destination",
    "value": DestinationModel(
        **{
            "name": "SFTP destination",
            "con_type": ConType.SFTP,
            "con_data": {
                "host": "localhost",
                "port": "22",
                "login": "username",
                "password": "password",
                "path": "/",
            },
        }
    ),
}

destinations_examples = {
    ConType.SFTP: sftp_dest_example,
}
