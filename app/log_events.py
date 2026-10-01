from __future__ import annotations

from enum import StrEnum


class LogEvent(StrEnum):
    API_STARTUP = "api.startup"
    API_SHUTDOWN = "api.shutdown"

    CREATE_PAYMENT_IDEMPOTENCY_CONFLICT = "create_payment.idempotency_conflict"

    PROCESS_PAYMENT_NOT_FOUND = "process_payment.not_found"
    PROCESS_PAYMENT_SKIP_NON_PENDING = "process_payment.skip_non_pending"
    PROCESS_PAYMENT_WEBHOOK_FAILED = "process_payment.webhook_failed"

    OUTBOX_PUBLISH_FAILED = "outbox.publish_failed"
    OUTBOX_PARKED_FAILED = "outbox.parked_failed"

    OUTBOX_RELAY_STARTED = "outbox_relay.started"
    OUTBOX_RELAY_PUBLISHED = "outbox_relay.published"
    OUTBOX_RELAY_TICK_FAILED = "outbox_relay.tick_failed"
    OUTBOX_RELAY_STOPPED = "outbox_relay.stopped"

    CONSUMER_MISSING_PAYMENT_ID = "consumer.missing_payment_id"
    CONSUMER_INVALID_JSON = "consumer.invalid_json"
    CONSUMER_DLQ = "consumer.dlq"
    CONSUMER_RETRY = "consumer.retry"
    CONSUMER_STARTED = "consumer.started"
    CONSUMER_STOPPED = "consumer.stopped"

    WEBHOOK_SENT = "webhook.sent"
    WEBHOOK_EXHAUSTED_RETRIES = "webhook.exhausted_retries"
