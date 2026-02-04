# tx-lookup-service

기획서의 FR-ADM-02(거래 내역 추적)를 구현하기 위한 서빙 레이어입니다.  
OLTP 원장 데이터를 Kafka로 동기화하고, Admin API로 tx_id 기반 조회를 제공합니다.

---

## 목적

- **FR-ADM-02**: 특정 트랜잭션 ID로 검색하면 시간, 보낸 사람, 받는 사람, 상태를 조회할 수 있습니다

---

## 구성 요소

| 컴포넌트 | 역할 |
|----------|------|
| **Admin API** | tx_id로 거래를 조회하는 REST API입니다 (FastAPI) |
| **Sync Consumer** | Kafka에서 이벤트를 받아 Serving DB에 저장합니다 (Python) |
| **Serving DB** | 조회에 최적화된 PostgreSQL입니다 (bo 스키마) |

---

## 아키텍처

OLTP DB → Kafka → [Sync Consumer] → Serving DB → [Admin API] → 관리자

---

## 주요 테이블

- `bo.ledger_entries` — 원장 엔트리를 저장합니다 (PK: tx_id)
- `bo.payment_orders` — 결제 오더를 저장합니다 (PK: order_id)
- `bo.payment_ledger_pairs` — PAYMENT/RECEIVE 페어링 결과를 저장합니다

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/admin/tx/{tx_id}` | 단건 거래를 조회합니다 |
| GET | `/admin/payment-orders/{order_id}` | 오더 기준으로 조회합니다 |
| GET | `/admin/wallets/{wallet_id}/tx` | 지갑의 거래 내역을 조회합니다 |

---

### 데이터 흐름

```mermaid
sequenceDiagram
  participant Admin as Admin User
  participant UI as Admin UI
  participant API as Admin API
  participant DB as Backoffice DB
  participant BUS as Kafka/Event Hub
  participant C as Sync Consumer

  Note over BUS,C: Continuous sync (near real-time)
  BUS->>C: LedgerEntryUpserted / PaymentOrderUpserted
  C->>DB: UPSERT (idempotent)

  Admin->>UI: Search tx_id
  UI->>API: GET /admin/tx/{tx_id}
  API->>DB: SELECT ledger_entries WHERE tx_id=...
  alt related_id exists
    API->>DB: SELECT pairs/peer by related_id
  end
  DB-->>API: tx trace (+pairing_status)
  API-->>UI: Response (+data_lag_sec)
  UI-->>Admin: Render result
```


