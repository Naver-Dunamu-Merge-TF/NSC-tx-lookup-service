# 이벤트 계약 변동 리스크 흡수 계획 (Pre-AKS 우선)

## 요약
업스트림 이벤트 계약이 미확정인 기간에도 개발/검증을 계속할 수 있도록, Consumer를 `Compat Core` 모드로 고정하고 `Profile Mapping` 기반으로 토픽/필드 차이를 흡수한다.
이번 범위는 문서 + 최소 코드 + 테스트(Phase 1-2)까지 포함하며, AKS 이전에 계약 변동 리스크를 운영 가능 상태로 낮추는 것이 목표다.

## 리뷰 반영 고정 결정 (2026-02-24)
1. 설정 로드 생명주기
- `load_config()`와 profile YAML 로드는 프로세스 시작 시 1회만 수행한다.
- `_handle_payload()`/DLQ 헬퍼 hot path에서는 설정 파일 I/O를 금지한다.
- `EVENT_PROFILE_ID` 변경 반영은 재시작으로만 처리한다(런타임 hot-reload 비대상).
2. alias 해석 규칙 (결정 완료)
- alias 후보는 선언 순서대로 평가한다.
- `trim 후 non-empty` 첫 값을 canonical로 채택한다.
- 같은 alias 그룹에서 서로 다른 non-empty 값이 2개 이상 발견되면 `contract_core_violation`으로 DLQ 격리한다(침묵 덮어쓰기 금지).
- 문자열 공백값(`\"\"`, `"   "`)은 missing으로 취급한다.
3. Env override 의미 (부분 override 허용)
- `LEDGER_TOPIC`과 `PAYMENT_ORDER_TOPIC`은 각각 독립 override 가능하다.
- 최종 우선순위는 키별로 `env > profile > default`다.
- override 결과 두 logical topic이 동일 값으로 수렴하면 시작 시점에 fail-fast 한다(역할 구분 불가).
4. 런타임 의존성
- 프로파일 로더 도입에 맞춰 `requirements.txt`에 `PyYAML>=6.0`를 명시한다.
5. 관측/알림 기준
- 신규 메트릭 3개 중 `consumer_contract_core_violation_total`만 알림 규칙으로 승격한다.
- `consumer_contract_alias_hit_total`, `consumer_contract_profile_messages_total`은 대시보드 관측 전용으로 운영한다(알림 대상 아님).

## 확정된 의사결정
1. 수용 정책: `Compat Core`
핵심 필드만 hard-fail, 그 외 변형은 alias/optional로 흡수하고 메트릭으로 드리프트 관측.
2. 토픽 전략: `Profile Mapping`
업스트림/환경별 프로파일을 선택해 단일 Consumer 로직 유지.
3. 제공 범위: `Phase 1-2 Full`
문서 정합화 + 최소 코드 + 테스트까지.
4. 설정 인터페이스: `EVENT_PROFILE_ID + YAML`
5. 문서 대상: `Core 4 docs`
`configs/topic_checklist.md`, `.specs/decision_open_items.md`, `.roadmap/implementation_roadmap.md`, `.specs/architecture_guide.md`
6. 충돌 우선순위: `Env Override`
`EVENT_PROFILE_ID`와 `LEDGER_TOPIC/PAYMENT_ORDER_TOPIC` 동시 설정 시 기존 env 토픽이 우선.

## 공개 인터페이스/타입 변경
1. 환경변수 추가
`EVENT_PROFILE_ID` (기본값: `canonical-v1`)
2. 설정 파일 추가
`configs/event_profiles.yaml`
3. 내부 설정 모델 확장
`src/common/config.py`의 `AppConfig`에 `event_profile_id`, `effective_ledger_topic`, `effective_payment_order_topic`(또는 동등 필드) 추가
4. 내부 계약 타입 추가
`src/consumer/contract_profile.py`(신규)
`EventContractProfile`, `TopicProfile`, `AliasProfile`, `CoreRequiredPolicy`
5. 메트릭 추가
`consumer_contract_alias_hit_total`
`consumer_contract_core_violation_total`
`consumer_contract_profile_messages_total`
6. 외부 Admin API 스펙 변경 없음
`/admin/*` 응답/경로는 변경하지 않는다.

## 구현 작업 계획

