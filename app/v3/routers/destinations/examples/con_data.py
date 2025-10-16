from v3.routers.destinations.enums import ConType
from v3.routers.destinations.models.models import ConnectionModel

sftp_con_example = {
    "summary": "SFTP connection",
    "description": "SFTP connection example",
    "value": ConnectionModel(
        **{
            "con_type": ConType.SFTP,
            "con_data": {
                "host": "localhost",
                "port": 22,
                "login": "username",
                "password": "password",
                "path": "/",
            },
        }
    ),
}

con_data_examples = {ConType.SFTP: sftp_con_example}
