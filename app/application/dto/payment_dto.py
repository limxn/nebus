from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.payment.entity import Payment
from app.domain.payment.value_objects import Currency, PaymentStatus


@dataclass(frozen=True, slots=True)
class CreatePaymentDTO:
    idempotency_key: str
    amount: Decimal
    currency: Currency
    webhook_url: str
    description: str | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class PaymentDTO:
    id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    description: str | None
    metadata: dict[str, object] | None
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_domain(cls, payment: Payment) -> PaymentDTO:
        return cls(
            id=payment.id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            metadata=payment.metadata,
            webhook_url=payment.webhook_url,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": str(self.id),
                "status": self.status.value,
                "amount": str(self.amount),
                "currency": self.currency.value,
                "description": self.description,
                "metadata": self.metadata,
                "webhook_url": self.webhook_url,
                "created_at": self.created_at.isoformat(),
                "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            }
        )
