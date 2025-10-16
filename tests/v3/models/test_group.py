import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.schemas import SourceGroup
from v3.routers.groups.models import SourceMappingTypes

SOURCE_GROUP_DATA = {"name": 0, "source_type": SourceMappingTypes.PM_DATA.value}


@pytest.mark.asyncio
async def test_creating_group_is_successful(session: AsyncSession):
    """Test creating SourceGroup is successful."""

    group = SourceGroup(**SOURCE_GROUP_DATA)
    session.add(group)
    await session.commit()

    await session.refresh(group)
    assert group.id >= 1


@pytest.mark.asyncio
async def test_creating_group_raises_error_name_exist(session: AsyncSession):
    """Test Raises error if creating SourceGroup name is not unique."""

    group = SourceGroup(**SOURCE_GROUP_DATA)
    group2 = SourceGroup(**SOURCE_GROUP_DATA)

    session.add(group)
    session.add(group2)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_creating_group_raises_error_wrong_source_type(
    session: AsyncSession,
):
    """Test Raises error if source_type not in SourceMappingTypes."""
    wrong_source_type = "Some"
    assert wrong_source_type not in [x.value for x in SourceMappingTypes]
    group = SourceGroup(**SOURCE_GROUP_DATA)
    with pytest.raises(AssertionError):
        group.source_type = wrong_source_type
