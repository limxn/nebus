from __future__ import annotations

from app.application.ports.event_publisher import EventPublisher
from app.infrastructure.messaging.broker import (
    PAYMENTS_EXCHANGE_NAME,
    broker,
    payments_exchange,
    setup_topology,
)


class RabbitEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._topology_ready = False

    async def publish(self, routing_key: str, body: bytes) -> None:
        if not self._topology_ready:
            await setup_topology()
            self._topology_ready = True
        await broker.publish(
            body,
            exchange=payments_exchange,
            routing_key=routing_key,
        )


class InMemoryEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    async def publish(self, routing_key: str, body: bytes) -> None:
        self.messages.append((routing_key, body))


__all__ = ["PAYMENTS_EXCHANGE_NAME", "InMemoryEventPublisher", "RabbitEventPublisher"]
