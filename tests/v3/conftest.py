import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from v3.database.schemas import Base

ENGINE = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest_asyncio.fixture(name="session", scope="function")
async def session_fixture():
    async_session = sessionmaker(
        ENGINE, class_=AsyncSession, expire_on_commit=False
    )
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        await session.execute("pragma foreign_keys=ON")
        yield session