### Task 1: 프로파일 스키마와 기본 프로파일 정의
- 대상 파일: `configs/event_profiles.yaml` (신규), `configs/env.example`, `configs/README.md`
- 작업:
1. YAML 스키마를 고정한다.
```yaml
version: 1
profiles:
  canonical-v1:
    topics:
      ledger: ledger.entry.upserted
      payment_order: payment.order.upserted
    aliases:
      ledger:
        entry_type: [entry_type, type]
        event_time: [event_time, source_created_at, created_at]
        version: [version, source_version]
      payment_order:
        version: [version, source_version]
    core_required:
      ledger: [tx_id, wallet_id, entry_type, amount, event_time_or_alias]
      payment_order: [order_id, amount, status, created_at]
  nsc-dev-v1:
    topics:
      ledger: cdc-events
      payment_order: order-events
    aliases:
      ledger:
        entry_type: [entry_type, type]
        event_time: [event_time, source_created_at, created_at]
        version: [version, source_version]
      payment_order:
        version: [version, source_version]
    core_required:
      ledger: [tx_id, wallet_id, entry_type, amount, event_time_or_alias]
      payment_order: [order_id, amount, status, created_at]
```
2. `EVENT_PROFILE_ID` 설명/예시를 `configs/env.example`, `configs/README.md`에 추가한다.
3. `EVENT_PROFILE_ID`는 재시작 반영 정책임을 운영 가이드에 명시한다.
- 완료 기준: 프로파일 스키마/기본 2개 프로파일이 문서와 일치한다.

### Task 2: 설정 로더에 프로파일 해석 추가
- 대상 파일: `src/common/config.py`, `tests/unit/test_config.py`, `src/common/event_profiles.py` (신규)
- 작업:
1. YAML 로더를 추가하고 `EVENT_PROFILE_ID` 검증 로직을 구현한다.
2. 우선순위를 고정한다: `env topic override > profile topic > default`.
3. 부팅 시 유효하지 않은 프로파일 ID는 명시적 `ValueError`로 실패시킨다.
4. `load_config()` 결과에 `effective_*_topic`을 포함하고, 프로세스 실행 중에는 재로드하지 않는다.
5. `requirements.txt`에 `PyYAML>=6.0`를 추가하고 import 실패를 테스트로 방지한다.
- 완료 기준: `load_config()`만으로 최종 토픽 결정이 가능하고 테스트로 검증된다.

### Task 3: 계약 정규화 계층 추가
- 대상 파일: `src/consumer/contract_normalizer.py` (신규), `src/consumer/events.py`, `src/consumer/main.py`
- 작업:
1. 프로파일 alias를 사용해 입력 payload를 canonical 키로 정규화한다.
2. `core_required` 누락 시 `EventValidationError`를 표준 메시지로 발생시킨다.
3. alias 그룹에서 충돌(non-empty 상이값) 발생 시 `contract_core_violation`으로 분류한다.
4. 기존 `LedgerEntryUpserted.from_dict`, `PaymentOrderUpserted.from_dict` 호출 전에 정규화를 삽입한다.
5. `run_consumer`와 `run_backfill` 경로 모두 동일 정규화 함수를 사용한다.
- 완료 기준: 이벤트 원본 필드명이 달라도 canonical 이벤트 객체 생성이 동일하게 동작한다.

### Task 4: 컨슈머 토픽 디스패치 안정화
- 대상 파일: `src/consumer/main.py`, `tests/unit/test_consumer_handlers.py`
- 작업:
1. 토픽 비교를 `effective_*_topic` 기준으로 통일한다.
2. 프로파일 정보와 실제 topic 매핑을 시작 로그에 남긴다.
3. 미지원 topic 오류 메시지에 `profile_id`를 포함한다.
4. 동일 topic 중복 매핑(ledger == payment)은 시작 시 fail-fast 한다.
5. `_handle_payload()`가 runtime `load_config()`를 다시 호출하지 않도록 config/context를 주입한다.
- 완료 기준: 프로파일만 바꿔도 `_handle_payload`가 동일 로직으로 동작한다.

### Task 5: 드리프트 관측 메트릭 추가
- 대상 파일: `src/consumer/metrics.py`, `src/consumer/main.py`, `tests/unit/test_alert_rules.py`, `docker/observability/alert_rules.yml`
- 작업:
1. alias 사용 횟수, core violation 횟수, profile별 처리량 메트릭을 추가한다.
2. DLQ 기록 시 `error`를 `contract_core_violation`, `parse_error`, `unsupported_topic` 등으로 표준화한다.
3. `ContractCoreViolationHigh`(warning) 규칙을 `docker/observability/alert_rules.yml`에 추가한다.
4. 기존 `consumer_version_missing_total`과 함께 계약 성숙도 추적이 가능하도록 로그 포맷을 보강한다.
- 완료 기준: 계약 변동의 양과 유형이 메트릭/로그에서 분리 관측된다.

