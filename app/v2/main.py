# from starlette.responses import RedirectResponse
from fastapi import Depends

from init_app import create_app
from services.security.security_factory import security
from settings.config import PREFIX, TITLE
from v2.routers import extract, data_sources, previews

v2_prefix = f"{PREFIX}/v2"
app = create_app(
    root_path=v2_prefix,
    title=TITLE,
    version="2",
    dependencies=[Depends(security)],
)

app.include_router(extract.router)
app.include_router(data_sources.router)
app.include_router(previews.router)


# @app.get("/", include_in_schema=False)
# def docs():
#     return RedirectResponse(url=f"{v2_prefix}/docs")
