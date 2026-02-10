# tx-lookup-service Azure 네이밍 컨벤션

작성일: 2026-02-10
근거: DEC-111 (`.specs/decision_open_items.md`)

## 1. 리소스 소유 모델

리소스 생성은 인프라팀이 수행한다. 이 문서는 네이밍 컨벤션과 리소스 요구사항을 정의한다.

| 분류 | 리소스 | 비고 |
|------|--------|------|
| **서비스 전용** | Azure Database for PostgreSQL Flexible Server | 인프라팀에 생성 요청 |
| **RG 공유** | AKS, ACR, Key Vault, App Insights, Log Analytics | 인프라팀 소유, 서비스가 활용 |
| **기존 활용** | Event Hubs namespace | 이미 존재, 토픽(hub)만 소유 |
| **플랫폼 소유** | App Gateway, Bastion, Firewall, VNet, Private DNS Zone | 이 서비스 비관여 |

## 2. 포괄 네이밍 규칙

```
nsc-<service>-<resource>
```

- `nsc` — 조직 prefix
- `<service>` — 서비스명 (예: `txlookup`)
- `<resource>` — 리소스 타입 약어 (예: `pg`)

환경(dev/prod) 분리 없이 단일 소스로 운영한다.

## 3. 서비스 전용 리소스 명명

| 리소스 | 네이밍 | 비고 |
|--------|--------|------|
| PostgreSQL Flexible Server | `nsc-txlookup-pg` | 서비스 전용 DB |

## 4. 공유 리소스 내 서비스 격리 명명

| 대상 | 네이밍 | 비고 |
|------|--------|------|
| AKS namespace | `txlookup` | 공유 클러스터 내 격리 |
| ACR 이미지 리포지토리 | `txlookup/api`, `txlookup/consumer` | `<acr>.azurecr.io/txlookup/api:v1.0` |
| Key Vault secret prefix | `txlookup-<key>` | `txlookup-db-url`, `txlookup-kafka-password` |
| App Insights cloud_roleName | `txlookup-api`, `txlookup-consumer` | — |
| Event Hubs consumer group | `bo-sync-v1` | — |
| Event Hubs 토픽(hub) | `ledger.entry.upserted`, `payment.order.upserted` | — |

## 5. 태그 규칙

서비스 전용 리소스(PostgreSQL)에 아래 태그를 적용한다.

| 태그 | 값 | 비고 |
|------|----|------|
| `owner` | 배포 시 지정 | 담당자/팀 |
| `project` | `txlookup` | 프로젝트 식별 |

## 6. 참조

- 리소스 소유 모델: `.specs/decision_open_items.md` DEC-111
- Cloud-Secure 프로파일: `.specs/backoffice_project_specs.md` 10.3항
- 마이그레이션/재생성 정책: `.specs/cloud_migration_rebuild_plan.md`
