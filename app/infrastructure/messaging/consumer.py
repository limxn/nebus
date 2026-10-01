from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import structlog
from faststream import FastStream
from faststream.rabbit import RabbitMessage

from app.application.use_cases.process_payment import ProcessPayment
from app.config import get_settings
from app.infrastructure.db.base import create_engine, create_session_factory
from app.infrastructure.db.repositories import SqlAlchemyPaymentRepository
from app.infrastructure.logging import configure_logging
from app.infrastructure.messaging.broker import (
    PAYMENTS_NEW_ROUTING_KEY,
    broker,
    dlx_exchange,
    payments_exchange,
    payments_new_queue,
    retry_queues,
    setup_topology,
)
from app.infrastructure.webhook.httpx_sender import HttpxWebhookSender
from app.log_events import LogEvent

logger = structlog.get_logger(__name__)
settings = get_settings()

RETRY_HEADER = "x-retry-count"

_engine = create_engine()
_session_factory = create_session_factory(_engine)
_webhook = HttpxWebhookSender(
    timeout=settings.webhook_timeout_seconds,
    max_attempts=settings.webhook_max_attempts,
)


async def _process_message(message_body: dict[str, Any]) -> None:
    payload = message_body.get("payload") or message_body
    payment_id_str = payload.get("payment_id") if isinstance(payload, dict) else None
    if not payment_id_str:
        logger.warning(LogEvent.CONSUMER_MISSING_PAYMENT_ID, body=message_body)
        return

    async with _session_factory() as session:
        payments = SqlAlchemyPaymentRepository(session)
        use_case = ProcessPayment(
            payments=payments,
            webhook=_webhook,
        )
        try:
            await use_case.execute(payment_id=uuid.UUID(payment_id_str))
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _retry_or_dlq(
    raw_body: bytes,
    headers: Mapping[str, Any],
    exc: Exception,
    retry_count: int,
) -> None:
    if retry_count >= settings.max_retry_attempts - 1:
        logger.warning(
            LogEvent.CONSUMER_DLQ,
            retry_count=retry_count,
            error=str(exc),
        )
        await broker.publish(
            raw_body,
            exchange=dlx_exchange,
            routing_key=PAYMENTS_NEW_ROUTING_KEY,
        )
        return

    retry_queue = retry_queues[retry_count]
    logger.info(
        LogEvent.CONSUMER_RETRY,
        retry_count=retry_count,
        delay_seconds=settings.retry_base_delay_seconds * (2**retry_count),
        error=str(exc),
    )

    new_headers = dict(headers)
    new_headers[RETRY_HEADER] = retry_count + 1
    await broker.publish(
        raw_body,
        exchange=payments_exchange,
        routing_key=retry_queue.routing_key,
        headers=new_headers,
    )


@broker.subscriber(
    payments_new_queue,
    exchange=payments_exchange,
)
async def handle_payment_new(msg: RabbitMessage) -> None:
    raw_body: bytes = bytes(msg.body)
    headers: dict[str, Any] = dict(msg.headers or {})
    retry_count = int(headers.get(RETRY_HEADER, 0))

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning(LogEvent.CONSUMER_INVALID_JSON, raw=raw_body)
        return

    try:
        await _process_message(body)
    except Exception as exc:
        await _retry_or_dlq(raw_body, headers, exc, retry_count)


@asynccontextmanager
async def _lifespan() -> AsyncIterator[None]:
    configure_logging()
    await setup_topology()
    logger.info(LogEvent.CONSUMER_STARTED)
    try:
        yield
    finally:
        await _webhook.aclose()
        await _engine.dispose()
        logger.info(LogEvent.CONSUMER_STOPPED)


app = FastStream(broker, lifespan=_lifespan)
