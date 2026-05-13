# Backend 작업 가이드

세션 상태와 API 컨트랙트의 무결성을 지킨다 — DT 직접 import·schema 임의 변경·MLSimulator의 prod-환경 Stub fallback이 가장 큰 함정.

**Tradeoff**: 실시간 세션 상태를 in-memory(`InMemoryStateStore`)로 두고 DB 영속화는 `simulation_log_repo`로 분리하면 단일 영속 경로 단순함을 포기하는 대신 세션 일관성·테스트 격리·책임 경계를 얻는다.

## 1. WHAT — 이 모듈은 무엇을 하는가

FastAPI 기반 API 서버. 시뮬 세션 관리, 제어 입력 주입, WebSocket 실시간 스트리밍, 5분 horizon NOx 예측 API를 담당한다. 운영 임계값을 단일 진실원에서 노출(`GET /api/threshold`)하고, ML 스냅샷 모드에서는 DB `sensor_data`를 조회해 DT 입력으로 변환한다.

## 2. CONTENTS — 파일/디렉토리와 기술 스택

- `app/api/` — REST/WebSocket 엔드포인트 (`router.py`, `deps.py`, `errors.py`)
  - `endpoints/`: `health`, `session`, `stream`(REST), `streaming`(WebSocket), `prediction`, `threshold`
- `app/services/` — 비즈니스 로직 (`session_service`, `forecast_service`, `threshold_service`)
- `app/domain/` — 도메인 모델 + IGCC 태그 매핑 (`tags.py` — 10 ControlVars의 `_FIELD_RULES`가 SoT)
- `app/repositories/` — DB 접근 레이어
  - `sensor_repo.py`: `sensor_data` 14컬럼 조회 (`fetch_recent_window` — ML 스냅샷 입력)
  - `simulation_log_repo.py`: 세션/예측 로그 영속화 (`simulation_session_log`, `simulation_log` 테이블 DDL 포함)
- `app/adapters/` — 외부 시스템 어댑터 (각 폴더 `base.py` Protocol + 구현체)
  - `simulator/`: `ml.py` `MLSimulator` (정상 경로) / `stub.py` `StubSimulator` (fallback)
  - `forecaster/`: `ml.py` `MLForecaster` / `stub.py` `StubForecaster`
  - `data_source/`: `snapshot.py` `SnapshotDataSource` — `sensor_repo` 경유 ML 스냅샷 제공
- `app/core/` — 런타임 핵심 모듈 (Simulator/Forecaster 외 모두 여기)
  - `lifespan.py` — startup DI 주입 (모든 singleton을 `app.state`에 attach)
  - `sim_loop.py` `SimLoopManager` — 시뮬 step 비동기 루프 (efficiency 후처리 포함)
  - `state_store.py` `InMemoryStateStore` — 세션별 SimulationState 보관
  - `input_injector.py`, `kafka_stream.py`, `ws_manager.py`, `session_context.py`, `ml_mode.py`, `sensor_csv.py`, `logging.py`
- `app/db/` — `DbContext` (sync `sessionmaker`). `db/models/__init__.py`는 의도적으로 빈 상태 (운영 조회 페이지 미구현 + 임계 SoT는 DT config 직결)
- `app/schemas/` — Pydantic 요청/응답 (`session`, `stream`, `streaming`, `prediction`, `threshold`, `common`)
- `app/core/`, `config.py`, `exceptions.py` — 설정/예외
- `tests/` — pytest. 루트 `test_*.py` + 하위 `adapters/api/core/integration/repositories/services/` 분류
- `pytest.ini`, `requirements.txt`, `Dockerfile`

기술 스택: FastAPI 0.115, Pydantic 2.9, SQLAlchemy 2.0, psycopg 3.2, kafka-python 2.0, asyncio, pytest

## 3. HOW — 일반적인 수정은 어떻게 하는가

- **새 엔드포인트**: `app/api/endpoints/<name>.py` 라우터 추가 → `router.py`에 include → `app/schemas/`에 Pydantic schema → `app/services/`에 로직 → `tests/api/` 또는 `tests/services/`.
- **외부 의존(DT 모델/DB) 호출**: 어댑터 또는 repository 경유. 서비스에서 DT를 직접 import하지 않음.
- **DI 주입**: `app/core/lifespan.py`에서 singleton을 `app.state.*`에 attach → `app/api/deps.py`의 getter로 endpoint에 주입.
- **schema 변경 시**: 프론트(`apps/frontend/`)의 타입과 동시 갱신. PR 메시지에 `[API 임시]` 마커.
- **테스트 추가**: `tests/<카테고리>/`에 pytest 파일. `pytest.ini`의 `asyncio_mode = auto`이므로 `async def test_*` 그대로.

## 4. ⛔ HOW NOT — 시스템을 깨뜨리는 비명백한 함정

