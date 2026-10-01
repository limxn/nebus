from __future__ import annotations

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.config import get_settings

settings = get_settings()

PAYMENTS_EXCHANGE_NAME = "payments"
DLX_EXCHANGE_NAME = "payments.dlx"
PAYMENTS_NEW_QUEUE_NAME = "payments.new"
PAYMENTS_NEW_DLQ_NAME = "payments.new.dlq"
RETRY_QUEUE_PREFIX = "payments.new.retry"

PAYMENTS_NEW_ROUTING_KEY = "payments.new"


def retry_delay_ms(attempt: int) -> int:
    return int(settings.retry_base_delay_seconds * (2**attempt) * 1000)


payments_exchange = RabbitExchange(PAYMENTS_EXCHANGE_NAME, type=ExchangeType.TOPIC, durable=True)
dlx_exchange = RabbitExchange(DLX_EXCHANGE_NAME, type=ExchangeType.TOPIC, durable=True)


payments_new_queue = RabbitQueue(
    name=PAYMENTS_NEW_QUEUE_NAME,
    durable=True,
    routing_key=PAYMENTS_NEW_ROUTING_KEY,
    arguments={"x-dead-letter-exchange": DLX_EXCHANGE_NAME},
)


payments_new_dlq = RabbitQueue(
    name=PAYMENTS_NEW_DLQ_NAME,
    durable=True,
    routing_key=PAYMENTS_NEW_ROUTING_KEY,
)


retry_queues = [
    RabbitQueue(
        name=f"{RETRY_QUEUE_PREFIX}.{attempt}",
        durable=True,
        routing_key=f"{RETRY_QUEUE_PREFIX}.{attempt}",
        arguments={
            "x-message-ttl": retry_delay_ms(attempt),
            "x-dead-letter-exchange": PAYMENTS_EXCHANGE_NAME,
            "x-dead-letter-routing-key": PAYMENTS_NEW_ROUTING_KEY,
        },
    )
    for attempt in range(max(settings.max_retry_attempts - 1, 0))
]


broker = RabbitBroker(settings.rabbitmq_url)


async def setup_topology() -> None:
    await broker.connect()
    await broker.declare_exchange(payments_exchange)
    await broker.declare_exchange(dlx_exchange)

    dlq = await broker.declare_queue(payments_new_dlq)
    await dlq.bind(DLX_EXCHANGE_NAME, routing_key=PAYMENTS_NEW_ROUTING_KEY)

    for queue in retry_queues:
        declared = await broker.declare_queue(queue)
        await declared.bind(PAYMENTS_EXCHANGE_NAME, routing_key=queue.routing_key)
