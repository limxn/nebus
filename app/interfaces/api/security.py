from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key is None or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
