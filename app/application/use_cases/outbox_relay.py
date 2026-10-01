from __future__ import annotations

import structlog

from app.application.ports.event_publisher import EventPublisher
from app.application.ports.outbox_repository import OutboxRepository
from app.log_events import LogEvent

logger = structlog.get_logger(__name__)

PAYMENTS_EXCHANGE = "payments"
PAYMENTS_NEW_ROUTING_KEY = "payments.new"


class OutboxRelay:
    def __init__(
        self,
        outbox: OutboxRepository,
        publisher: EventPublisher,
        exchange: str = PAYMENTS_EXCHANGE,
        max_attempts: int = 10,
    ) -> None:
        self._outbox = outbox
        self._publisher = publisher
        self._exchange = exchange
        self._max_attempts = max_attempts

    async def tick(self, limit: int = 100) -> int:
        published = 0
        for event in await self._outbox.list_pending(limit=limit):
            try:
                await self._publisher.publish(
                    routing_key=event.event_type,
                    body=event.to_json().encode(),
                )
            except Exception:
                attempts = event.attempts + 1
                logger.exception(
                    LogEvent.OUTBOX_PUBLISH_FAILED,
                    event_id=str(event.id),
                    attempts=attempts,
                )
                await self._outbox.increment_attempts(event.id)
                if attempts >= self._max_attempts:
                    await self._outbox.mark_failed(event.id)
                    logger.error(
                        LogEvent.OUTBOX_PARKED_FAILED,
                        event_id=str(event.id),
                        attempts=attempts,
                    )
                continue

            await self._outbox.mark_published(event.id)
            published += 1
        return published
