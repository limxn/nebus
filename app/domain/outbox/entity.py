from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from app.domain.payment.entity import Payment


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


EVENT_TYPE_PAYMENT_CREATED = "payments.new"


@dataclass
class OutboxEvent:
    aggregate_id: UUID
    event_type: str
    payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    status: OutboxStatus = OutboxStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None
    attempts: int = 0

    @classmethod
    def for_payment_created(cls, payment: Payment) -> OutboxEvent:
        return cls(
            aggregate_id=payment.id,
            event_type=EVENT_TYPE_PAYMENT_CREATED,
            payload={
                "payment_id": str(payment.id),
                "idempotency_key": payment.idempotency_key,
            },
        )

    def mark_published(self, at: datetime) -> None:
        self.status = OutboxStatus.PUBLISHED
        self.published_at = at
        self.attempts += 1

    def mark_attempt_failed(self) -> None:
        self.attempts += 1

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": str(self.id),
                "aggregate_id": str(self.aggregate_id),
                "event_type": self.event_type,
                "payload": self.payload,
            },
            default=str,
        )

    @classmethod
    def from_json(cls, raw: str) -> OutboxEvent:
        data = json.loads(raw)
        return cls(
            id=UUID(data["id"]),
            aggregate_id=UUID(data["aggregate_id"]),
            event_type=data["event_type"],
            payload=data["payload"],
        )
