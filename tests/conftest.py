from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.infrastructure.db.base import Base


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def api_key() -> str:
    settings = get_settings()
    return settings.api_key


@pytest.fixture
async def integration_engine() -> AsyncIterator[AsyncEngine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_async_engine(url, future=True, pool_pre_ping=True)
    else:
        try:
            from testcontainers.postgres import PostgresContainer
        except ImportError:
            pytest.skip("testcontainers not available")

        container = PostgresContainer("postgres:16-alpine")
        container.start()
        url = container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(url, future=True, pool_pre_ping=True)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def integration_session_factory(
    integration_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    factory = async_sessionmaker(integration_engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
