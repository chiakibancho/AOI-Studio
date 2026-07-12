import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

_engine_kwargs = {"echo": False, "pool_pre_ping": True}
if os.environ.get("TESTING"):
    # pytest-asyncio gives each test its own event loop; pooled asyncpg
    # connections from a previous test's loop are unusable in the next one.
    _engine_kwargs = {"echo": False, "poolclass": NullPool}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
