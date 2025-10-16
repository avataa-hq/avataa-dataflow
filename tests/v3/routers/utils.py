from sqlalchemy.ext.asyncio import AsyncSession

from v3.database.schemas import Source


def create_and_save_in_db_source_inst(session: AsyncSession, data: dict):
    """Creates and return RESTAPI Source instance"""
    source = Source(**data)
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source
