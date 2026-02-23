from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from src.common.config import load_config
from src.consumer import main as consumer_main
from src.consumer.metrics import PairingMetrics, VersionMissingCounter


@contextmanager
def _fake_session_scope():
    yield object()


class _FakeMsg:
    def __init__(self, topic: str, payload: dict, key: str = "k-1") -> None:
        self._topic = topic
        self._payload = json.dumps(payload).encode("utf-8")
        self._key = key.encode("utf-8")

    def error(self):
        return None

    def headers(self):
        return []

    def value(self):
        return self._payload

    def topic(self):
        return self._topic

    def partition(self):
        return 0

    def offset(self):
        return 1

    def key(self):
        return self._key


class _FakeConsumer:
    def __init__(self, messages: list[_FakeMsg]) -> None:
        self._messages = messages
        self._idx = 0
        self.subscribed: list[str] = []
        self.committed: int = 0
        self.closed = False

    def subscribe(self, topics: list[str]) -> None:
        self.subscribed = topics

    def poll(self, timeout: float):
        if self._idx < len(self._messages):
            msg = self._messages[self._idx]
            self._idx += 1
            return msg
        return None

    def commit(self, _msg) -> None:
        self.committed += 1

    def get_watermark_offsets(self, topic: str, partition: int, cached: bool = False):
        _ = (topic, partition, cached)
        return 0, 2

    def close(self) -> None:
        self.closed = True


def test_handle_payload_accepts_profile_specific_topics(
    monkeypatch: pytest.MonkeyPatch, transaction_ledger_happy_rows
) -> None:
    config = load_config(env={"EVENT_PROFILE_ID": "nsc-dev-v1"})
    runtime = consumer_main._build_runtime(config)
    monkeypatch.setattr(consumer_main, "session_scope", _fake_session_scope)

    captured: dict[str, object] = {}

    def fake_upsert(_session, event):
        captured["event"] = event
        return False, None

    monkeypatch.setattr(consumer_main, "upsert_ledger_entry", fake_upsert)

    consumer_main._handle_payload(
        runtime.profile.topics.ledger,
        transaction_ledger_happy_rows[0],
        VersionMissingCounter(),
        PairingMetrics(),
        runtime,
    )
    assert captured["event"].tx_id == transaction_ledger_happy_rows[0]["tx_id"]


def _run_consumer_with_single_payload(
    monkeypatch: pytest.MonkeyPatch, payload: dict
) -> list[dict]:
    config = load_config(env={})
    fake_consumer = _FakeConsumer([_FakeMsg(config.effective_ledger_topic, payload)])
    dlq_payloads: list[dict] = []

    monkeypatch.setattr(consumer_main, "load_config", lambda: config)
    monkeypatch.setattr(consumer_main, "_build_consumer", lambda _config: fake_consumer)
    monkeypatch.setattr(consumer_main, "_init_observability", lambda: None)
    monkeypatch.setattr(consumer_main, "_maybe_prune_dlq", lambda _config: None)
    monkeypatch.setattr(
        consumer_main,
        "_write_dlq_payload",
        lambda _config, dlq_payload: dlq_payloads.append(dlq_payload),
    )

    consumer_main.run_consumer(max_messages=1, max_idle_seconds=0)
    return dlq_payloads


def test_run_consumer_alias_conflict_goes_to_contract_core_violation_dlq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "tx_id": "tx-1",
        "wallet_id": "wallet-1",
        "entry_type": "PAYMENT",
        "type": "RECEIVE",
        "amount": "10.00",
        "event_time": "2026-02-05T01:00:00Z",
    }
    dlq_payloads = _run_consumer_with_single_payload(monkeypatch, payload)
    assert len(dlq_payloads) == 1
    assert dlq_payloads[0]["error"] == "contract_core_violation"


def test_run_consumer_core_missing_goes_to_parse_error_dlq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "tx_id": "tx-1",
        "type": "PAYMENT",
        "amount": "10.00",
        "event_time": "2026-02-05T01:00:00Z",
    }
    dlq_payloads = _run_consumer_with_single_payload(monkeypatch, payload)
    assert len(dlq_payloads) == 1
    assert dlq_payloads[0]["error"] == "parse_error"
