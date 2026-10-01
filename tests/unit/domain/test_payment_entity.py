from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.payment.entity import Payment
from app.domain.payment.value_objects import Currency, Money, PaymentStatus


def _make_payment() -> Payment:
    return Payment.create(
        idempotency_key="k1",
        amount=Decimal("10"),
        currency=Currency.USD,
        webhook_url="https://example.com/hook",
    )


def test_payment_create_returns_pending() -> None:
    payment = _make_payment()
    assert payment.status is PaymentStatus.PENDING
    assert payment.processed_at is None
    assert payment.money == Money(amount=Decimal("10"), currency=Currency.USD)


def test_payment_create_rejects_non_positive_amount() -> None:
    with pytest.raises(ValueError, match="positive"):
        Payment.create(
            idempotency_key="k",
            amount=Decimal("0"),
            currency=Currency.USD,
            webhook_url="https://example.com/hook",
        )


def test_payment_mark_succeeded_sets_status_and_processed_at() -> None:
    payment = _make_payment()
    at = datetime(2025, 1, 1, tzinfo=UTC)
    payment.mark_succeeded(at)
    assert payment.status is PaymentStatus.SUCCEEDED
    assert payment.processed_at == at


def test_payment_mark_failed_sets_status_and_processed_at() -> None:
    payment = _make_payment()
    at = datetime(2025, 1, 1, tzinfo=UTC)
    payment.mark_failed(at)
    assert payment.status is PaymentStatus.FAILED
    assert payment.processed_at == at


def test_payment_double_transition_raises() -> None:
    payment = _make_payment()
    payment.mark_succeeded(datetime.now(UTC))
    with pytest.raises(ValueError):
        payment.mark_failed(datetime.now(UTC))


def test_payment_idempotency_key_must_be_unique() -> None:
    payment_a = _make_payment()
    payment_b = _make_payment()
    assert payment_a.idempotency_key == payment_b.idempotency_key
    assert payment_a.id != payment_b.id
