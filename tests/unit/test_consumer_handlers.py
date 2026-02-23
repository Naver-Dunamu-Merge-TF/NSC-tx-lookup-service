from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.consumer import main as consumer_main
from src.consumer.contract_profile import (
    AliasProfile,
    CoreRequiredPolicy,
    EventContractProfile,
    TopicProfile,
)
from src.consumer.events import EventValidationError
from src.consumer.metrics import PairingMetrics, VersionMissingCounter
from src.consumer.pairing import PairingSnapshot


@contextmanager
def _fake_session_scope():
    yield object()


def _config():
    return SimpleNamespace(
        effective_ledger_topic="ledger.entry.upserted",
        effective_payment_order_topic="payment.order.upserted",
        ledger_topic="ledger.entry.upserted",
        payment_order_topic="payment.order.upserted",
        event_profile_id="canonical-v1",
    )


def _runtime() -> consumer_main.ConsumerRuntime:
    config = _config()
    profile = EventContractProfile(
        profile_id=config.event_profile_id,
        topics=TopicProfile(
            ledger=config.effective_ledger_topic,
            payment_order=config.effective_payment_order_topic,
        ),
        aliases=AliasProfile(
            ledger={
                "entry_type": ("entry_type", "type"),
                "event_time": ("event_time", "source_created_at", "created_at"),
                "version": ("version", "source_version"),
            },
            payment_order={"version": ("version", "source_version")},
        ),
        core_required=CoreRequiredPolicy(
            ledger=("tx_id", "wallet_id", "entry_type", "amount", "event_time_or_alias"),
            payment_order=("order_id", "amount", "status", "created_at"),
        ),
    )
    return consumer_main.ConsumerRuntime(config=config, profile=profile)


def test_handle_payload_ledger_topic(
    monkeypatch: pytest.MonkeyPatch, transaction_ledger_happy_rows
):
    runtime = _runtime()
    monkeypatch.setattr(consumer_main, "session_scope", _fake_session_scope)

    calls: dict[str, object] = {}

    def fake_upsert(session, event):
        calls["event"] = event
        snapshot = PairingSnapshot(
            payment_order_id="po-1",
            payment_tx_id=event.tx_id,
            receive_tx_id=None,
            payer_wallet_id=event.wallet_id,
            payee_wallet_id=None,
            amount=Decimal("10.00"),
            status=None,
            event_time=datetime.now(timezone.utc),
            complete=False,
            incomplete_age_sec=1.0,
        )
        return True, snapshot

    monkeypatch.setattr(consumer_main, "upsert_ledger_entry", fake_upsert)

    counter = VersionMissingCounter(log_every=1)
    pairing_metrics = PairingMetrics(log_every=1)

    payload = transaction_ledger_happy_rows[0]
    consumer_main._handle_payload(
        runtime.profile.topics.ledger,
        payload,
        counter,
        pairing_metrics,
        runtime,
    )
    consumer_main._handle_payload(
        runtime.profile.topics.ledger,
        payload,
        counter,
        pairing_metrics,
        runtime,
    )

    assert calls["event"].tx_id == payload["tx_id"]
    assert counter.processed == 2
    assert counter.missing_version == 2
    assert pairing_metrics.total == 2
    assert pairing_metrics.incomplete == 2


def test_handle_payload_payment_order_topic(
    monkeypatch: pytest.MonkeyPatch, payment_orders_happy_rows
):
    runtime = _runtime()
    monkeypatch.setattr(consumer_main, "session_scope", _fake_session_scope)

    calls: dict[str, object] = {}

    def fake_upsert(session, event):
        calls["event"] = event
        return False

    monkeypatch.setattr(consumer_main, "upsert_payment_order", fake_upsert)

    counter = VersionMissingCounter(log_every=1)
    pairing_metrics = PairingMetrics(log_every=1)

    payload = payment_orders_happy_rows[0]
    consumer_main._handle_payload(
        runtime.profile.topics.payment_order,
        payload,
        counter,
        pairing_metrics,
        runtime,
    )

    assert calls["event"].order_id == payload["order_id"]
    assert counter.processed == 1
    assert counter.missing_version == 0
    assert pairing_metrics.total == 0


def test_handle_payload_unknown_topic(monkeypatch: pytest.MonkeyPatch):
    runtime = _runtime()
    monkeypatch.setattr(consumer_main, "session_scope", _fake_session_scope)

    counter = VersionMissingCounter()
    pairing_metrics = PairingMetrics()

    with pytest.raises(EventValidationError):
        consumer_main._handle_payload(
            "unknown-topic", {}, counter, pairing_metrics, runtime
        )


def test_handle_payload_unknown_topic_includes_profile_id(
    monkeypatch: pytest.MonkeyPatch,
):
    runtime = _runtime()
    monkeypatch.setattr(consumer_main, "session_scope", _fake_session_scope)

    counter = VersionMissingCounter()
    pairing_metrics = PairingMetrics()

    with pytest.raises(EventValidationError, match="canonical-v1"):
        consumer_main._handle_payload(
            "unknown-topic", {}, counter, pairing_metrics, runtime
        )


def test_handle_payload_invalid_payload(monkeypatch: pytest.MonkeyPatch):
    runtime = _runtime()
    monkeypatch.setattr(consumer_main, "session_scope", _fake_session_scope)

    counter = VersionMissingCounter()
    pairing_metrics = PairingMetrics()

    with pytest.raises(EventValidationError):
        consumer_main._handle_payload(
            runtime.profile.topics.ledger,
            {"wallet_id": "w1"},
            counter,
            pairing_metrics,
            runtime,
        )


def test_handle_payload_hot_path_does_not_reload_config(
    monkeypatch: pytest.MonkeyPatch, payment_orders_happy_rows
):
    runtime = _runtime()
    monkeypatch.setattr(
        consumer_main,
        "load_config",
        lambda: (_ for _ in ()).throw(AssertionError("load_config call forbidden")),
    )
    monkeypatch.setattr(consumer_main, "session_scope", _fake_session_scope)
    monkeypatch.setattr(consumer_main, "upsert_payment_order", lambda _s, _e: False)

    counter = VersionMissingCounter(log_every=1)
    pairing_metrics = PairingMetrics(log_every=1)
    payload = payment_orders_happy_rows[0]

    consumer_main._handle_payload(
        runtime.profile.topics.payment_order,
        payload,
        counter,
        pairing_metrics,
        runtime,
    )
