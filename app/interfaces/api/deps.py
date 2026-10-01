from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.use_cases.create_payment import CreatePayment
from app.application.use_cases.get_payment import GetPayment
from app.config import get_settings
from app.infrastructure.db.base import create_engine, create_session_factory
from app.infrastructure.db.repositories import (
    SqlAlchemyOutboxRepository,
    SqlAlchemyPaymentRepository,
)
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return create_engine(get_settings().database_url)


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return create_session_factory(get_engine())


async def get_session(
    factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session


async def get_create_payment_use_case(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreatePayment:
    return CreatePayment(
        payments=SqlAlchemyPaymentRepository(session),
        outbox=SqlAlchemyOutboxRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


async def get_get_payment_use_case(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GetPayment:
    return GetPayment(payments=SqlAlchemyPaymentRepository(session))