### Task 6: 테스트 확장
- 대상 파일: `tests/unit/test_events.py`, `tests/unit/test_consumer_handlers.py`, `tests/unit/test_config.py`, `tests/integration/test_db_integration.py`(필요 최소), `tests/e2e/test_admin_tx_e2e.py`(토픽 프로파일 경로 1건)
- 작업:
1. alias 기반 파싱 성공 케이스를 프로파일별로 추가한다.
2. core required 누락 시 DLQ로 격리되는 경로를 검증한다.
3. `EVENT_PROFILE_ID=nsc-dev-v1`에서 `cdc-events/order-events` 처리가 가능한지 검증한다.
4. env override 우선순위 테스트를 추가한다.
5. alias 충돌(non-empty 상이값) 시 DLQ 분류가 `contract_core_violation`인지 검증한다.
6. `ledger_topic == payment_order_topic` 구성에서 시작 fail-fast를 검증한다.
7. consumer hot path에서 config 재로드가 발생하지 않는지 단위 테스트로 검증한다.
- 완료 기준: 계약 변동 흡수 경로 회귀 테스트가 자동화된다.

### Task 7: 문서 동기화 (Core 4)
- 대상 파일: `configs/topic_checklist.md`, `.specs/decision_open_items.md`, `.roadmap/implementation_roadmap.md`, `.specs/architecture_guide.md`
- 작업:
1. `topic_checklist`를 `Core Required`와 `Profile-specific` 섹션으로 분리한다.
2. `decision_open_items`에 신규 DEC를 추가한다.
`DEC-227`: Compat Core 운영 정책
`DEC-228`: Profile Mapping + 설정 우선순위 정책
3. `implementation_roadmap` F3-1에 “프로파일 매핑/계약 성숙도 지표” 태스크를 추가한다.
4. `architecture_guide` 설정 섹션에 `EVENT_PROFILE_ID`, 우선순위, 정규화 흐름을 추가한다.
- 완료 기준: 코드/운영 정책/문서가 동일 용어와 동일 규칙을 사용한다.

### Task 8: Pre-AKS 운영 적용 절차 문서화
- 대상 파일: `.specs/architecture_guide.md` 또는 운영 가이드 섹션
- 작업:
1. dev에서 `EVENT_PROFILE_ID=nsc-dev-v1` 적용 절차를 정의한다.
2. 3일 관측 기준을 고정한다.
`contract_core_violation_rate`, `alias_hit_ratio`, `consumer_version_missing_total`
3. 기준 미달 시 조치 경로를 명시한다.
`profile alias 추가 -> replay/backfill -> 재검증`
- 완료 기준: 업스트림 변경이 와도 AKS 이전 개발을 멈추지 않는 운영 절차가 문서에 고정된다.

## 테스트 케이스/시나리오

1. `Config`
`EVENT_PROFILE_ID` 유효/무효, env override 우선순위, 기본 프로파일 fallback
2. `Ledger alias`
`type`, `source_created_at`, `source_version` 입력이 canonical로 변환되는지
3. `Payment alias`
`source_version` 등 변형 필드 수용
4. `Core missing`
필수 코어 누락 시 `EventValidationError` + DLQ 기록
5. `Unsupported topic`
현재 프로파일 기준 미지원 topic은 에러 격리
6. `Profile switch`
같은 바이너리로 `canonical-v1`과 `nsc-dev-v1`를 env 전환만으로 처리
7. `Regression`
기존 E2E (`/admin/tx/{tx_id}` 200/404) 동작 변화 없음
8. `Alias conflict`
동일 의미 alias 그룹에 상이한 non-empty 값이 동시에 올 때 `contract_core_violation`으로 DLQ 격리되는지
9. `Startup guard`
`effective_ledger_topic == effective_payment_order_topic`일 때 프로세스가 시작 실패하는지

## 검증 커맨드(구현 단계에서 실행)
1. L0: `.venv/bin/python -m py_compile $(find src -name '*.py')`
2. L1: `.venv/bin/python -m pytest tests/unit/ -x`
3. L2: `.venv/bin/python -m pytest --cov-fail-under=80`
4. 필요 시 E2E: `.venv/bin/python -m pytest tests/e2e/test_admin_tx_e2e.py -x`
5. 모든 증빙 로그 저장: `.agents/logs/verification/`

## 가정 및 기본값
1. 업스트림은 단기간에 단일 고정 계약으로 수렴하지 않는다.
2. Producer 변경은 이 저장소 범위 밖이며, Consumer 쪽 흡수로 대응한다.
3. 기존 `LEDGER_TOPIC`, `PAYMENT_ORDER_TOPIC`은 하위호환 유지한다.
4. 기본 프로파일은 `canonical-v1`로 둔다.
5. 이번 단계에서는 AKS 자체 변경보다 계약 흡수 레이어 구축을 우선한다.
