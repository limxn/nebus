from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.dto.payment_dto import CreatePaymentDTO
from app.application.use_cases.create_payment import CreatePayment
from app.domain.payment.value_objects import Currency, PaymentStatus
from tests.fakes import FakeOutboxRepository, FakePaymentRepository, FakeUnitOfWork


@pytest.mark.asyncio
async def test_create_payment_persists_payment_and_outbox_event() -> None:
    payments = FakePaymentRepository()
    outbox = FakeOutboxRepository()
    uow = FakeUnitOfWork()
    use_case = CreatePayment(payments, outbox, uow)

    result = await use_case.execute(
        CreatePaymentDTO(
            idempotency_key="key-1",
            amount=Decimal("100"),
            currency=Currency.USD,
            webhook_url="https://example.com/hook",
        )
    )

    assert result.status == PaymentStatus.PENDING
    assert await payments.get_by_id(result.id) is not None
    assert payments.count() == 1
    assert outbox.count() == 1
    assert outbox.event_types() == ("payments.new",)
    assert uow.committed is True


@pytest.mark.asyncio
async def test_create_payment_is_idempotent() -> None:
    payments = FakePaymentRepository()
    outbox = FakeOutboxRepository()
    uow = FakeUnitOfWork()
    use_case = CreatePayment(payments, outbox, uow)
    data = CreatePaymentDTO(
        idempotency_key="same-key",
        amount=Decimal("50"),
        currency=Currency.EUR,
        webhook_url="https://example.com/hook",
    )

    first = await use_case.execute(data)
    second = await use_case.execute(data)

    assert first.id == second.id
    assert payments.count() == 1
    assert outbox.count() == 1


@pytest.mark.asyncio
async def test_create_payment_resolves_unique_constraint_conflict() -> None:
    payments = FakePaymentRepository()
    outbox = FakeOutboxRepository()
    uow = FakeUnitOfWork(fail_on_commit=True)
    use_case = CreatePayment(payments, outbox, uow)

    result = await use_case.execute(
        CreatePaymentDTO(
            idempotency_key="race-key",
            amount=Decimal("100"),
            currency=Currency.USD,
            webhook_url="https://example.com/hook",
        )
    )

    assert result.id is not None
    assert uow.committed is False
    assert uow.rolled_back is True
    assert payments.count() == 1
