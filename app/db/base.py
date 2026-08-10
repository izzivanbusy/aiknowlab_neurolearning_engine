from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Convert URL directly - bypasses property, works with any Railway scheme
_rest = settings.DATABASE_URL.split("://", 1)[1]
_async_url = "postgresql+asyncpg://" + _rest

engine = create_async_engine(_async_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSessionLocal() as session:
        yield session
