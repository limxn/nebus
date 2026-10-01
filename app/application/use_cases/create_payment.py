from __future__ import annotations

import structlog

from app.application.dto.payment_dto import CreatePaymentDTO, PaymentDTO
from app.application.exceptions import ConflictError
from app.application.ports.outbox_repository import OutboxRepository
from app.application.ports.payment_repository import PaymentRepository
from app.application.ports.unit_of_work import UnitOfWork
from app.domain.outbox.entity import OutboxEvent
from app.domain.payment.entity import Payment
from app.log_events import LogEvent

logger = structlog.get_logger(__name__)


class CreatePayment:
    def __init__(
        self,
        payments: PaymentRepository,
        outbox: OutboxRepository,
        uow: UnitOfWork,
    ) -> None:
        self._payments = payments
        self._outbox = outbox
        self._uow = uow

    async def execute(self, data: CreatePaymentDTO) -> PaymentDTO:
        existing = await self._payments.get_by_idempotency_key(data.idempotency_key)
        if existing is not None:
            return PaymentDTO.from_domain(existing)

        payment = Payment.create(
            idempotency_key=data.idempotency_key,
            amount=data.amount,
            currency=data.currency,
            webhook_url=data.webhook_url,
            description=data.description,
            metadata=data.metadata,
        )
        event = OutboxEvent.for_payment_created(payment)

        try:
            async with self._uow:
                await self._payments.add(payment)
                await self._outbox.add(event)
        except ConflictError:
            return await self._resolve_conflict(data.idempotency_key)

        return PaymentDTO.from_domain(payment)

    async def _resolve_conflict(self, idempotency_key: str) -> PaymentDTO:
        winner = await self._payments.get_by_idempotency_key(idempotency_key)
        if winner is None:
            raise ConflictError(f"idempotency key {idempotency_key!r} is taken but not readable")
        logger.info(LogEvent.CREATE_PAYMENT_IDEMPOTENCY_CONFLICT, idempotency_key=idempotency_key)
        return PaymentDTO.from_domain(winner)
