# tx-lookup-service Azure 리소스 인벤토리 (dev)

최종 검증: 2026-02-23 22:40 KST  
검증 방법: Azure CLI(`az`) 실시간 조회  
리소스 그룹: `2dt-final-team4`  
구독: `대한상공회의소 Data School`

## 1. 핵심 런타임 리소스 (필수 사용)

| 구분 | Azure 리소스 타입 | 리소스 이름 | 엔드포인트 / 접근 지점 | tx-lookup-service에서의 용도 | 현재 상태 |
|---|---|---|---|---|---|
| Backoffice DB | PostgreSQL Flexible Server | `nsc-pg-dev` | `nsc-pg-dev.postgres.database.azure.com:5432` | Consumer upsert 대상, Admin API 조회 원본 | `Ready` |
| 메시징 | Event Hubs Namespace (Kafka) | `nsc-evh-dev` | `nsc-evh-dev.servicebus.windows.net:9093` (Kafka), `:443` (AMQP/관리) | Sync Consumer 입력 스트림 | `Active` |
| 런타임 | AKS Managed Cluster | `nsc-aks-dev` | Private cluster (`az aks get-credentials`) | Admin API + Consumer 배포 대상 | `Running` (`provisioningState=Canceled`) |
| 이미지 레지스트리 | Azure Container Registry | `nscacrdevw4mlu8` | `nscacrdevw4mlu8.azurecr.io` | API/Consumer 이미지 push/pull | `Succeeded` |
| 시크릿 저장소 | Azure Key Vault | `nsc-kv-dev` | `https://nsc-kv-dev.vault.azure.net/` | DB/Event Hubs/Auth 시크릿 관리 | `Succeeded` |
| 앱 텔레메트리 | Application Insights | `nsc-ai-dev` | App Insights connection string | 앱 트레이스/메트릭 전송 대상 | `Succeeded` |
| 로그 분석 | Log Analytics Workspace | `nsc-law-dev` | LAW Workspace | 중앙 로그/알림 쿼리 백엔드 | `Succeeded` |

## 2. Event Hubs 상세 (현재 기준)

### 2.1 Event Hub(토픽) 목록

| Event Hub 이름 | 파티션 수 | 보관 기간(일) | 상태 |
|---|---:|---:|---|
| `cdc-events` | 4 | 7 | Active |
| `order-events` | 4 | 7 | Active |
| `server.domain.events` | 1 | 1 | Active |
| `wallet-create` | 1 | 7 | Active |

### 2.2 확인된 Consumer Group

| Event Hub 이름 | Consumer Group |
|---|---|
| `cdc-events` | `$Default`, `analytics-consumer` |
| `order-events` | `$Default`, `sync-consumer` |
| `server.domain.events` | `$Default` |
| `wallet-create` | `$Default`, `custody-consumer-group` |

### 2.3 Namespace 권한 규칙

| 규칙 이름 | 권한 |
|---|---|
| `RootManageSharedAccessKey` | Listen, Send, Manage |
| `domain_server` | Listen, Send |

## 3. 보조 인프라 (간접 사용)

| 구분 | Azure 리소스 타입 | 리소스 이름 | 필요한 이유 |
|---|---|---|---|
| 운영 접근 | Azure Bastion | `nsc-bas-dev` | Private 리소스/AKS 트러블슈팅 접근 경로 |
| Private Endpoint | Microsoft.Network/privateEndpoints | `nsc-pe-kv`, `nsc-pe-acr`, `nsc-pe-evh`, `nsc-pe-adls`, `nsc-pe-sqldb`, `nsc-pe-pg` | PaaS 서비스에 대한 private 경로 제공 |
| Private DNS Zone | Azure Private DNS Zone | `privatelink.postgres.database.azure.com`, `privatelink.servicebus.windows.net`, `privatelink.vaultcore.azure.net`, `privatelink.azurecr.io`, `privatelink.database.windows.net`, `privatelink.dfs.core.windows.net`, `privatelink.confidential-ledger.azure.com` | Private Endpoint 트래픽 내부 DNS 해석 |

## 4. 인접 리소스 (참고용, tx-lookup 핵심 런타임 아님)

