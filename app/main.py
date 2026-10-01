from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.infrastructure.logging import configure_logging
from app.interfaces.api.deps import get_engine
from app.interfaces.api.router import api_v1_router
from app.log_events import LogEvent

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info(LogEvent.API_STARTUP)
    try:
        yield
    finally:
        logger.info(LogEvent.API_SHUTDOWN)
        await get_engine().dispose()


app = FastAPI(
    title="nebus payment processing",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_v1_router)


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
