import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.schemas import SourceGroup
from v3.routers.groups.models import SourceMappingTypes
from fastapi.testclient import TestClient


URL = "/api/dataflow/v3/groups"
GROUP_DATA = {
    "name": "TEST GROUP NAME",
    "source_type": SourceMappingTypes.PM_DATA.value,
}
UPDATE_GROUP_DATA = {
    "name": "UPDATED GROUP NAME",
    "source_type": SourceMappingTypes.GEO_DATA.value,
}
RESP_JSON_EXPECTED = {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_read_group_error_not_authorized_user(
    public_client: TestClient, default_group: SourceGroup
):
    """TEST Successful GET request returns status 401 for unauthorized user"""
    resp = public_client.get(URL + "/" + str(default_group.id))
    assert resp.status_code == 401
    assert resp.json() == RESP_JSON_EXPECTED


@pytest.mark.asyncio
async def test_delete_group_error_not_authorized_user(
    public_client: TestClient, default_group: SourceGroup, session: AsyncSession
):
    """TEST Successful DELETE request returns status 401 for unauthorized user and does not delete group."""
    resp = public_client.delete(URL + "/" + str(default_group.id))
    assert resp.status_code == 401
    assert resp.json() == RESP_JSON_EXPECTED

    await session.refresh(default_group)
    assert default_group is not None


@pytest.mark.asyncio
async def test_patch_group_error_not_authorized_user(
    public_client: TestClient, default_group: SourceGroup, session: AsyncSession
):
    """TEST Successful PATCH request returns status 401 for unauthorized user and does not update group."""
    resp = public_client.patch(
        URL + "/" + str(default_group.id), json=UPDATE_GROUP_DATA
    )
    assert resp.status_code == 401
    assert resp.json() == RESP_JSON_EXPECTED

    stmt = select(SourceGroup).where(SourceGroup.id == default_group.id)
    default_group_after = await session.execute(stmt)
    default_group_after = default_group_after.scalars().first()
    assert default_group == default_group_after


@pytest.mark.asyncio
async def test_post_group_error_not_authorized_user(
    public_client: TestClient, default_group: SourceGroup, session: AsyncSession
):
    """TEST Successful POST request returns status 401 for unauthorized user and does not create new group."""
    new_name = "New Group Name"

    stmt = select(SourceGroup).where(SourceGroup.name == new_name)
    res = await session.execute(stmt)
    res = res.scalars().first()

    assert res is None

    data = dict()
    data.update(GROUP_DATA)
    data["name"] = new_name

    resp = public_client.post(URL, json=data)

    assert resp.status_code == 401
    assert resp.json() == RESP_JSON_EXPECTED

    res = await session.execute(stmt)
    res = res.scalars().first()

    assert res is None
