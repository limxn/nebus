from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PaymentCreatedEvent:
    payment_id: UUID
    idempotency_key: str
    amount: str
    currency: str
    webhook_url: str
    created_at: datetime
