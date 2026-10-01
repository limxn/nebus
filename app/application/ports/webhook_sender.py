from __future__ import annotations

from typing import Protocol


class WebhookSender(Protocol):
    async def send(self, url: str, payload: dict[str, object]) -> None: ...
