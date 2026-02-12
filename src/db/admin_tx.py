from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AdminTxContext:
    ledger_entry: Any
    payment_order: Any | None
    payment_pair: Any | None
    peer_entry: Any | None


def fetch_admin_tx_context(session: "Session", tx_id: str) -> AdminTxContext | None:
    from sqlalchemy import select

    from src.db.models import LedgerEntry, PaymentLedgerPair, PaymentOrder

    stmt = (
        select(LedgerEntry, PaymentOrder, PaymentLedgerPair)
        .outerjoin(PaymentOrder, PaymentOrder.order_id == LedgerEntry.related_id)
        .outerjoin(
            PaymentLedgerPair,
            PaymentLedgerPair.payment_order_id == LedgerEntry.related_id,
        )
        .where(LedgerEntry.tx_id == tx_id)
    )

    row = session.execute(stmt).first()
    if not row:
        return None

    ledger_entry, payment_order, payment_pair = row
    peer_entry = None

    if ledger_entry.related_id:
        needs_peer = payment_pair is None or not (
            payment_pair.payment_tx_id and payment_pair.receive_tx_id
        )
        if needs_peer:
            opposite_type = (
                "RECEIVE" if ledger_entry.entry_type == "PAYMENT" else "PAYMENT"
            )
            peer_stmt = (
                select(LedgerEntry)
                .where(
                    LedgerEntry.related_id == ledger_entry.related_id,
                    LedgerEntry.tx_id != ledger_entry.tx_id,
                    LedgerEntry.entry_type == opposite_type,
                )
                .order_by(LedgerEntry.event_time.desc(), LedgerEntry.tx_id)
            )
            peer_entry = session.execute(peer_stmt).scalars().first()

    return AdminTxContext(
        ledger_entry=ledger_entry,
        payment_order=payment_order,
        payment_pair=payment_pair,
        peer_entry=peer_entry,
    )
