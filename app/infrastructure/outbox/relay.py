from __future__ import annotations

import asyncio
import contextlib
import signal

import structlog

from app.application.use_cases.outbox_relay import OutboxRelay
from app.config import get_settings
from app.infrastructure.db.base import create_engine, create_session_factory
from app.infrastructure.db.repositories import SqlAlchemyOutboxRepository
from app.infrastructure.logging import configure_logging
from app.infrastructure.messaging.broker import setup_topology
from app.infrastructure.messaging.publisher import RabbitEventPublisher
from app.log_events import LogEvent

logger = structlog.get_logger(__name__)
settings = get_settings()

MAX_PUBLISH_ATTEMPTS = 10


async def _run() -> None:
    engine = create_engine()
    session_factory = create_session_factory(engine)
    publisher = RabbitEventPublisher()

    stop_event = asyncio.Event()

    def _request_stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _request_stop)

    await setup_topology()
    logger.info(LogEvent.OUTBOX_RELAY_STARTED, interval=settings.outbox_poll_interval_seconds)

    while not stop_event.is_set():
        async with session_factory() as session:
            outbox = SqlAlchemyOutboxRepository(session)
            relay = OutboxRelay(
                outbox=outbox,
                publisher=publisher,
                max_attempts=MAX_PUBLISH_ATTEMPTS,
            )
            try:
                count = await relay.tick()
                if count:
                    logger.info(LogEvent.OUTBOX_RELAY_PUBLISHED, count=count)
                await session.commit()
            except Exception:
                logger.exception(LogEvent.OUTBOX_RELAY_TICK_FAILED)
                await session.rollback()

        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=settings.outbox_poll_interval_seconds)

    await engine.dispose()
    logger.info(LogEvent.OUTBOX_RELAY_STOPPED)


def main() -> None:
    configure_logging()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
