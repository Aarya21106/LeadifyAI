from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from leadify.db.session import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session, commit on success, rollback on error."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
