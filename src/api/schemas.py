from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PairingStatus(str, Enum):
    """PAYMENT/RECEIVE 엔트리 페어링 상태."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class RelatedInfo(BaseModel):
    """거래와 연관된 결제 주문 정보."""

    related_id: str | None = Field(
        description="연관 엔티티 ID (예: payment_order_id)",
        examples=["po-001"],
    )
    related_type: str = Field(
        description="연관 엔티티 유형",
        examples=["PAYMENT_ORDER"],
    )


class AdminTxResponse(BaseModel):
    """관리자 거래 조회 응답. 단일 원장 엔트리와 페어링 정보를 포함."""

    tx_id: str = Field(description="원장 엔트리 ID", examples=["tx-001"])
    event_time: datetime = Field(
        description="거래 발생 시각 (UTC)",
        examples=["2026-02-04T03:12:45Z"],
    )
    entry_type: str = Field(
        description="엔트리 유형 (PAYMENT 또는 RECEIVE)",
        examples=["PAYMENT"],
    )
    amount: Decimal = Field(description="거래 금액 (양수)", examples=[10000.00])
    amount_signed: Decimal | None = Field(
        description="부호 포함 금액 (출금 시 음수)",
        examples=[-10000.00],
    )
    status: str | None = Field(
        description="결제 주문 상태",
        examples=["SETTLED"],
    )
    status_group: str = Field(
        description="상태 그룹 (SUCCESS/FAIL/IN_PROGRESS/UNKNOWN)",
        examples=["UNKNOWN"],
    )
    sender_wallet_id: str | None = Field(
        description="송금자 지갑 ID",
        examples=["wallet-A"],
    )
    receiver_wallet_id: str | None = Field(
        description="수취자 지갑 ID",
        examples=["wallet-B"],
    )
    related: RelatedInfo | None = Field(
        default=None,
        description="연관 결제 주문 정보",
    )
    paired_tx_id: str | None = Field(
        description="페어링된 반대편 엔트리 tx_id",
        examples=["tx-002"],
    )
    merchant_name: str | None = Field(
        description="가맹점명",
        examples=["MERCHANT_1"],
    )
    pairing_status: PairingStatus = Field(
        description="PAYMENT/RECEIVE 페어링 상태",
    )
    data_lag_sec: int | None = Field(
        description="데이터 지연 시간 (초)",
        examples=[3],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "tx_id": "tx-001",
                    "event_time": "2026-02-04T03:12:45Z",
                    "entry_type": "PAYMENT",
                    "amount": 10000.00,
                    "amount_signed": -10000.00,
                    "status": "SETTLED",
                    "status_group": "UNKNOWN",
                    "sender_wallet_id": "wallet-A",
                    "receiver_wallet_id": "wallet-B",
                    "related": {
                        "related_id": "po-001",
                        "related_type": "PAYMENT_ORDER",
                    },
                    "paired_tx_id": "tx-002",
                    "merchant_name": "MERCHANT_1",
                    "pairing_status": "COMPLETE",
                    "data_lag_sec": 3,
                }
            ]
        }
    )
