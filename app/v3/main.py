from fastapi import Depends
from starlette.responses import RedirectResponse

from init_app import create_app
from services.security.security_factory import security
from settings.config import PREFIX, TITLE
from v3.routers.destinations import destinations, sftp_destinations
from v3.routers.groups import groups
from v3.routers.sources import (
    sources,
    db_sources,
    api_sources,
    file_sources,
    inventory_sources,
)
from v3.routers.dags.routers import router as dags_routers
from settings import config as main_config


v3_prefix = f"{PREFIX}/v3"

if main_config.DEBUG:
    app = create_app(root_path=v3_prefix, title=TITLE, version="3")
else:
    app = create_app(
        root_path=v3_prefix,
        title=TITLE,
        version="3",
        dependencies=[Depends(security)],
    )

app.include_router(groups.router)
app.include_router(sources.router)
app.include_router(db_sources.router)
app.include_router(api_sources.router)
app.include_router(file_sources.router)
app.include_router(inventory_sources.router)
app.include_router(dags_routers)
app.include_router(destinations.router)
app.include_router(sftp_destinations.router)


@app.get("/", include_in_schema=False)
def docs():
    return RedirectResponse(url=f"{v3_prefix}/docs")
