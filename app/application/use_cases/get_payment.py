from __future__ import annotations

from uuid import UUID

from app.application.dto.payment_dto import PaymentDTO
from app.application.ports.payment_repository import PaymentRepository


class GetPayment:
    def __init__(self, payments: PaymentRepository) -> None:
        self._payments = payments

    async def execute(self, payment_id: UUID) -> PaymentDTO | None:
        payment = await self._payments.get_by_id(payment_id)
        return PaymentDTO.from_domain(payment) if payment else None
