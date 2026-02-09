# Cloud Migration/Rebuild Plan (Test-first)

Last updated: 2026-02-09

## 1. 목적

이 문서는 Azure 테스트 환경을 빠르게 만들고 부순 뒤, 나중에 보안 적용 버전으로 재생성할 때
데이터/마이그레이션/운영 절차를 일관되게 유지하기 위한 기준이다.

## 2. 기본 원칙

1. Backoffice DB는 파생 저장소다. 데이터는 재생성 가능해야 한다.
2. 스키마 변경은 Alembic 마이그레이션으로만 관리한다.
3. 테스트 환경은 폐기 가능(disposable)해야 한다.
4. 운영 전환은 "기존 리소스 수정"보다 "새 리소스 생성 후 컷오버"를 우선한다.

## 3. 범위

Phase 8 클라우드 인프라 준비 항목 기준:
- Azure PostgreSQL Flexible Server
- Event Hubs (Kafka endpoint) 또는 Managed Kafka
- ACR + 실행환경(ACA/AKS)
- Key Vault + Managed Identity
- App Insights + Log Analytics

## 3.1 Phase 8 테스트 프로파일 (확정)

1. 메시징/런타임: `Event Hubs(Kafka) + Azure Container Apps`
2. Event Hubs 소유: 팀 공유가 아닌 개인 분리 namespace 사용
3. 네트워크: 테스트 목적 퍼블릭 엔드포인트 허용
4. 시크릿: 가장 단순한 전달 방식(SAS/env 주입) 우선
5. Event Hubs 기준값:
- hubs: `ledger.entry.upserted`, `payment.order.upserted`
- partition: 각 2
- retention: 3 days
- consumer group naming: `bo-sync-<env>-<owner>-v1`
6. 본 프로파일은 테스트/검증 전용이며, 보안 강화 버전은 별도 리소스 재구성으로 전환한다.

## 3.2 개발 단계 모델 (테스트 리소스 -> 보안 리소스)

1. Stage A: **Cloud-Test(폐기형)**
- 퍼블릭 허용 리소스에서 빠른 E2E 검증
- synthetic 이벤트 기반 동작 확인
- 필요 시 즉시 폐기/재생성

2. Stage B: **Cloud-Secure(운영형)**
- 보안 네트워크/권한이 적용된 별도 리소스에 재배포
- Key Vault + Managed Identity 전환
- 동일 스모크 + SLO 게이트 재검증

3. Stage C: **승격 자동화**
- Stage A 통과 결과를 기준으로 Stage B 반영
- CI/CD 게이트와 재처리(runbook)를 포함

로드맵 매핑:
- Stage A -> `.roadmap/implementation_roadmap.md` Phase 8
- Stage B -> `.roadmap/implementation_roadmap.md` Phase 9
- Stage C -> `.roadmap/implementation_roadmap.md` Phase 10

## 3.3 공통 명명/태그/가드레일 정책 (지속 적용)

1. 리소스 명명 규칙
- 하이픈 허용 리소스: `team4-txlookup-<resource>-<owner>-<env>`
- 하이픈 비허용 리소스(예: ACR, Storage): `team4txlookup<resource><owner><env>`
- 길이 제한 리소스(Container Apps 계열): `team4-tx-<resource>-<owner>-<env_short>` 형태를 사용하고 이름 길이는 32자 이하여야 한다.
- `owner`, `env` 토큰은 환경 프로파일 입력값으로 관리한다(정책에 하드코딩하지 않음).

2. 테스트/폐기형 환경 공통 태그 규칙
- 필수 태그: `env`, `owner`, `project`, `ttl`
- `ttl`은 `YYYY-MM-DD` 형식을 사용하며 만료 전/만료 시점에 연장 또는 폐기 결정을 수행한다.

3. 공통 가드레일
- Databricks managed 리소스 그룹 및 하위 리소스는 플랫폼 관리 대상이므로 수동 rename/delete를 금지한다.
- tx-lookup 테스트 실행은 Event Hubs 개인 분리 namespace를 사용한다(공유 namespace 의존 금지).
- 파괴 작업은 명명 규칙과 태그 규칙으로 테스트 대상임을 식별한 리소스에만 수행한다.

## 4. 마이그레이션 전략

