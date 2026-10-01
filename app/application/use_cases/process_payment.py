from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

import structlog

from app.application.ports.payment_repository import PaymentRepository
from app.application.ports.webhook_sender import WebhookSender
from app.domain.payment.entity import Payment
from app.log_events import LogEvent

logger = structlog.get_logger(__name__)


class ProcessPayment:
    SUCCESS_PROBABILITY = 0.9

    def __init__(
        self,
        payments: PaymentRepository,
        webhook: WebhookSender,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        rng: Callable[[], float] = random.random,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._payments = payments
        self._webhook = webhook
        self._clock = clock
        self._rng = rng
        self._sleep = sleep

    async def execute(self, payment_id: UUID) -> None:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            logger.warning(LogEvent.PROCESS_PAYMENT_NOT_FOUND, payment_id=str(payment_id))
            return

        if not payment.is_pending():
            logger.info(
                LogEvent.PROCESS_PAYMENT_SKIP_NON_PENDING,
                payment_id=str(payment_id),
                status=payment.status,
            )
            return

        await self._sleep(self._emulated_delay())
        now = self._clock()
        succeeded = self._rng() < self.SUCCESS_PROBABILITY

        if succeeded:
            payment.mark_succeeded(now)
        else:
            payment.mark_failed(now)

        await self._payments.update(payment)

        await self._send_webhook(payment)

    async def _send_webhook(self, payment: Payment) -> None:
        try:
            await self._webhook.send(payment.webhook_url, payment.notification_payload())
        except Exception:
            logger.exception(
                LogEvent.PROCESS_PAYMENT_WEBHOOK_FAILED,
                payment_id=str(payment.id),
                webhook_url=payment.webhook_url,
            )

    def _emulated_delay(self) -> float:
        return random.uniform(0.01, 0.05)
