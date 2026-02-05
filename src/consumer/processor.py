from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.consumer.events import LedgerEntryUpserted, PaymentOrderUpserted
from src.consumer.pairing import PairingSnapshot, update_pairing_for_related_id
from src.db.models import LedgerEntry, PaymentLedgerPair, PaymentOrder
from src.db.upsert import latest_wins_upsert


def _ingested_now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_ledger_entry(
    session: Session, event: LedgerEntryUpserted
) -> tuple[bool, PairingSnapshot | None]:
    ingested_at = _ingested_now()
    values = {
        "tx_id": event.tx_id,
        "wallet_id": event.wallet_id,
        "entry_type": event.entry_type,
        "amount": event.amount,
        "amount_signed": event.amount_signed,
        "related_id": event.related_id,
        "related_type": event.related_type,
        "event_time": event.event_time,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "source_version": event.source_version,
        "ingested_at": ingested_at,
    }
    stmt = latest_wins_upsert(LedgerEntry.__table__, values, ["tx_id"])
    session.execute(stmt)

    missing_version = event.updated_at is None and event.source_version is None
    pairing_snapshot = None
    if event.related_id:
        pairing_snapshot = update_pairing_for_related_id(session, event.related_id)

    return missing_version, pairing_snapshot


def upsert_payment_order(session: Session, event: PaymentOrderUpserted) -> bool:
    ingested_at = _ingested_now()
    values = {
        "order_id": event.order_id,
        "user_id": event.user_id,
        "merchant_name": event.merchant_name,
        "amount": event.amount,
        "status": event.status,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "source_version": event.source_version,
        "ingested_at": ingested_at,
    }
    stmt = latest_wins_upsert(PaymentOrder.__table__, values, ["order_id"])
    session.execute(stmt)

    return event.updated_at is None and event.source_version is None


def upsert_payment_pair(
    session: Session,
    payment_order_id: str,
    payment_tx_id: str | None,
    receive_tx_id: str | None,
    payer_wallet_id: str | None,
    payee_wallet_id: str | None,
    amount,
    status: str | None,
    event_time,
) -> None:
    ingested_at = _ingested_now()
    values = {
        "payment_order_id": payment_order_id,
        "payment_tx_id": payment_tx_id,
        "receive_tx_id": receive_tx_id,
        "payer_wallet_id": payer_wallet_id,
        "payee_wallet_id": payee_wallet_id,
        "amount": amount,
        "status": status,
        "event_time": event_time,
        "updated_at": ingested_at,
        "ingested_at": ingested_at,
    }
    stmt = latest_wins_upsert(
        PaymentLedgerPair.__table__, values, ["payment_order_id"]
    )
    session.execute(stmt)
