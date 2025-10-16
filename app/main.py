from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware

from init_app import create_app
from settings.config import PREFIX
from v2.main import app as v2_app
from v3.main import app as v3_app
from services.security.security_factory import security
from settings import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("startup")
    yield


if config.DEBUG:
    app = create_app(root_path=PREFIX, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app = create_app(
        root_path=PREFIX,
        lifespan=lifespan,
        dependencies=[Depends(security)],
    )

app.mount("/v2", v2_app)
app.mount("/v3", v3_app)
