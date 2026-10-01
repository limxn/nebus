from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.outbox.entity import OutboxEvent, OutboxStatus
from app.domain.payment.entity import Payment
from app.domain.payment.value_objects import Currency, Money, PaymentStatus
from app.infrastructure.db.models import OutboxEventModel, PaymentModel


def payment_to_domain(model: PaymentModel) -> Payment:
    return Payment.reconstitute(
        id=model.id,
        idempotency_key=model.idempotency_key,
        money=Money(amount=model.amount, currency=Currency(model.currency)),
        webhook_url=model.webhook_url,
        description=model.description,
        metadata=model.metadata_json,
        status=PaymentStatus(model.status),
        created_at=model.created_at,
        processed_at=model.processed_at,
    )


def payment_from_domain(payment: Payment) -> PaymentModel:
    return PaymentModel(
        id=payment.id,
        idempotency_key=payment.idempotency_key,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata_json=payment.metadata,
        webhook_url=payment.webhook_url,
        status=payment.status,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )


def outbox_to_domain(model: OutboxEventModel) -> OutboxEvent:
    return OutboxEvent(
        id=model.id,
        aggregate_id=model.aggregate_id,
        event_type=model.event_type,
        payload=model.payload,
        status=OutboxStatus(model.status),
        created_at=model.created_at,
        published_at=model.published_at,
        attempts=model.attempts,
    )


class SqlAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, payment: Payment) -> None:
        self._session.add(payment_from_domain(payment))

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        model = result.scalar_one_or_none()
        return payment_to_domain(model) if model else None

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.idempotency_key == key)
        )
        model = result.scalar_one_or_none()
        return payment_to_domain(model) if model else None

    async def update(self, payment: Payment) -> None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.id == payment.id)
        )
        model = result.scalar_one()
        model.status = PaymentStatus(payment.status)
        model.processed_at = payment.processed_at


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> None:
        self._session.add(
            OutboxEventModel(
                id=event.id,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=event.payload,
                status=OutboxStatus(event.status),
                created_at=event.created_at,
                published_at=event.published_at,
                attempts=event.attempts,
            )
        )

    async def list_pending(self, limit: int = 100) -> list[OutboxEvent]:
        result = await self._session.execute(
            select(OutboxEventModel)
            .where(OutboxEventModel.status == OutboxStatus.PENDING)
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return [outbox_to_domain(m) for m in result.scalars().all()]

    async def mark_published(self, event_id: UUID) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(
                status=OutboxStatus.PUBLISHED,
                published_at=datetime.now(UTC),
            )
        )

    async def increment_attempts(self, event_id: UUID) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(attempts=OutboxEventModel.attempts + 1)
        )

    async def mark_failed(self, event_id: UUID) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(status=OutboxStatus.FAILED)
        )