1. 마이그레이션 파일은 `migrations/` 디렉터리를 단일 SSOT로 유지한다.
2. DB 재생성 시 마다 동일하게 `alembic upgrade head`를 실행한다.
3. 기존 마이그레이션은 수정하지 않고, 변경은 새 리비전 추가만 허용한다.
4. 스키마 변경은 호환성 우선으로 진행한다(Expand -> 애플리케이션 반영 -> Contract).
5. 테스트 환경 파괴 시 DB 상태는 폐기하며, 데이터 복구는 백필/재동기화로 수행한다.
6. 긴급 상황 외 수동 SQL 변경은 금지하며, 예외 적용 시 사후 Alembic 리비전으로 환원한다.

## 5. 재생성 순서 정책 (Destroy -> Recreate)

1. 클라우드 리소스 신규 생성
2. 앱 시크릿/연결정보(Key Vault) 재주입
3. DB 초기화 + `alembic upgrade head`
4. 초기 백필 실행
5. consumer 기동 후 증분 동기화 시작
6. API 스모크 테스트 (`GET /admin/tx/{tx_id}`)
7. 모니터링/알림 정상 여부 확인

## 6. 데이터 복구/동기화 정책

1. Backoffice DB 데이터는 정합성 기준이 아니라 캐시/서빙 파생본으로 취급한다.
2. 정합성 복구는 `backfill` 후 `consumer 증분 반영` 순서로 보장한다.
3. 모든 재생성 작업은 UTC 기준 컷오버 시각(`T_cutover`)을 명시해야 한다.
4. backfill 범위는 `T_cutover` 이전, 증분 반영 범위는 `T_cutover` 이후로 정의한다.
5. 이벤트 보관기간은 backfill 수행시간과 복구 버퍼를 고려해 충분히 확보해야 한다.

## 7. 컨슈머 오프셋/그룹 정책

1. 오프셋/컨슈머 그룹은 환경별로 분리한다.
2. 재생성 시 기본 원칙은 신규 컨슈머 그룹 사용이다.
3. 기존 컨슈머 그룹 오프셋 재사용은 명시적 재처리 목적일 때만 허용한다.
4. 컨슈머 그룹 정책은 환경 식별자(`dev`/`prod`)와 배포 세대를 구분 가능해야 한다.

## 8. 검증 게이트 정책

1. 마이그레이션 직후 DB 리비전은 `head`와 일치해야 한다.
2. 백필/증분 반영 후 서비스 품질은 프로젝트 SLO 기준(API p95, freshness, error, DLQ)에 부합해야 한다.
3. API 조회 기준 성공/실패 케이스(200/404) 모두 정상 동작해야 한다.
4. 페어링/신선도/지연 지표는 관측 스택에서 확인 가능해야 한다.

## 9. 롤백 원칙

1. 애플리케이션 버그는 배포 롤백으로 처리한다.
2. 스키마/데이터 문제가 크면 환경 전체 재생성을 우선한다.
3. 롤백/재생성 판단 시 데이터 정합성, 복구시간, 운영 리스크를 함께 평가한다.
4. 전환 기간에는 애플리케이션과 스키마의 상호 호환성을 유지해야 한다.

## 10. 보안 버전 전환 계획 (추후)

1. 테스트용 퍼블릭 엔드포인트 구성과 보안 구성은 동일 환경에서 인플레이스 변경하지 않는다.
2. 보안 적용 리소스를 별도 생성한다.
3. 데이터 재적재(backfill + sync) 후 컷오버한다.
4. 테스트 리소스는 컷오버 확인 후 폐기한다.

## 11. 폐기 안전장치 정책

1. 파괴 작업은 테스트용으로 식별된 리소스에만 수행한다.
2. 환경 간 리소스 격리와 명명 규칙은 파괴 작업 전에 검증 가능해야 한다.
3. 파괴 전에는 대상 환경, 영향 범위, 복구 경로가 확인돼야 한다.

## 12. 운영 체크리스트

- [ ] 환경별 리소스 명명 규칙 확정 (`dev`/`prod`)
- [ ] 마이그레이션 호환성 정책(Expand/Contract) 적용
- [ ] 컷오버 시각(`T_cutover`) 관리 기준 확정
- [ ] consumer group 식별 정책 확정
- [ ] SLO 기반 검증 게이트 기준 확정
- [ ] 테스트 리소스 폐기 안전장치 기준 확정

## 13. 참조

- `.roadmap/implementation_roadmap.md` (Phase 8)
- `.specs/backoffice_project_specs.md` (10.3 Azure 배포)
- `.specs/backoffice_data_project.md` (동기화/재처리 원칙)
