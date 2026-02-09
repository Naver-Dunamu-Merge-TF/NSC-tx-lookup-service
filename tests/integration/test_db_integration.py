from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from src.consumer.pairing import update_pairing_for_related_id
from src.db.models import LedgerEntry, PaymentLedgerPair, PaymentOrder
from src.db.upsert import latest_wins_upsert


def _dt(minutes: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def test_latest_wins_upsert_respects_updated_at(db_session, cleanup_test_rows):
    order_id = f"{cleanup_test_rows}-order"
    first = {
        "order_id": order_id,
        "user_id": "user-1",
        "merchant_name": "Merchant",
        "amount": Decimal("10.00"),
        "status": "NEW",
        "created_at": _dt(-10),
        "updated_at": _dt(-5),
        "source_version": 1,
        "ingested_at": _dt(-5),
    }
    stale = {
        "order_id": order_id,
        "user_id": "user-1",
        "merchant_name": "Merchant",
        "amount": Decimal("10.00"),
        "status": "OLD",
        "created_at": _dt(-10),
        "updated_at": _dt(-20),
        "source_version": 0,
        "ingested_at": _dt(-1),
    }

    db_session.execute(latest_wins_upsert(PaymentOrder.__table__, first, ["order_id"]))
    db_session.execute(latest_wins_upsert(PaymentOrder.__table__, stale, ["order_id"]))
    db_session.commit()

    row = db_session.get(PaymentOrder, order_id)
    assert row is not None
    assert row.status == "NEW"


def test_latest_wins_upsert_uses_version_when_updated_missing(
    db_session, cleanup_test_rows
):
    order_id = f"{cleanup_test_rows}-order-version"
    first = {
        "order_id": order_id,
        "user_id": "user-1",
        "merchant_name": "Merchant",
        "amount": Decimal("10.00"),
        "status": "V1",
        "created_at": _dt(-10),
        "updated_at": None,
        "source_version": 1,
        "ingested_at": _dt(-5),
    }
    newer = {
        "order_id": order_id,
        "user_id": "user-1",
        "merchant_name": "Merchant",
        "amount": Decimal("10.00"),
        "status": "V2",
        "created_at": _dt(-10),
        "updated_at": None,
        "source_version": 2,
        "ingested_at": _dt(-1),
    }

    db_session.execute(latest_wins_upsert(PaymentOrder.__table__, first, ["order_id"]))
    db_session.execute(latest_wins_upsert(PaymentOrder.__table__, newer, ["order_id"]))
    db_session.commit()

    row = db_session.get(PaymentOrder, order_id)
    assert row is not None
    assert row.status == "V2"


def test_update_pairing_for_related_id(db_session, cleanup_test_rows):
    related_id = f"{cleanup_test_rows}-po"

    ledger_payment = LedgerEntry(
        tx_id=f"{cleanup_test_rows}-tx-pay",
        wallet_id="wallet-pay",
        entry_type="PAYMENT",
        amount=Decimal("10.00"),
        amount_signed=Decimal("-10.00"),
        related_id=related_id,
        related_type="PAYMENT_ORDER",
        event_time=_dt(-5),
        created_at=_dt(-5),
        updated_at=_dt(-4),
        source_version=1,
        ingested_at=_dt(-4),
    )
    ledger_receive = LedgerEntry(
        tx_id=f"{cleanup_test_rows}-tx-rec",
        wallet_id="wallet-rec",
        entry_type="RECEIVE",
        amount=Decimal("10.00"),
        amount_signed=Decimal("10.00"),
        related_id=related_id,
        related_type="PAYMENT_ORDER",
        event_time=_dt(-4),
        created_at=_dt(-4),
        updated_at=_dt(-3),
        source_version=1,
        ingested_at=_dt(-3),
    )

    db_session.add(ledger_payment)
    db_session.add(ledger_receive)
    db_session.commit()

    snapshot = update_pairing_for_related_id(db_session, related_id)
    assert snapshot is not None
    db_session.commit()

    pair = db_session.execute(
        select(PaymentLedgerPair).where(
            PaymentLedgerPair.payment_order_id == related_id
        )
    ).scalar_one_or_none()

    assert pair is not None
    assert pair.payment_tx_id is not None
    assert pair.receive_tx_id is not None
