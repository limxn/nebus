from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

from app.application.exceptions import ConflictError
from app.application.ports.event_publisher import EventPublisher
from app.application.ports.outbox_repository import OutboxRepository
from app.application.ports.payment_repository import PaymentRepository
from app.application.ports.unit_of_work import UnitOfWork
from app.application.ports.webhook_sender import WebhookSender
from app.domain.outbox.entity import OutboxEvent, OutboxStatus
from app.domain.payment.entity import Payment
from app.domain.payment.value_objects import PaymentStatus


class FakePaymentRepository(PaymentRepository):
    def __init__(self, seed: list[Payment] | None = None) -> None:
        self._by_id: dict[UUID, Payment] = {}
        self._by_key: dict[str, Payment] = {}
        for p in seed or []:
            self._add(p)

    def _add(self, payment: Payment) -> None:
        self._by_id[payment.id] = payment
        self._by_key[payment.idempotency_key] = payment

    async def add(self, payment: Payment) -> None:
        self._add(payment)

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return self._by_id.get(payment_id)

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        return self._by_key.get(key)

    async def update(self, payment: Payment) -> None:
        self._by_id[payment.id] = payment
        self._by_key[payment.idempotency_key] = payment

    def count(self) -> int:
        return len(self._by_id)


class FakeOutboxRepository(OutboxRepository):
    def __init__(self) -> None:
        self._events: list[OutboxEvent] = []

    def seed(self, *events: OutboxEvent) -> None:
        self._events.extend(events)

    async def add(self, event: OutboxEvent) -> None:
        self._events.append(event)

    async def list_pending(self, limit: int = 100) -> list[OutboxEvent]:
        return [e for e in self._events if e.status == OutboxStatus.PENDING][:limit]

    async def mark_published(self, event_id: object) -> None:
        for event in self._events:
            if event.id == event_id:
                event.status = OutboxStatus.PUBLISHED
                event.published_at = datetime.now(UTC)

    async def increment_attempts(self, event_id: object) -> None:
        for event in self._events:
            if event.id == event_id:
                event.attempts += 1

    async def mark_failed(self, event_id: object) -> None:
        for event in self._events:
            if event.id == event_id:
                event.status = OutboxStatus.FAILED

    def count(self) -> int:
        return len(self._events)

    def event_types(self) -> tuple[str, ...]:
        return tuple(e.event_type for e in self._events)


class FakeUnitOfWork(UnitOfWork):
    def __init__(self, fail_on_commit: bool = False) -> None:
        self.committed = False
        self.rolled_back = False
        self.fail_on_commit = fail_on_commit

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rolled_back = True
            return
        if self.fail_on_commit:
            self.rolled_back = True
            raise ConflictError("simulated unique constraint violation")
        self.committed = True


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._messages: list[tuple[str, bytes]] = []
        self.lock = asyncio.Lock()

    async def publish(self, routing_key: str, body: bytes) -> None:
        async with self.lock:
            self._messages.append((routing_key, body))

    def count(self) -> int:
        return len(self._messages)

    def messages_for(self, routing_key: str) -> tuple[bytes, ...]:
        return tuple(body for rk, body in self._messages if rk == routing_key)


class FakeWebhookSender(WebhookSender):
    def __init__(self, fail: bool = False) -> None:
        self._sent: list[tuple[str, dict[str, object]]] = []
        self.fail = fail

    async def send(self, url: str, payload: dict[str, object]) -> None:
        if self.fail:
            raise RuntimeError("webhook failed")
        self._sent.append((url, payload))

    def sent_payloads(self) -> tuple[dict[str, object], ...]:
        return tuple(p for _url, p in self._sent)

    def count(self) -> int:
        return len(self._sent)


def make_pending_payment(
    *,
    amount: str = "100",
    currency: str = "USD",
    idempotency_key: str = "k",
    webhook_url: str = "https://example.com/hook",
) -> Payment:
    from datetime import UTC, datetime
    from decimal import Decimal

    from app.domain.payment.value_objects import Currency as CurrencyEnum
    from app.domain.payment.value_objects import Money

    return Payment.reconstitute(
        id=uuid4(),
        idempotency_key=idempotency_key,
        money=Money(amount=Decimal(amount), currency=CurrencyEnum(currency)),
        webhook_url=webhook_url,
        description=None,
        metadata=None,
        status=PaymentStatus.PENDING,
        created_at=datetime.now(UTC),
        processed_at=None,
    )
