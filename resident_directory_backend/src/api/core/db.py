from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.core.settings import settings

# Single engine for the app process.
engine = create_async_engine(settings.postgres_url, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# PUBLIC_INTERFACE
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession.

    Contract:
    - Yields a live AsyncSession bound to the configured Postgres database.
    - Commits/rollbacks are the caller's responsibility (service layer).
    - Ensures the session is closed at the end of request.
    """
    async with AsyncSessionLocal() as session:
        yield session
