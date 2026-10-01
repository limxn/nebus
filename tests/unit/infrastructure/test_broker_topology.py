from __future__ import annotations

from app.infrastructure.messaging import broker as broker_module


def test_dlq_is_dead_letter_target_of_main_queue() -> None:
    arguments = broker_module.payments_new_queue.arguments
    assert arguments["x-dead-letter-exchange"] == broker_module.DLX_EXCHANGE_NAME


def test_retry_queues_dead_letter_back_to_payments_exchange() -> None:
    assert len(broker_module.retry_queues) == broker_module.settings.max_retry_attempts - 1
    for queue in broker_module.retry_queues:
        assert queue.arguments["x-dead-letter-exchange"] == broker_module.PAYMENTS_EXCHANGE_NAME
        assert (
            queue.arguments["x-dead-letter-routing-key"] == broker_module.PAYMENTS_NEW_ROUTING_KEY
        )


def test_retry_delays_grow_exponentially() -> None:
    assert broker_module.retry_delay_ms(0) == 1000
    assert broker_module.retry_delay_ms(1) == 2000
    assert broker_module.retry_delay_ms(2) == 4000


def test_dlq_routing_key_matches_main_queue() -> None:
    assert broker_module.payments_new_dlq.routing_key == broker_module.PAYMENTS_NEW_ROUTING_KEY
