from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class PairingStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class RelatedInfo(BaseModel):
    related_id: str | None
    related_type: str


class AdminTxResponse(BaseModel):
    tx_id: str
    event_time: datetime
    entry_type: str
    amount: Decimal
    amount_signed: Decimal | None
    status: str | None
    status_group: str
    sender_wallet_id: str | None
    receiver_wallet_id: str | None
    related: RelatedInfo | None
    paired_tx_id: str | None
    merchant_name: str | None
    pairing_status: PairingStatus
    data_lag_sec: int | None
