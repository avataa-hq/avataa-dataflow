from copy import deepcopy

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.schemas import SourceGroup, Source

BASE_URL = "/api/dataflow/v3"
URL_AUTH_TYPES = BASE_URL + "/api_sources/auth_types"
URL_CREATE_SOURCE = BASE_URL + "/api_sources/"


BASE_DATA_CREATE_REST_API = {
    "name": "RESTAPI Router",
    "group_id": 0,
    "con_type": "RestAPI",
    "con_data": {
        "source_data_columns": ["string"],
        "entry_point": "string",
        "end_point": "string",
        "obj_name_from_resp": "string",
    },
}

BASE_DATA_UPDATE_REST_API = {
    "name": "RESTAPI Router UPdate",
    "group_id": 0,
    "con_type": "RestAPI",
    "con_data": {
        "source_data_columns": ["string update"],
        "entry_point": "string update",
        "end_point": "string update",
        "obj_name_from_resp": "string update",
    },
}

CON_DATA_BASIC_AUTH = {
    "auth_type": "Basic Authentication",
    "auth_data": {"username": "test user", "password": "test password"},
}

CON_DATA_BASIC_AUTH_UPDATE = {
    "auth_type": "Basic Authentication",
    "auth_data": {
        "username": "test user update",
        "password": "test password update",
    },
}


@pytest.mark.asyncio
async def test_get_auth_types_successful(private_client: TestClient):
    """TEST Successful GET request to URL_AUTH_TYPES returns list of implemented auth_types for RESTAPI"""
    res = private_client.get(URL_AUTH_TYPES)

    assert res.status_code == 200
    assert isinstance(res.json(), dict)


@pytest.mark.asyncio
async def test_post_restapi_source_with_basic_auth_type_successful(
    private_client: TestClient,
    default_group: SourceGroup,
    session: AsyncSession,
):
    """TEST Successful POST request creates RESTAPI Source with basic auth type"""
    data = deepcopy(BASE_DATA_CREATE_REST_API)
    data["group_id"] = default_group.id
    data["con_data"].update(CON_DATA_BASIC_AUTH)
    resp = private_client.post(URL_CREATE_SOURCE, json=data)

    assert resp.status_code == 201

    stmt = select(Source).where(
        Source.group_id == default_group.id, Source.name == data["name"]
    )
    res = await session.scalars(stmt)
    res = res.first()
    assert res is not None
