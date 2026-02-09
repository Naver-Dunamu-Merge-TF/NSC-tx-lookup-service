from __future__ import annotations

import pytest

from src.consumer.events import (
    EventValidationError,
    LedgerEntryUpserted,
    PaymentOrderUpserted,
)


def test_ledger_entry_from_dict_happy(transaction_ledger_happy_rows):
    payload = transaction_ledger_happy_rows[0]
    event = LedgerEntryUpserted.from_dict(payload)

    assert event.tx_id == payload["tx_id"]
    assert event.wallet_id == payload["wallet_id"]
    assert event.entry_type == payload["type"]
    assert event.amount is not None
    assert event.event_time is not None


def test_ledger_entry_missing_tx_id_raises():
    with pytest.raises(EventValidationError):
        LedgerEntryUpserted.from_dict(
            {
                "wallet_id": "wallet-1",
                "entry_type": "PAYMENT",
                "amount": "1.00",
                "event_time": "2026-02-05T01:00:00Z",
                "created_at": "2026-02-05T01:00:00Z",
            }
        )


def test_payment_order_from_dict_happy(payment_orders_happy_rows):
    payload = payment_orders_happy_rows[0]
    event = PaymentOrderUpserted.from_dict(payload)

    assert event.order_id == payload["order_id"]
    assert event.status == payload["status"]
    assert event.amount is not None


def test_payment_order_missing_status_raises():
    with pytest.raises(EventValidationError):
        PaymentOrderUpserted.from_dict(
            {
                "order_id": "order-1",
                "amount": "10.00",
                "created_at": "2026-02-05T01:00:00Z",
            }
        )
