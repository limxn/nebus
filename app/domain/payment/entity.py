from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.payment.value_objects import Currency, Money, PaymentStatus


@dataclass
class Payment:
    idempotency_key: str
    money: Money
    webhook_url: str
    description: str | None = None
    metadata: dict[str, object] | None = None
    id: UUID = field(default_factory=uuid4)
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        idempotency_key: str,
        amount: Decimal,
        currency: Currency,
        webhook_url: str,
        description: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Payment:
        money = Money(amount=amount, currency=currency)
        return cls(
            idempotency_key=idempotency_key,
            money=money,
            webhook_url=webhook_url,
            description=description,
            metadata=metadata,
        )

    @classmethod
    def reconstitute(
        cls,
        *,
        id: UUID,
        idempotency_key: str,
        money: Money,
        webhook_url: str,
        description: str | None,
        metadata: dict[str, object] | None,
        status: PaymentStatus,
        created_at: datetime,
        processed_at: datetime | None,
    ) -> Payment:
        return cls(
            id=id,
            idempotency_key=idempotency_key,
            money=money,
            webhook_url=webhook_url,
            description=description,
            metadata=metadata,
            status=status,
            created_at=created_at,
            processed_at=processed_at,
        )

    def is_pending(self) -> bool:
        return self.status is PaymentStatus.PENDING

    @property
    def amount(self) -> Decimal:
        return self.money.amount

    @property
    def currency(self) -> Currency:
        return self.money.currency

    def notification_payload(self) -> dict[str, object]:
        return {
            "payment_id": str(self.id),
            "status": self.status.value,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }

    def mark_succeeded(self, at: datetime) -> None:
        self._transition(PaymentStatus.SUCCEEDED, at)

    def mark_failed(self, at: datetime) -> None:
        self._transition(PaymentStatus.FAILED, at)

    def _transition(self, new_status: PaymentStatus, at: datetime) -> None:
        if not self.is_pending():
            raise ValueError(
                f"cannot transition payment {self.id} from {self.status} to {new_status}"
            )
        self.status = new_status
        self.processed_at = at