| 영역 | 리소스 | 비고 |
|---|---|---|
| OLTP (Account/Commerce) | `nsc-sql-dev`, `nsc-account-commerce-db` | 업스트림 도메인 DB이며 Backoffice Serving DB가 아님 |
| Crypto Ledger | `nsc-cl-dev` | Crypto 서비스 소유 영역 |
| Analytics/Lakehouse | `nsc-dbw-dev`, `nscstdevw4mlu8` | 분석/ETL 경로로 tx-lookup 핵심 런타임은 아님 |

## 5. 환경변수 매핑 가이드 (tx-lookup-service)

클라우드 환경변수(`configs/env.example` 키) 구성 시 아래 매핑을 사용한다.

| 앱 설정 키 | 대상 리소스 | 권장 값 패턴 |
|---|---|---|
| `DATABASE_URL` | `nsc-pg-dev` | `postgresql+psycopg://<user>:<password>@nsc-pg-dev.postgres.database.azure.com:5432/<db>?sslmode=require` |
| `KAFKA_BROKERS` | `nsc-evh-dev` | `nsc-evh-dev.servicebus.windows.net:9093` |
| `KAFKA_SECURITY_PROTOCOL` | `nsc-evh-dev` | `SASL_SSL` |
| `KAFKA_SASL_MECHANISM` | `nsc-evh-dev` | `PLAIN` |
| `KAFKA_SASL_USERNAME` | `nsc-evh-dev` | SAS policy 이름 (예: 전용 listen policy) |
| `KAFKA_SASL_PASSWORD` | `nsc-evh-dev` | Key Vault에 저장된 SAS key |
| `LEDGER_TOPIC` | Event Hub | `cdc-events` (팀 합의 필요) |
| `PAYMENT_ORDER_TOPIC` | Event Hub | `order-events` (팀 합의 필요) |
| `KAFKA_GROUP_ID` | Consumer Group | tx-lookup 전용 그룹 (예: `bo-sync-consumer`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | `nsc-ai-dev` | Key Vault 저장 connection string |

## 6. 소유권 경계 (운영 규칙)

- 리소스 프로비저닝과 기본 정책은 인프라팀 소유다.
- 이 저장소는 필요한 리소스/네이밍/애플리케이션 설정을 정의한다.
- 문서와 실리소스 간 드리프트는 추적하되 F-track 개발을 차단하지 않는다(`DEC-225`).
- AKS/클러스터 내 검증은 현재 후순위로 이연하되, 문서 최종화 전에 선행 수행한다(`DEC-226`).

## 7. 증빙

- 실검증 로그: `.agents/logs/verification/azure_resource_validation_20260223_222811.log`
- 관련 의사결정: `.specs/decision_open_items.md` (`DEC-111`, `DEC-225`)

## 8. 업데이트 절차

인프라 변경 시점 또는 주요 배포 게이트 전에 본 문서를 갱신한다.
AKS/클러스터 내 검증은 문서 최종화 전에 반드시 1회 수행하고 증빙을 남긴다.

1. 대상 구독/리소스 그룹 확인:
   - `az account show`
   - `az group show --name 2dt-final-team4`
2. 핵심 런타임 리소스 재확인:
   - `az postgres flexible-server show -g 2dt-final-team4 -n nsc-pg-dev`
   - `az eventhubs namespace show -g 2dt-final-team4 -n nsc-evh-dev`
   - `az aks show -g 2dt-final-team4 -n nsc-aks-dev`
   - `az acr show -g 2dt-final-team4 -n nscacrdevw4mlu8`
   - `az keyvault show -g 2dt-final-team4 -n nsc-kv-dev`
   - `az monitor app-insights component show -g 2dt-final-team4 -a nsc-ai-dev`
   - `az monitor log-analytics workspace show -g 2dt-final-team4 -n nsc-law-dev`
3. Event Hubs 상세 재확인:
   - `az eventhubs eventhub list -g 2dt-final-team4 --namespace-name nsc-evh-dev`
   - `az eventhubs eventhub consumer-group list -g 2dt-final-team4 --namespace-name nsc-evh-dev --eventhub-name <hub-name>`
4. 출력 결과를 `.agents/logs/verification/`에 증빙으로 저장하고, 본 문서의 `최종 검증` 시각을 갱신한다.
