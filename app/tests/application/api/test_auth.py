"""Tests for auth exchange flow: valid/expired/missing/used token."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi import FastAPI, status
from fastapi.testclient import TestClient


@pytest.fixture
def mock_auth_collection():
    """Mock MongoDB auth_tokens collection for testing without real DB."""
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.update_one = AsyncMock(return_value=None)
    return col


@pytest.mark.asyncio
async def test_exchange_valid_token_naive_expires_at(
    app: FastAPI, client: TestClient, mock_auth_collection
):
    """Valid token with naive expires_at (as MongoDB returns) should return 200."""
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    naive_future = future.replace(tzinfo=None)  # MongoDB stores naive
    mock_auth_collection.find_one = AsyncMock(
        return_value={
            "token": "valid-token-xyz",
            "telegram_id": 12345,
            "expires_at": naive_future,
            "used": False,
        }
    )

    with patch(
        "app.application.api.v1.auth.handlers._get_auth_tokens_collection",
        return_value=mock_auth_collection,
    ):
        response = client.post(
            "/api/v1/auth/exchange",
            json={"token": "valid-token-xyz"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["ok"] is True
    assert data["telegram_id"] == 12345
    assert "lsj_session" in response.cookies


@pytest.mark.asyncio
async def test_exchange_valid_token_aware_expires_at(
    app: FastAPI, client: TestClient, mock_auth_collection
):
    """Valid token with timezone-aware expires_at should return 200."""
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    mock_auth_collection.find_one = AsyncMock(
        return_value={
            "token": "valid-token-aware",
            "telegram_id": 99999,
            "expires_at": future,
            "used": False,
        }
    )

    with patch(
        "app.application.api.v1.auth.handlers._get_auth_tokens_collection",
        return_value=mock_auth_collection,
    ):
        response = client.post(
            "/api/v1/auth/exchange",
            json={"token": "valid-token-aware"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["ok"] is True
    assert data["telegram_id"] == 99999


@pytest.mark.asyncio
async def test_exchange_expired_token(
    app: FastAPI, client: TestClient, mock_auth_collection
):
    """Expired token should return 400 with detail about expiration."""
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    naive_past = past.replace(tzinfo=None)
    mock_auth_collection.find_one = AsyncMock(
        return_value={
            "token": "expired-token",
            "telegram_id": 11111,
            "expires_at": naive_past,
            "used": False,
        }
    )

    with patch(
        "app.application.api.v1.auth.handlers._get_auth_tokens_collection",
        return_value=mock_auth_collection,
    ):
        response = client.post(
            "/api/v1/auth/exchange",
            json={"token": "expired-token"},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Токен истёк" in data["detail"]


@pytest.mark.asyncio
async def test_exchange_token_not_found(
    app: FastAPI, client: TestClient, mock_auth_collection
):
    """Missing/non-existent token should return 400."""
    mock_auth_collection.find_one = AsyncMock(return_value=None)

    with patch(
        "app.application.api.v1.auth.handlers._get_auth_tokens_collection",
        return_value=mock_auth_collection,
    ):
        response = client.post(
            "/api/v1/auth/exchange",
            json={"token": "nonexistent-token"},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "недействителен" in data["detail"] or "использован" in data["detail"]


@pytest.mark.asyncio
async def test_exchange_used_token(
    app: FastAPI, client: TestClient, mock_auth_collection
):
    """Already used token should return 400 (find_one with used=False finds nothing)."""
    mock_auth_collection.find_one = AsyncMock(return_value=None)

    with patch(
        "app.application.api.v1.auth.handlers._get_auth_tokens_collection",
        return_value=mock_auth_collection,
    ):
        response = client.post(
            "/api/v1/auth/exchange",
            json={"token": "already-used-token"},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_exchange_empty_token_returns_400(
    app: FastAPI, client: TestClient, mock_auth_collection
):
    """Empty token should return 400 (not found)."""
    mock_auth_collection.find_one = AsyncMock(return_value=None)

    with patch(
        "app.application.api.v1.auth.handlers._get_auth_tokens_collection",
        return_value=mock_auth_collection,
    ):
        response = client.post(
            "/api/v1/auth/exchange",
            json={"token": ""},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
