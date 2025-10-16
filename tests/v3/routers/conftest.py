import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from main import app, v3_app
from security import oauth2_scheme
from v3.database import database
from v3.database.schemas import SourceGroup
from v3.routers.groups.models import SourceMappingTypes


@pytest_asyncio.fixture(name="private_client")
async def private_client_fixture(session: AsyncSession):
    def get_session_override():
        return session

    def get_oauth2_scheme_overwrite():
        return True

    app.dependency_overrides[oauth2_scheme] = get_oauth2_scheme_overwrite
    v3_app.dependency_overrides[oauth2_scheme] = get_oauth2_scheme_overwrite

    app.dependency_overrides[database.get_session] = get_session_override
    v3_app.dependency_overrides[database.get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    v3_app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="public_client")
async def public_client_fixture(session: AsyncSession):
    def get_session_override():
        return session

    app.dependency_overrides[database.get_session] = get_session_override
    v3_app.dependency_overrides[database.get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    v3_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function", name="default_group")
async def default_group_fixture(session: AsyncSession):
    group = SourceGroup(
        name="Test group", source_type=SourceMappingTypes.PM_DATA.value
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group
