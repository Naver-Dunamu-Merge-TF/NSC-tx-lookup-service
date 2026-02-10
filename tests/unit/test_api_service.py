from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.api.schemas import PairingStatus
from src.api.service import _resolve_status_group, build_admin_tx_response
from src.db.admin_tx import AdminTxContext


@dataclass
class LedgerEntryStub:
    tx_id: str
    wallet_id: str
    entry_type: str
    amount: Decimal
    amount_signed: Decimal | None
    related_id: str | None
    related_type: str | None
    event_time: datetime
    created_at: datetime
    updated_at: datetime | None
    source_version: int | None
    ingested_at: datetime


@dataclass
class PaymentOrderStub:
    order_id: str
    user_id: str | None
    merchant_name: str | None
    amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime | None
    source_version: int | None
    ingested_at: datetime


@dataclass
class PaymentLedgerPairStub:
    payment_order_id: str
    payment_tx_id: str | None
    receive_tx_id: str | None
    payer_wallet_id: str | None
    payee_wallet_id: str | None
    amount: Decimal | None
    status: str | None
    event_time: datetime | None
    updated_at: datetime
    ingested_at: datetime


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def test_build_admin_tx_response_complete_pair() -> None:
    ledger = LedgerEntryStub(
        tx_id="tx-pay",
        wallet_id="wallet-pay",
        entry_type="PAYMENT",
        amount=Decimal("10.00"),
        amount_signed=Decimal("-10.00"),
        related_id="po-1",
        related_type=None,
        event_time=_dt("2026-02-05T01:00:00Z"),
        created_at=_dt("2026-02-05T01:00:00Z"),
        updated_at=_dt("2026-02-05T01:00:01Z"),
        source_version=1,
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    payment_order = PaymentOrderStub(
        order_id="po-1",
        user_id="user-1",
        merchant_name="Merchant",
        amount=Decimal("10.00"),
        status="SETTLED",
        created_at=_dt("2026-02-05T00:59:00Z"),
        updated_at=_dt("2026-02-05T01:00:00Z"),
        source_version=1,
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    pair = PaymentLedgerPairStub(
        payment_order_id="po-1",
        payment_tx_id="tx-pay",
        receive_tx_id="tx-rec",
        payer_wallet_id="wallet-pay",
        payee_wallet_id="wallet-rec",
        amount=Decimal("10.00"),
        status="SETTLED",
        event_time=_dt("2026-02-05T01:00:00Z"),
        updated_at=_dt("2026-02-05T01:00:02Z"),
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    context = AdminTxContext(
        ledger_entry=ledger,
        payment_order=payment_order,
        payment_pair=pair,
        peer_entry=None,
    )

    response = build_admin_tx_response(context)

    assert response.pairing_status == PairingStatus.COMPLETE
    assert response.status_group == "SUCCESS"
    assert response.paired_tx_id == "tx-rec"
    assert response.sender_wallet_id == "wallet-pay"
    assert response.receiver_wallet_id == "wallet-rec"
    assert response.related is not None
    assert response.related.related_type == "PAYMENT_ORDER"


def test_build_admin_tx_response_unknown_pairing() -> None:
    ledger = LedgerEntryStub(
        tx_id="tx-unknown",
        wallet_id="wallet-unknown",
        entry_type="RECEIVE",
        amount=Decimal("5.00"),
        amount_signed=Decimal("5.00"),
        related_id=None,
        related_type=None,
        event_time=_dt("2026-02-05T01:00:00Z"),
        created_at=_dt("2026-02-05T01:00:00Z"),
        updated_at=None,
        source_version=None,
        ingested_at=_dt("2026-02-05T01:00:00Z"),
    )

    context = AdminTxContext(
        ledger_entry=ledger,
        payment_order=None,
        payment_pair=None,
        peer_entry=None,
    )

    response = build_admin_tx_response(context)

    assert response.pairing_status == PairingStatus.UNKNOWN
    assert response.related is None
    assert response.status_group == "UNKNOWN"


# --- _resolve_status_group tests ---


@pytest.mark.parametrize(
    "status",
    ["SETTLED", "COMPLETED", "SUCCESS", "SUCCEEDED", "PAID"],
)
def test_resolve_status_group_success_variants(status: str) -> None:
    assert _resolve_status_group(status) == "SUCCESS"


@pytest.mark.parametrize(
    "status",
    ["FAILED", "CANCELLED", "CANCELED", "REJECTED", "DECLINED"],
)
def test_resolve_status_group_fail_variants(status: str) -> None:
    assert _resolve_status_group(status) == "FAIL"


@pytest.mark.parametrize(
    "status",
    ["CREATED", "PENDING", "PROCESSING", "AUTHORIZED"],
)
def test_resolve_status_group_in_progress_variants(status: str) -> None:
    assert _resolve_status_group(status) == "IN_PROGRESS"


@pytest.mark.parametrize(
    "status",
    [None, "", " ", "RANDOM", "refunded"],
)
def test_resolve_status_group_unknown_and_edge(status: str | None) -> None:
    assert _resolve_status_group(status) == "UNKNOWN"


# --- Incomplete pairing tests ---


def test_build_admin_tx_response_incomplete_pair() -> None:
    ledger = LedgerEntryStub(
        tx_id="tx-pay",
        wallet_id="wallet-pay",
        entry_type="PAYMENT",
        amount=Decimal("10.00"),
        amount_signed=Decimal("-10.00"),
        related_id="po-1",
        related_type="PAYMENT_ORDER",
        event_time=_dt("2026-02-05T01:00:00Z"),
        created_at=_dt("2026-02-05T01:00:00Z"),
        updated_at=_dt("2026-02-05T01:00:01Z"),
        source_version=1,
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    context = AdminTxContext(
        ledger_entry=ledger,
        payment_order=None,
        payment_pair=None,
        peer_entry=None,
    )

    response = build_admin_tx_response(context)

    assert response.pairing_status == PairingStatus.INCOMPLETE
    assert response.paired_tx_id is None
    assert response.sender_wallet_id == "wallet-pay"
    assert response.receiver_wallet_id is None


def test_build_admin_tx_response_receive_perspective() -> None:
    ledger = LedgerEntryStub(
        tx_id="tx-rec",
        wallet_id="wallet-rec",
        entry_type="RECEIVE",
        amount=Decimal("10.00"),
        amount_signed=Decimal("10.00"),
        related_id="po-1",
        related_type="PAYMENT_ORDER",
        event_time=_dt("2026-02-05T01:00:00Z"),
        created_at=_dt("2026-02-05T01:00:00Z"),
        updated_at=_dt("2026-02-05T01:00:01Z"),
        source_version=1,
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    pair = PaymentLedgerPairStub(
        payment_order_id="po-1",
        payment_tx_id="tx-pay",
        receive_tx_id="tx-rec",
        payer_wallet_id="wallet-pay",
        payee_wallet_id="wallet-rec",
        amount=Decimal("10.00"),
        status="SETTLED",
        event_time=_dt("2026-02-05T01:00:00Z"),
        updated_at=_dt("2026-02-05T01:00:02Z"),
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    payment_order = PaymentOrderStub(
        order_id="po-1",
        user_id="user-1",
        merchant_name="Merchant",
        amount=Decimal("10.00"),
        status="SETTLED",
        created_at=_dt("2026-02-05T00:59:00Z"),
        updated_at=_dt("2026-02-05T01:00:00Z"),
        source_version=1,
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    context = AdminTxContext(
        ledger_entry=ledger,
        payment_order=payment_order,
        payment_pair=pair,
        peer_entry=None,
    )

    response = build_admin_tx_response(context)

    assert response.pairing_status == PairingStatus.COMPLETE
    assert response.paired_tx_id == "tx-pay"
    assert response.sender_wallet_id == "wallet-pay"
    assert response.receiver_wallet_id == "wallet-rec"


def test_build_admin_tx_response_peer_entry_fallback() -> None:
    ledger = LedgerEntryStub(
        tx_id="tx-pay",
        wallet_id="wallet-pay",
        entry_type="PAYMENT",
        amount=Decimal("10.00"),
        amount_signed=Decimal("-10.00"),
        related_id="po-1",
        related_type="PAYMENT_ORDER",
        event_time=_dt("2026-02-05T01:00:00Z"),
        created_at=_dt("2026-02-05T01:00:00Z"),
        updated_at=_dt("2026-02-05T01:00:01Z"),
        source_version=1,
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    peer = LedgerEntryStub(
        tx_id="tx-rec",
        wallet_id="wallet-rec",
        entry_type="RECEIVE",
        amount=Decimal("10.00"),
        amount_signed=Decimal("10.00"),
        related_id="po-1",
        related_type="PAYMENT_ORDER",
        event_time=_dt("2026-02-05T01:00:00Z"),
        created_at=_dt("2026-02-05T01:00:00Z"),
        updated_at=_dt("2026-02-05T01:00:01Z"),
        source_version=1,
        ingested_at=_dt("2026-02-05T01:00:02Z"),
    )
    context = AdminTxContext(
        ledger_entry=ledger,
        payment_order=None,
        payment_pair=None,
        peer_entry=peer,
    )

    response = build_admin_tx_response(context)

    assert response.pairing_status == PairingStatus.COMPLETE
    assert response.paired_tx_id == "tx-rec"
    assert response.sender_wallet_id == "wallet-pay"
    assert response.receiver_wallet_id == "wallet-rec"
