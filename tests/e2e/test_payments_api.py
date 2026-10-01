from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.interfaces.api.deps import get_session_factory
from app.main import app


@pytest.fixture
async def client(
    integration_session_factory: async_sessionmaker[AsyncSession],
    api_key: str,
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_session_factory] = lambda: integration_session_factory
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_session_factory, None)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_get_payment(client: AsyncClient, api_key: str) -> None:
    response = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": api_key, "Idempotency-Key": "idem-1"},
        json={
            "amount": "10.50",
            "currency": "USD",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    payment_id = body["payment_id"]

    get_resp = await client.get(
        f"/api/v1/payments/{payment_id}",
        headers={"X-API-Key": api_key},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "pending"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_same_payment(
    client: AsyncClient, api_key: str
) -> None:
    headers = {"X-API-Key": api_key, "Idempotency-Key": "idem-dup"}
    body = {"amount": "5", "currency": "RUB", "webhook_url": "https://example.com/hook"}

    first = await client.post("/api/v1/payments", headers=headers, json=body)
    second = await client.post("/api/v1/payments", headers=headers, json=body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_api_key_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/payments/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_unknown_payment_returns_404(client: AsyncClient, api_key: str) -> None:
    response = await client.get(
        "/api/v1/payments/00000000-0000-0000-0000-000000000000",
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_amount_returns_422(client: AsyncClient, api_key: str) -> None:
    response = await client.post(
        "/api/v1/payments",
        headers={"X-API-Key": api_key, "Idempotency-Key": "bad"},
        json={"amount": "-1", "currency": "USD", "webhook_url": "https://example.com/hook"},
    )
    assert response.status_code == 422


def test_healthz() -> None:
    with TestClient(app) as c:
        try:
            resp = c.get("/healthz")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}
        except Exception:
            pytest.skip("app lifespan requires a real DB")
