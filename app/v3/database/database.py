from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import Executable

from v3.config import DATABASE_URL
from v3.database.schemas import Base

engine = create_async_engine(
    DATABASE_URL, echo=False, pool_size=20, max_overflow=100
)
session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_tables():
    """Initialize tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Yields AsyncSession object"""
    async with session_maker() as session:
        yield session


async def execute(
    session: AsyncSession, query: Executable, params: dict | None = None
):
    print(query)
    print(params)
    response = await session.execute(query, params)
    return response.mappings().all()
