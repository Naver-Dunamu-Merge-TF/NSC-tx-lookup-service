from __future__ import annotations

import pytest

from src.consumer.contract_normalizer import (
    ContractCoreViolationError,
    normalize_payload_for_topic,
)
from src.consumer.contract_profile import (
    AliasProfile,
    CoreRequiredPolicy,
    EventContractProfile,
    TopicProfile,
)
from src.consumer.events import EventValidationError


def _profile() -> EventContractProfile:
    return EventContractProfile(
        profile_id="canonical-v1",
        topics=TopicProfile(
            ledger="ledger.entry.upserted",
            payment_order="payment.order.upserted",
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


def test_normalize_payload_resolves_aliases_in_order():
    payload = {
        "tx_id": "tx-1",
        "wallet_id": "wallet-1",
        "type": "PAYMENT",
        "amount": "10.00",
        "source_created_at": "2026-02-05T01:00:00Z",
        "source_version": 7,
    }
    normalized = normalize_payload_for_topic(
        "ledger.entry.upserted", payload, _profile()
    )

    assert normalized.topic_kind == "ledger"
    assert normalized.payload["entry_type"] == "PAYMENT"
    assert normalized.payload["event_time"] == "2026-02-05T01:00:00Z"
    assert normalized.payload["version"] == 7
    assert ("entry_type", "type") in normalized.alias_hits
    assert ("event_time", "source_created_at") in normalized.alias_hits
    assert ("version", "source_version") in normalized.alias_hits


def test_normalize_payload_raises_on_alias_conflict():
    payload = {
        "tx_id": "tx-1",
        "wallet_id": "wallet-1",
        "entry_type": "PAYMENT",
        "type": "RECEIVE",
        "amount": "10.00",
        "event_time": "2026-02-05T01:00:00Z",
    }
    with pytest.raises(ContractCoreViolationError, match="entry_type"):
        normalize_payload_for_topic("ledger.entry.upserted", payload, _profile())


def test_normalize_payload_raises_on_missing_core_required():
    payload = {
        "tx_id": "tx-1",
        "type": "PAYMENT",
        "amount": "10.00",
        "source_created_at": "2026-02-05T01:00:00Z",
    }
    with pytest.raises(EventValidationError, match="core required"):
        normalize_payload_for_topic("ledger.entry.upserted", payload, _profile())
