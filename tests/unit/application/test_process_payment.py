from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest

from app.application.use_cases.process_payment import ProcessPayment
from tests.fakes import FakePaymentRepository, FakeWebhookSender, make_pending_payment


def _fixed_clock() -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC)


async def _noop_sleep(_delay: float) -> None:
    return None


@pytest.mark.asyncio
async def test_process_payment_marks_succeeded_and_sends_webhook() -> None:
    pending = make_pending_payment()
    payments = FakePaymentRepository(seed=[pending])
    webhook = FakeWebhookSender()
    use_case = ProcessPayment(
        payments=payments,
        webhook=webhook,
        clock=_fixed_clock,
        rng=lambda: 0.5,
        sleep=_noop_sleep,
    )

    await use_case.execute(payment_id=pending.id)

    updated = await payments.get_by_id(pending.id)
    assert updated is not None
    assert updated.status.value == "succeeded"
    assert updated.processed_at == _fixed_clock()
    assert webhook.count() == 1
    sent = webhook.sent_payloads()
    assert sent[0]["status"] == "succeeded"
    assert sent[0]["payment_id"] == str(pending.id)


@pytest.mark.asyncio
async def test_process_payment_marks_failed_when_rng_above_threshold() -> None:
    pending = make_pending_payment()
    payments = FakePaymentRepository(seed=[pending])
    webhook = FakeWebhookSender()
    use_case = ProcessPayment(
        payments=payments,
        webhook=webhook,
        clock=_fixed_clock,
        rng=lambda: 0.95,
        sleep=_noop_sleep,
    )

    await use_case.execute(payment_id=pending.id)

    updated = await payments.get_by_id(pending.id)
    assert updated is not None
    assert updated.status.value == "failed"
    sent = webhook.sent_payloads()
    assert sent[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_process_payment_is_idempotent_for_already_processed() -> None:
    pending = make_pending_payment()
    pending.mark_succeeded(_fixed_clock())
    payments = FakePaymentRepository(seed=[pending])
    webhook = FakeWebhookSender()
    use_case = ProcessPayment(
        payments=payments,
        webhook=webhook,
        clock=_fixed_clock,
        rng=lambda: 0.5,
        sleep=_noop_sleep,
    )

    await use_case.execute(payment_id=pending.id)

    assert webhook.count() == 0


@pytest.mark.asyncio
async def test_process_payment_swallows_webhook_failure() -> None:
    pending = make_pending_payment()
    payments = FakePaymentRepository(seed=[pending])
    webhook = FakeWebhookSender(fail=True)
    use_case = ProcessPayment(
        payments=payments,
        webhook=webhook,
        clock=_fixed_clock,
        rng=lambda: 0.5,
        sleep=_noop_sleep,
    )

    await use_case.execute(payment_id=pending.id)

    updated = await payments.get_by_id(pending.id)
    assert updated is not None
    assert updated.status.value == "succeeded"


@pytest.mark.asyncio
async def test_process_payment_does_nothing_when_payment_missing() -> None:
    import uuid

    payments = FakePaymentRepository()
    webhook = FakeWebhookSender()
    use_case = ProcessPayment(
        payments=payments,
        webhook=webhook,
        clock=_fixed_clock,
        rng=lambda: 0.5,
        sleep=_noop_sleep,
    )

    await use_case.execute(payment_id=uuid.uuid4())
    assert webhook.count() == 0


def _ensure_sleep_type() -> None:
    default_sleep: Callable[[float], Awaitable[None]] = ProcessPayment()._sleep  # type: ignore[attr-defined]
    _ = default_sleep
