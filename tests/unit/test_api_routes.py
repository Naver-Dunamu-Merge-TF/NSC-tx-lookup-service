from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from src.api import main as api_main


@contextmanager
def _fake_session_scope():
    yield object()


def _allow_admin(request: Request):
    request.state.actor_id = "actor-1"
    request.state.actor_roles = ["ADMIN_READ"]
    return None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    api_main.app.dependency_overrides[api_main.require_admin_read] = _allow_admin
    monkeypatch.setattr(api_main, "session_scope", _fake_session_scope)
    with TestClient(api_main.app) as client:
        yield client
    api_main.app.dependency_overrides = {}


def test_get_admin_tx_success(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    expected = {
        "tx_id": "tx-123",
        "event_time": datetime(2026, 2, 5, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
        "entry_type": "PAYMENT",
        "amount": str(Decimal("10.00")),
        "amount_signed": str(Decimal("-10.00")),
        "status": "SETTLED",
        "status_group": "SETTLED",
        "sender_wallet_id": "wallet-1",
        "receiver_wallet_id": "wallet-2",
        "related": {"related_id": "po-1", "related_type": "PAYMENT_ORDER"},
        "paired_tx_id": "tx-456",
        "merchant_name": "Shop",
        "pairing_status": "COMPLETE",
        "data_lag_sec": 0,
    }

    recorded: dict[str, object] = {}
    sentinel = object()

    def fake_fetch(session, tx_id):
        assert tx_id == "tx-123"
        return sentinel

    def fake_build(context):
        assert context is sentinel
        return expected

    def fake_record(session, fields):
        recorded.update(fields)

    monkeypatch.setattr(api_main, "fetch_admin_tx_context", fake_fetch)
    monkeypatch.setattr(api_main, "build_admin_tx_response", fake_build)
    monkeypatch.setattr(api_main, "record_admin_audit", fake_record)

    response = client.get("/admin/tx/tx-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tx_id"] == "tx-123"
    assert payload["pairing_status"] == "COMPLETE"
    assert recorded["result"] == "FOUND"
    assert recorded["status_code"] == 200
    assert recorded["resource_id"] == "tx-123"


def test_get_admin_tx_404(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    recorded: dict[str, object] = {}

    def fake_fetch(session, tx_id):
        assert tx_id == "missing-tx"
        return None

    def fake_record(session, fields):
        recorded.update(fields)

    monkeypatch.setattr(api_main, "fetch_admin_tx_context", fake_fetch)
    monkeypatch.setattr(api_main, "record_admin_audit", fake_record)

    response = client.get("/admin/tx/missing-tx")

    assert response.status_code == 404
    assert response.json()["detail"] == "tx_id not found"
    assert recorded["result"] == "NOT_FOUND"
    assert recorded["status_code"] == 404
    assert recorded["resource_id"] == "missing-tx"


def test_get_admin_tx_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    api_main.app.dependency_overrides = {}
    monkeypatch.setenv("AUTH_MODE", "oidc")

    with TestClient(api_main.app) as client:
        response = client.get("/admin/tx/tx-123")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authorization header missing"
