import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.schemas import Source, SourceGroup
from v3.routers.groups.models import SourceMappingTypes
from v3.routers.sources.models.general_model import SourceType

SOURCE_DATA = {
    "name": "Test source",
    "con_type": SourceType.DB.value,
    "con_data": dict(),
}


@pytest.fixture(scope="function", name="default_group")
async def default_group_fixture(session: AsyncSession):
    group = SourceGroup(
        name="Test group", source_type=SourceMappingTypes.PM_DATA.value
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


@pytest.mark.asyncio
async def test_creating_source_successful(
    session: AsyncSession, default_group: SourceGroup
):
    """TEST Creating Source is successful."""
    default_group = await default_group
    source = Source(**SOURCE_DATA, group_id=default_group.id)
    session.add(source)
    await session.commit()
    await session.refresh(source)
    assert source.id >= 1


@pytest.mark.asyncio
async def test_creating_source_raises_error_wrong_con_type(
    default_group: SourceGroup,
):
    """TEST Raises error if con_type not in SourceType"""
    wrong_con_type = "TEST"
    assert wrong_con_type not in [x.value for x in SourceType]

    data = dict()
    data.update(SOURCE_DATA)
    data["con_type"] = wrong_con_type

    with pytest.raises(AssertionError):
        Source(**data)


@pytest.mark.asyncio
async def test_creating_source_raises_error_source_name_not_unique(
    session: AsyncSession, default_group: SourceGroup
):
    """TEST Raises error if source name not unique across group."""
    default_group = await default_group
    source = Source(**SOURCE_DATA, group_id=default_group.id)
    session.add(source)
    await session.commit()

    source = Source(**SOURCE_DATA, group_id=default_group.id)
    session.add(source)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_creating_source_raises_cant_create_without_group(
    session: AsyncSession, default_group: SourceGroup
):
    """TEST Raises error if group_id not specified."""
    source = Source(**SOURCE_DATA)
    session.add(source)
    with pytest.raises(IntegrityError):
        await session.commit()
