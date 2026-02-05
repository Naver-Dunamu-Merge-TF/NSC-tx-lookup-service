from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from src.db.admin_tx import fetch_admin_tx_context
from src.db.audit import record_admin_audit
from src.db.models import AdminAuditLog, LedgerEntry, PaymentOrder


def _dt(minutes: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def test_fetch_admin_tx_context_returns_peer(db_session, cleanup_test_rows):
    related_id = f"{cleanup_test_rows}-order"
    payment_tx_id = f"{cleanup_test_rows}-tx-pay"
    receive_tx_id = f"{cleanup_test_rows}-tx-rec"

    order = PaymentOrder(
        order_id=related_id,
        user_id="user-1",
        merchant_name="Shop",
        amount=Decimal("10.00"),
        status="SETTLED",
        created_at=_dt(-10),
        updated_at=_dt(-5),
        source_version=1,
        ingested_at=_dt(-5),
    )
    payment_entry = LedgerEntry(
        tx_id=payment_tx_id,
        wallet_id="wallet-pay",
        entry_type="PAYMENT",
        amount=Decimal("10.00"),
        amount_signed=Decimal("-10.00"),
        related_id=related_id,
        related_type="PAYMENT_ORDER",
        event_time=_dt(-6),
        created_at=_dt(-6),
        updated_at=_dt(-5),
        source_version=1,
        ingested_at=_dt(-5),
    )
    receive_entry = LedgerEntry(
        tx_id=receive_tx_id,
        wallet_id="wallet-rec",
        entry_type="RECEIVE",
        amount=Decimal("10.00"),
        amount_signed=Decimal("10.00"),
        related_id=related_id,
        related_type="PAYMENT_ORDER",
        event_time=_dt(-5),
        created_at=_dt(-5),
        updated_at=_dt(-4),
        source_version=1,
        ingested_at=_dt(-4),
    )

    db_session.add(order)
    db_session.add(payment_entry)
    db_session.add(receive_entry)
    db_session.commit()

    context = fetch_admin_tx_context(db_session, payment_tx_id)

    assert context is not None
    assert context.ledger_entry.tx_id == payment_tx_id
    assert context.payment_order is not None
    assert context.payment_pair is None
    assert context.peer_entry is not None
    assert context.peer_entry.tx_id == receive_tx_id


def test_record_admin_audit_persists_row(db_session, cleanup_test_rows):
    resource_id = f"{cleanup_test_rows}-tx-audit"
    fields = {
        "actor_id": "actor-1",
        "actor_roles": "ADMIN_READ",
        "action": "ADMIN_TX_LOOKUP",
        "resource_type": "TX",
        "resource_id": resource_id,
        "result": "FOUND",
        "status_code": 200,
        "ip": "127.0.0.1",
        "user_agent": "pytest",
        "request_method": "GET",
        "request_path": "/admin/tx/" + resource_id,
        "request_query": None,
        "requested_at": _dt(0),
        "duration_ms": 12,
    }

    record_admin_audit(db_session, fields)
    db_session.commit()

    row = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.resource_id == resource_id)
    ).scalar_one_or_none()

    assert row is not None
    assert row.actor_id == "actor-1"
    assert row.status_code == 200
