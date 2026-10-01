from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.application.use_cases.outbox_relay import OutboxRelay
from app.domain.outbox.entity import OutboxEvent, OutboxStatus
from tests.fakes import FakeEventPublisher, FakeOutboxRepository


def _event(**overrides: object) -> OutboxEvent:
    from uuid import uuid4

    base: dict[str, object] = {
        "aggregate_id": uuid4(),
        "event_type": "payments.new",
        "payload": {"payment_id": "abc"},
    }
    base.update(overrides)
    return OutboxEvent(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_relay_publishes_pending_events() -> None:
    outbox = FakeOutboxRepository()
    publisher = FakeEventPublisher()
    event = _event()
    outbox.seed(event)

    relay = OutboxRelay(outbox=outbox, publisher=publisher)
    count = await relay.tick()

    assert count == 1
    assert publisher.count() == 1
    bodies = publisher.messages_for("payments.new")
    assert len(bodies) == 1
    payload = json.loads(bodies[0])
    assert payload["payload"] == {"payment_id": "abc"}
    assert event.status == OutboxStatus.PUBLISHED


@pytest.mark.asyncio
async def test_relay_skips_published_events() -> None:
    outbox = FakeOutboxRepository()
    publisher = FakeEventPublisher()
    outbox.seed(
        _event(
            status=OutboxStatus.PUBLISHED,
            published_at=datetime.now(UTC),
            payload={},
        )
    )

    relay = OutboxRelay(outbox=outbox, publisher=publisher)
    count = await relay.tick()

    assert count == 0
    assert publisher.count() == 0


@pytest.mark.asyncio
async def test_relay_increments_attempts_on_failure() -> None:
    outbox = FakeOutboxRepository()
    publisher = FakeEventPublisher()

    async def _boom(routing_key: str, body: bytes) -> None:
        raise RuntimeError("broker down")

    publisher.publish = _boom  # type: ignore[method-assign]

    event = _event(payload={})
    outbox.seed(event)

    relay = OutboxRelay(outbox=outbox, publisher=publisher)
    count = await relay.tick()

    assert count == 0
    assert event.attempts == 1
    assert event.status == OutboxStatus.PENDING


@pytest.mark.asyncio
async def test_relay_parks_event_after_max_attempts() -> None:
    outbox = FakeOutboxRepository()
    publisher = FakeEventPublisher()

    async def _boom(routing_key: str, body: bytes) -> None:
        raise RuntimeError("broker down")

    publisher.publish = _boom  # type: ignore[method-assign]

    event = _event(payload={}, attempts=1)
    outbox.seed(event)

    relay = OutboxRelay(outbox=outbox, publisher=publisher, max_attempts=2)
    count = await relay.tick()

    assert count == 0
    assert event.attempts == 2
    assert event.status == OutboxStatus.FAILED
