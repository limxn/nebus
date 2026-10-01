from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.application.dto.payment_dto import CreatePaymentDTO, PaymentDTO
from app.domain.payment.value_objects import Currency, PaymentStatus


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(..., gt=0)
    currency: Currency
    webhook_url: HttpUrl
    description: str | None = Field(default=None, max_length=1024)
    metadata: dict[str, object] | None = None

    def to_dto(self, idempotency_key: str) -> CreatePaymentDTO:
        return CreatePaymentDTO(
            idempotency_key=idempotency_key,
            amount=self.amount,
            currency=self.currency,
            webhook_url=str(self.webhook_url),
            description=self.description,
            metadata=self.metadata,
        )


class PaymentCreateResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime

    @classmethod
    def from_dto(cls, dto: PaymentDTO) -> PaymentCreateResponse:
        return cls(
            payment_id=dto.id,
            status=dto.status,
            created_at=dto.created_at,
        )


class PaymentDetailResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    description: str | None
    metadata: dict[str, object] | None
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None

    @classmethod
    def from_dto(cls, dto: PaymentDTO) -> PaymentDetailResponse:
        return cls(
            payment_id=dto.id,
            status=dto.status,
            amount=dto.amount,
            currency=dto.currency,
            description=dto.description,
            metadata=dto.metadata,
            webhook_url=dto.webhook_url,
            created_at=dto.created_at,
            processed_at=dto.processed_at,
        )
