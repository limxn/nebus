from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.log_events import LogEvent

logger = structlog.get_logger(__name__)


class HttpxWebhookSender:
    def __init__(self, timeout: float, max_attempts: int) -> None:
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send(self, url: str, payload: dict[str, Any]) -> None:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential(multiplier=0.2, min=0.2, max=2.0),
                retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
                reraise=True,
            ):
                with attempt:
                    response = await self._client.post(url, json=payload)
                    response.raise_for_status()
                    logger.info(
                        LogEvent.WEBHOOK_SENT,
                        url=url,
                        payment_id=str(payload.get("payment_id")),
                        attempt_number=attempt.retry_state.attempt_number,
                    )
        except RetryError:
            logger.warning(
                LogEvent.WEBHOOK_EXHAUSTED_RETRIES,
                url=url,
                payment_id=str(payload.get("payment_id")),
            )
            raise