- 실시간 세션 상태를 DB에 직접 저장 — `InMemoryStateStore`만 사용. 영속화는 `simulation_log_repo` 경로로 분리 (session start/end + prediction 결과만 기록)
- DT 모델을 서비스/엔드포인트에서 직접 import — `app/adapters/`를 통해서만 호출, 직접 import 시 테스트 모킹 불가
- API 응답 스키마 임의 변경 — 프론트와 컨트랙트 깨짐, 협의 (`[API 임시]`) 후 동시 PR
- DB 컬럼명 추측 사용 — 운영 시 쿼리 실패, DB 팀 협의 (`[DB 협의 필요]`) 후 진행
- `co` 필드를 schema/응답에 부활 — 학습 타겟에서 영구 제외 (`docs/REFACTOR_FLAME_TEMP_TO_EXHAUST_TEMP.md`)
- `ControlVars` 필드를 10개 외로 변경 — `tags.py::_FIELD_RULES`와 `digital_twin/simulation/state.py::ControlVars`를 동시 갱신해야 양쪽 검증 통과
- 운영 임계를 backend 자체 코드/DB에 두기 — SoT는 `digital_twin/simulation/config.py::ThresholdConfig`. `threshold_service`는 DT config를 그대로 노출
- `prediction_service`로 명명 복귀 — `forecast_service`가 현행 (5분 horizon 명시 의도, `PredictionRequest.target_minutes` 필드 없음)
- Simulator와 Forecaster를 단일 어댑터로 통합 — `lifespan.py`에서 별도 DI, 통합 시 테스트/모킹 어려움 + 책임 혼재
- `APP_ENV=production`에서 `MLSimulator` 초기화 실패를 Stub로 fallback — `lifespan.py`는 prod에서 `PredictorUnavailableError`를 raise. `SIMULATOR_FALLBACK_STUB=true`를 prod 환경에 설정 금지
- `SENSOR_COLUMN_MAPPING` 없이 prod ML 스냅샷 모드 기동 — `lifespan.py`가 `DataSourceUnavailableError` raise. 환경별 매핑을 `.env`로 명시
- `sensor_repo`/`simulation_log_repo`를 "폐기됐다"고 가정하고 제거 — 둘 다 운영 경로. 변경 시 영향 평가 필수

## 5. WHERE — 다른 모듈과의 의존성

<!-- 강결합: ThresholdConfig 9개 운영 임계가 GET /api/threshold 응답과 직결. ControlVars/OutputVars 정의는 backend tags.py와 1:1. -->
@../../digital_twin/AGENTS.md

- **의존 (약결합)**:
  - [`digital_twin/AGENTS.md`](../../digital_twin/AGENTS.md): 시뮬 엔진(`simulation/`)과 ML 모델(`models/`) — 어댑터 경유 호출, `preprocess`의 `RAW_FEATURES`/`TARGETS`는 `sensor_repo`가 직접 참조
  - [`database/AGENTS.md`](../../database/AGENTS.md): `sensor_data` 14컬럼 (psycopg + SQLAlchemy core), `simulation_session_log`/`simulation_log` 테이블은 `simulation_log_repo`가 생성
  - [`docker/AGENTS.md`](../../docker/AGENTS.md): Dockerfile + compose 통합 기동
- **피의존**: [`apps/frontend/AGENTS.md`](../frontend/AGENTS.md) — REST + WebSocket 클라이언트
- **경계 / 어댑터**:
  - `app/adapters/simulator/`, `app/adapters/forecaster/`, `app/adapters/data_source/` — DT/DB 경계
  - `app/db/session.py` `DbContext` — PostgreSQL 경계
  - `app/core/kafka_stream.py` — Kafka 토픽 소비 (실시간 모드 입력)

## 6. WHY — 코드에 안 적힌 배경 지식

- **현재 backend 스펙 (PR #35~#57 반영)**:
  - `ControlVars` 10개 — `app/domain/tags.py::_FIELD_RULES`가 SoT
  - `OutputVars` 5개 — nox/exhaust_temp/power/lambda_/efficiency (ML 직접 출력은 3개, lambda_/efficiency는 파생)
  - Simulator vs Forecaster 분리 — DI 슬롯 별도 (`app/core/lifespan.py`)
  - Forecast horizon 5분 고정 — `PredictionRequest`에 sid만, `target_minutes` 없음
  - `efficiency` 후처리 — `power / (syngas_flow × syngas_lhv)`를 `app/core/sim_loop.py`에서 계산
  - 운영 임계 SoT — `digital_twin/simulation/config.py::ThresholdConfig` 직결, `GET /api/threshold`가 운영 임계 반환
  - sensor 운영 조회 엔드포인트 미구현 — `app/db/models/`가 의도적으로 빈 상태
  - 세션/예측 영속화 — `simulation_log_repo`가 startup 시 `ensure_tables()`로 DDL 보장
- **MLSimulator 분기 배경 (env-driven)**: prod에서는 ML 모델 누락이 즉시 알림 대상이어야 하므로 raise. dev/test에서는 Stub로 fallback해 UI 검증 가능. `SIMULATOR_FALLBACK_STUB=true`로 강제 Stub 전환도 가능.
- **`SnapshotDataSource` 도입 배경**: ML 모드에서 DT 입력은 최근 1초/분 단위 시계열이 필요한데, 매 시뮬 step마다 DB를 직접 조회하면 성능 문제 → SnapshotDataSource가 캐시 + 버퍼링 책임을 가짐.

## 7. COMMANDS — 빌드/테스트/린트

- 개발 서버: `uvicorn app.main:app --reload` (또는 docker-compose 사용)
- 테스트 (전체): `pytest` (repo root 또는 `apps/backend/`에서)
- 테스트 (카테고리): `pytest tests/services/`, `pytest tests/adapters/` 등
- 통합 테스트: `pytest -m integration` (실제 모델/DB 필요)
- Docker 빌드: docker-compose 경유 ([`docker/AGENTS.md`](../../docker/AGENTS.md))

**영역 고유 명령어 가드**:
- pytest를 임의 디렉토리에서 실행하면 `digital_twin` import 실패 — `pytest.ini`의 `pythonpath = . ../..`가 적용되는 `apps/backend/` 또는 repo root에서만 실행
- `pytest -m integration`은 실제 DB/모델 필요 — staging 환경에서만
- `APP_ENV=production`에서 `SIMULATOR_FALLBACK_STUB=true` 사용 — 모델 누락을 은닉하므로 금지

## 8. ⚠️ LEARNED CAUTIONS — 학습된 주의사항

<!-- `learn` 스킬(`/learn` 또는 Codex의 `$learn`)로 누적되는 영역. -->

_(아직 없음)_
