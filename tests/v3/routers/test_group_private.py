import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from v3.database.schemas import SourceGroup
from v3.routers.groups.models import SourceMappingTypes, SourceGroupModelInfo

URL = "/api/dataflow/v3/groups"
GROUP_DATA = {
    "name": "TEST GROUP NAME",
    "source_type": SourceMappingTypes.PM_DATA.value,
}
UPDATE_GROUP_DATA = {
    "name": "UPDATED GROUP NAME",
    "source_type": SourceMappingTypes.GEO_DATA.value,
}


@pytest.mark.asyncio
async def test_read_group_successful(
    private_client: TestClient, default_group: SourceGroup
):
    """TEST Successful read_group request returns status 200 for an authorized user"""
    resp = private_client.get(URL + "/" + str(default_group.id))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_read_group_successful_return_group_data(
    private_client: TestClient, default_group: SourceGroup
):
    """TEST Successful read_group request returns SourceGroupModelInfo data for an authorized user"""
    resp = private_client.get(URL + "/" + str(default_group.id))
    assert resp.json() == SourceGroupModelInfo(**default_group.__dict__)


@pytest.mark.asyncio
async def test_read_group_error_returns_404(private_client: TestClient):
    """TEST Raises 404 error if group with group_id does not exist for an
    authorized user"""
    resp = private_client.get(URL + "/" + str(100000000000))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_group_successful(
    private_client: TestClient,
    default_group: SourceGroup,
    session: AsyncSession,
):
    """TEST Successful delete_group request returns 204 status code for an authorized user"""
    resp = private_client.delete(URL + "/" + str(default_group.id))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_group_successful_deletes_group(
    private_client: TestClient,
    default_group: SourceGroup,
    session: AsyncSession,
):
    """TEST Successful delete_group request deletes group from db for an authorized user"""
    private_client.delete(URL + "/" + str(default_group.id))

    stmt = select(SourceGroup).where(SourceGroup.id == default_group.id)
    res = await session.execute(stmt)
    res = res.scalars().first()
    assert res is None


@pytest.mark.asyncio
async def test_delete_group_error_returns_404(private_client: TestClient):
    """TEST Raises 404 error if group with group_id does not exist for an
    authorized user"""
    resp = private_client.delete(URL + "/" + str(100000000000))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_group_successful(private_client: TestClient):
    """TEST Successful create_group request returns 201 status code for an
    authorized user"""
    res = private_client.post(URL, json=GROUP_DATA)
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_create_group_successful_request_creates_group(
    private_client: TestClient, session: AsyncSession
):
    """TEST Successful create_group request creates group for an
    authorized user"""
    stmt = select(SourceGroup).where(SourceGroup.name == GROUP_DATA["name"])
    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.scalars().first()

    assert group_from_db is None

    private_client.post(URL, json=GROUP_DATA)

    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.scalars().first()

    assert group_from_db is not None


@pytest.mark.asyncio
async def test_create_group_successful_request_returns_data(
    private_client: TestClient, session: AsyncSession
):
    """TEST Successful create_group request returns created group data (SourceGroupModelInfo) for an
    authorized user"""

    res = private_client.post(URL, json=GROUP_DATA)

    stmt = select(SourceGroup).where(SourceGroup.name == GROUP_DATA["name"])
    group_from_db = await session.execute(stmt)
    group_from_db = group_from_db.scalars().first()

    source_group_response = SourceGroupModelInfo(**group_from_db.__dict__)

    assert res.json() == source_group_response


@pytest.mark.asyncio
async def test_create_group_error_not_unique_group_name(
    private_client: TestClient, session: AsyncSession, default_group
):
    """TEST Raises error if group with this name already exists."""
    data = dict()
    data.update(GROUP_DATA)
    data["name"] = default_group.name

    res = private_client.post(URL, json=data)

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_group_error_wrong_source_type(
    private_client: TestClient, default_group
):
    """TEST Raises error if source_type not in SourceMappingTypes."""
    wrong_source_type = "WRONG"
    assert wrong_source_type not in [x.value for x in SourceMappingTypes]

    data = dict()
    data.update(GROUP_DATA)
    data["source_type"] = wrong_source_type

    res = private_client.post(URL, json=data)

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_partial_update_group_successful(
    private_client: TestClient, default_group: SourceGroup
):
    """TEST successful PATCH request returns 200 status code for an
    authorized user"""
    res = private_client.patch(
        URL + "/" + str(default_group.id), json=UPDATE_GROUP_DATA
    )

    assert res.status_code == 200


@pytest.mark.asyncio
async def test_partial_update_group_successful_updates_data(
    private_client: TestClient,
    session: AsyncSession,
    default_group: SourceGroup,
):
    """TEST successful PATCH request updates group data for an
    authorized user"""

    for k, v in UPDATE_GROUP_DATA.items():
        assert getattr(default_group, k) != v

    private_client.patch(
        URL + "/" + str(default_group.id), json=UPDATE_GROUP_DATA
    )

    await session.refresh(default_group)

    for k, v in UPDATE_GROUP_DATA.items():
        assert getattr(default_group, k) == v


@pytest.mark.asyncio
async def test_partial_update_group_successful_returns_updated_data(
    private_client: TestClient,
    session: AsyncSession,
    default_group: SourceGroup,
):
    """TEST successful PATCH request returns updated group data (SourceGroupModelInfo) for an
    authorized user"""

    for k, v in UPDATE_GROUP_DATA.items():
        assert getattr(default_group, k) != v

    res = private_client.patch(
        URL + "/" + str(default_group.id), json=UPDATE_GROUP_DATA
    )

    await session.refresh(default_group)

    assert res.json() == SourceGroupModelInfo(**default_group.__dict__)
