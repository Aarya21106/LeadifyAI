from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from leadify.common.settings import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
