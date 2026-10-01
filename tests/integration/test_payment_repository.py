from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.payment.entity import Payment
from app.domain.payment.value_objects import Currency
from app.infrastructure.db.repositories import SqlAlchemyPaymentRepository


def _new_payment(**overrides: object) -> Payment:
    base: dict[str, object] = {
        "idempotency_key": "k",
        "amount": Decimal("10"),
        "currency": Currency.USD,
        "webhook_url": "https://example.com/hook",
    }
    base.update(overrides)
    return Payment.create(**base)  # type: ignore[arg-type]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_and_get_by_id(
    integration_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with integration_session_factory() as session:
        repo = SqlAlchemyPaymentRepository(session)
        payment = _new_payment(
            idempotency_key="idem-add",
            amount=Decimal("42.50"),
            currency=Currency.EUR,
        )
        await repo.add(payment)
        await session.commit()

    async with integration_session_factory() as session:
        repo = SqlAlchemyPaymentRepository(session)
        loaded = await repo.get_by_id(payment.id)
        assert loaded is not None
        assert loaded.idempotency_key == "idem-add"
        assert loaded.amount == Decimal("42.50")
        assert loaded.currency is Currency.EUR


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unique_idempotency_key(
    integration_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with integration_session_factory() as session:
        repo = SqlAlchemyPaymentRepository(session)
        await repo.add(_new_payment(idempotency_key="dup", amount=Decimal("1")))
        await session.commit()

    async with integration_session_factory() as session:
        repo = SqlAlchemyPaymentRepository(session)
        await repo.add(_new_payment(idempotency_key="dup", amount=Decimal("2")))
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_status(
    integration_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from datetime import UTC, datetime

    async with integration_session_factory() as session:
        repo = SqlAlchemyPaymentRepository(session)
        payment = _new_payment(idempotency_key="upd", amount=Decimal("10"), currency=Currency.RUB)
        await repo.add(payment)
        await session.commit()

    async with integration_session_factory() as session:
        repo = SqlAlchemyPaymentRepository(session)
        loaded = await repo.get_by_id(payment.id)
        assert loaded is not None
        loaded.mark_succeeded(datetime(2025, 1, 1, tzinfo=UTC))
        await repo.update(loaded)
        await session.commit()

    async with integration_session_factory() as session:
        repo = SqlAlchemyPaymentRepository(session)
        loaded = await repo.get_by_id(payment.id)
        assert loaded is not None
        assert loaded.status.value == "succeeded"
